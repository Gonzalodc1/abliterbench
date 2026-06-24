"""The operator agent loop — plan -> act -> observe -> reflect.

This is the operative layer that turns a raw 8B model into a capable red-team /
OSINT agent. It is UI-agnostic: it emits events through `on_event` and asks for
approvals through `approval_cb`, so the same loop drives the terminal REPL and
(with auto-approval) the autonomous benchmark harness.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..llm_client import ChatMessage, OllamaClient, ToolCall
from ..config import Sampling
from . import context as ctxmod
from . import prompts
from .planner import Plan
from .scope import Scope
from .session import Session
from .tools import Bridge, filter_catalog, find_tool, schemas_for

# Small 8B models frequently *narrate* a call ("call nuclei_scan(url=...)") instead
# of emitting a native tool_call. These helpers recover those so we don't burn a
# whole step on repair — the single biggest efficiency win observed in testing.
_CALL_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)", re.S)
_KV_RE = re.compile(r"([a-zA-Z_]\w*)\s*=\s*(\"[^\"]*\"|'[^']*'|[^,()]+)")


def _coerce(v: str) -> Any:
    v = v.strip().strip("\"'")
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def loose_calls(text: str, valid: set[str]) -> list[ToolCall]:
    """Extract the first `name(args)` call from prose, restricted to known tools."""
    for m in _CALL_RE.finditer(text or ""):
        name, inner = m.group(1), m.group(2).strip()
        if name not in valid:
            continue
        args: dict[str, Any] = {}
        if inner.startswith("{"):
            try:
                args = json.loads(inner)
            except Exception:
                args = {}
        if not args:
            args = {k: _coerce(val) for k, val in _KV_RE.findall(inner)}
        return [ToolCall(name=name, arguments=args, raw=m.group(0))]
    return []


def sanitize_args(args: dict) -> dict:
    """Unwrap schema-echo wrappers like {"domain": {"type": "string", "value": X}}."""
    out: dict[str, Any] = {}
    for k, v in (args or {}).items():
        if isinstance(v, dict) and "value" in v and set(v).issubset(
                {"type", "value", "description", "default", "items"}):
            out[k] = v["value"]
        else:
            out[k] = v
    return out


def schema_echo(args: dict) -> bool:
    """True if the model pasted JSON-schema fragments as argument *values*
    (e.g. {"query": {"type": "string", "description": "..."}}) — a common 8B
    failure mode that yields a 422 with no usable value."""
    for v in (args or {}).values():
        if isinstance(v, dict) and ("type" in v or "description" in v) and "value" not in v:
            return True
    return False


def example_call(tool_name: str) -> str:
    """Build a concrete one-line example call for a repair hint."""
    tool = find_tool(tool_name)
    if not tool:
        return f'{tool_name}(...)'
    req = tool.schema.get("required", []) or list(tool.schema.get("properties", {}))[:2]
    parts = []
    for k in req:
        typ = tool.schema.get("properties", {}).get(k, {}).get("type", "string")
        parts.append(f'{k}=3' if typ == "integer" else f'{k}="..."')
    return f'{tool_name}(' + ", ".join(parts) + ')'

EventCb = Callable[[dict[str, Any]], None]
ApprovalCb = Callable[[dict[str, Any]], bool]


@dataclass
class OperatorConfig:
    model_tag: str
    model_alias: str = "operator"
    host: str = "http://localhost:11434"
    bridge_url: str = "http://127.0.0.1:8765"
    tools_filter: str = "all"
    max_steps: int = 14
    seed: int | None = 42
    approval_policy: str = "intrusive"  # auto | intrusive | active | all
    rag_auto: bool = True
    rag_corpora: list[str] = field(default_factory=lambda: ["hacktricks", "gtfobins"])
    rag_top_k: int = 3
    compact_budget_tokens: int = 9000
    distill_over_chars: int = 1800
    per_tool_timeout_s: float = 150.0
    temperature: float = 0.4  # lower than bench default for steadier agentic behaviour
    # Optional per-agent persona override (used by the multiagent roles). When
    # None, the default red-team operator persona/few-shot are used.
    system_prompt: str | None = None
    fewshot: str | None = None
    # Refuse to accept a FINAL ANSWER until at least this many DISTINCT tools have
    # succeeded — stops the 8B "run one tool and quit" behaviour observed in eval.
    min_successful_tools: int = 0


def _needs_approval(risk: str, policy: str) -> bool:
    if policy == "auto":
        return False
    if policy == "all":
        return True
    if policy == "active":
        return risk in {"active", "intrusive"}
    return risk == "intrusive"  # default "intrusive"


class Operator:
    def __init__(self, cfg: OperatorConfig, scope: Scope | None = None,
                 on_event: EventCb | None = None, approval_cb: ApprovalCb | None = None,
                 session: Session | None = None) -> None:
        self.cfg = cfg
        self.scope = scope or Scope()
        self.on_event = on_event or (lambda ev: None)
        self.approval_cb = approval_cb
        self.client = OllamaClient(host=cfg.host, timeout_s=600.0)
        self.bridge = Bridge(cfg.bridge_url, timeout_s=cfg.per_tool_timeout_s)
        self.tools = filter_catalog(cfg.tools_filter)
        self.tool_names = [t.name for t in self.tools]
        self.schemas = schemas_for(self.tools)
        self.sampling = Sampling(temperature=cfg.temperature)
        self.session = session or Session(cfg.model_alias)
        self.plan = Plan()
        persona = cfg.system_prompt or prompts.SYSTEM_PERSONA
        fewshot = cfg.fewshot if cfg.fewshot is not None else prompts.FEWSHOT
        self.messages: list[ChatMessage] = [
            ChatMessage("system", persona + ("\n\n" + fewshot if fewshot else "")),
            ChatMessage("system", "[plan]\n(no plan yet)"),
        ]

    # ---- infrastructure ---------------------------------------------------
    def preflight(self) -> dict:
        ok_llm = self.client.health()
        ok_bridge, n_eps = self.bridge.health()
        native = False
        if ok_llm:
            try:
                native = self.client.supports_native_tools(self.cfg.model_tag)
            except Exception:
                native = False
        info = {"llm": ok_llm, "bridge": ok_bridge, "endpoints": n_eps, "native_tools": native}
        self._emit({"type": "preflight", **info})
        return info

    # ---- helpers ----------------------------------------------------------
    def _emit(self, ev: dict[str, Any]) -> None:
        try:
            self.on_event(ev)
        finally:
            self.session.event(ev)

    def _summarize(self, prompt: str) -> str:
        try:
            r = self.client.generate(self.cfg.model_tag, prompt, seed=self.cfg.seed,
                                     sampling=self.sampling)
            return r.text or ""
        except Exception:
            return ""

    def _set_plan_msg(self) -> None:
        cur = self.plan.current
        cur_line = f"\nCurrent step: {cur.text}" if cur else ""
        self.messages[1] = ChatMessage("system", f"[plan]\n{self.plan.render()}{cur_line}")

    def _rag_context(self, goal: str) -> str:
        if not self.cfg.rag_auto:
            return ""
        blocks: list[str] = []
        for corpus in self.cfg.rag_corpora:
            res = self.bridge.call("rag_search",
                                   {"query": goal, "corpus": corpus, "top_k": self.cfg.rag_top_k})
            for ch in (res.get("chunks") or [])[: self.cfg.rag_top_k]:
                blocks.append(f"[{ch.get('source')}] {str(ch.get('text',''))[:400]}")
        ctx = "\n".join(blocks)[:1800]
        if ctx:
            self._emit({"type": "rag", "corpora": self.cfg.rag_corpora, "chars": len(ctx)})
        return ctx

    # ---- main entry -------------------------------------------------------
    def run_task(self, goal: str) -> dict:
        self._emit({"type": "user", "text": goal})

        # 1. RAG-augmented planning
        rag_ctx = self._rag_context(goal)
        plan_text = self._summarize(prompts.plan_user_msg(goal, self.tool_names, rag_ctx))
        self.plan = Plan.from_text(plan_text)
        self._set_plan_msg()
        self._emit({"type": "plan", "steps": [s.text for s in self.plan.steps],
                    "render": self.plan.render()})

        self.messages.append(ChatMessage("user", goal))

        stuck = 0
        no_tool = 0
        final: str | None = None
        executed: dict[str, str] = {}  # tool+args signature -> short result, for dedupe
        ok_tools: set[str] = set()     # distinct tools that succeeded (for min_successful_tools)
        pushbacks = 0                  # times we refused a premature final

        for step in range(1, self.cfg.max_steps + 1):
            # context compaction
            self.messages, did = ctxmod.maybe_compact(
                self.messages, self._summarize, self.cfg.compact_budget_tokens)
            if did:
                self._emit({"type": "compact"})
            self._set_plan_msg()
            self._emit({"type": "step_start", "step": step,
                        "progress": list(self.plan.progress())})

            try:
                resp = self.client.chat_with_tools(
                    self.cfg.model_tag, self.messages, self.schemas,
                    seed=self.cfg.seed, sampling=self.sampling)
            except Exception as e:
                self._emit({"type": "error", "error": str(e)})
                final = f"ERROR: {e}"
                break

            text = (resp.text or "").strip()
            if text:
                self._emit({"type": "assistant", "text": text,
                            "mode": resp.tool_calling_mode,
                            "tok_s": round(resp.tokens_per_second, 1),
                            "tokens": resp.completion_tokens,
                            "prompt_tokens": resp.prompt_tokens})

            calls = resp.parsed_tool_calls
            is_final = "FINAL ANSWER" in text.upper()

            # Recover a narrated call ("call nuclei_scan(url=...)") if no native call.
            if not calls and not is_final:
                loose = loose_calls(text, set(self.tool_names))
                if loose:
                    calls = loose
                    self._emit({"type": "loose_parse", "tool": loose[0].name})

            # ---- no tool call ----
            if not calls:
                if is_final or (self.plan.all_done() and text):
                    # refuse a premature final: force more thorough enumeration
                    if (len(ok_tools) < self.cfg.min_successful_tools
                            and pushbacks < self.cfg.min_successful_tools
                            and step < self.cfg.max_steps):
                        pushbacks += 1
                        unused = [t for t in self.tool_names if t not in ok_tools][:6]
                        self.messages.append(ChatMessage("assistant", text or "(done?)"))
                        self.messages.append(ChatMessage("user",
                            f"Do NOT conclude yet — only {len(ok_tools)} tool(s) have succeeded, "
                            f"the objective needs at least {self.cfg.min_successful_tools} distinct "
                            f"tools. Make the next concrete tool call now. Useful options: "
                            f"{', '.join(unused)}."))
                        self._emit({"type": "pushback", "ok_tools": sorted(ok_tools)})
                        continue
                    final = text
                    self.plan.advance(ok=True)
                    break
                no_tool += 1
                self.messages.append(ChatMessage("assistant", text or "(no output)"))
                if no_tool >= 2:
                    # reflection / force a decision
                    self.messages.append(ChatMessage("user", prompts.REFLECT_TEMPLATE.format(
                        stuck=no_tool, plan=self.plan.render(),
                        recent=text[:400] or "(empty)")))
                    self._emit({"type": "reflect", "reason": "no tool call"})
                    no_tool = 0
                else:
                    self.messages.append(ChatMessage("user", prompts.REPAIR_TEMPLATE))
                    self._emit({"type": "repair"})
                continue

            no_tool = 0
            call = calls[0]  # one tool per step
            tname, targs = call.name, sanitize_args(call.arguments)

            # ---- malformed args: model pasted the JSON schema instead of values ----
            if schema_echo(targs):
                self._emit({"type": "bad_args", "tool": tname})
                self.messages.append(ChatMessage("assistant", text or f"[attempt {tname}]"))
                self.messages.append(ChatMessage("user",
                    f"Your arguments for {tname} were a JSON schema, not real values. "
                    f"Re-call it with concrete values only, e.g. {example_call(tname)}"))
                stuck += 1
                continue

            # ---- cap default exec timeout so a runaway command can't burn the budget ----
            if tname in ("run_python", "run_bash") and "timeout_s" not in targs:
                targs["timeout_s"] = 45

            risk = self.scope.risk(tname, targs)

            # ---- dedupe identical successful calls ----
            sig = tname + "|" + json.dumps(targs, sort_keys=True, default=str)
            if sig in executed:
                self._emit({"type": "dedupe", "tool": tname})
                self.messages.append(ChatMessage("assistant", text or f"[repeat {tname}]"))
                self.messages.append(ChatMessage("tool",
                    f"{tname} already run with these args earlier. Prior result:\n{executed[sig]}\n"
                    "Do NOT repeat it — use this result or take a different action."))
                stuck += 1
                continue

            # ---- scope guardrail ----
            ok_scope, reason = self.scope.check(tname, targs)
            if not ok_scope:
                self._emit({"type": "scope_block", "tool": tname, "args": targs, "reason": reason})
                self.messages.append(ChatMessage("assistant", text or f"[attempt {tname}]"))
                self.messages.append(ChatMessage("tool",
                    f"{tname} REFUSED (scope): {reason}. Choose an in-scope target."))
                stuck += 1
                continue

            # ---- approval gating ----
            if _needs_approval(risk, self.cfg.approval_policy):
                action = {"type": "approval_request", "tool": tname, "args": targs, "risk": risk}
                self._emit(action)
                approved = self.approval_cb(action) if self.approval_cb else True
                if not approved:
                    self._emit({"type": "denied", "tool": tname})
                    self.messages.append(ChatMessage("assistant", text or f"[attempt {tname}]"))
                    self.messages.append(ChatMessage("tool",
                        f"{tname} DENIED by operator. Propose a safer alternative or ask why."))
                    continue

            # ---- execute ----
            self._emit({"type": "tool_call", "step": step, "tool": tname, "args": targs, "risk": risk})
            result = self.bridge.call(tname, targs)
            ok = bool(result.get("ok"))
            raw = str(result.get("stdout", "") or result.get("chunks", "") or "")
            if "chunks" in result:
                raw = "\n".join(f"[{c.get('source')}] {str(c.get('text',''))[:500]}"
                                for c in result.get("chunks", []))
            err = result.get("stderr") or result.get("error") or ""
            shown, distilled = ctxmod.distill_tool_output(
                raw, tname, self._summarize, self.cfg.distill_over_chars)
            if ok and not (shown or "").strip():
                shown = ("(tool ran successfully but returned NO output / no findings — "
                         "do not invent results; treat as a negative result)")
            self._emit({"type": "tool_result", "tool": tname, "ok": ok,
                        "exit": result.get("exit"), "distilled": distilled,
                        "preview": (shown or err)[:600]})

            self.messages.append(ChatMessage("assistant", text or f"[invoking {tname}]"))
            self.messages.append(ChatMessage("tool",
                f"{tname} result: ok={ok} exit={result.get('exit')}\n{shown}"
                + (f"\nstderr: {str(err)[:300]}" if not ok and err else "")))

            if ok:
                executed[sig] = (shown or "")[:300]
                ok_tools.add(tname)
                self.plan.advance(ok=True)
                stuck = 0
            else:
                stuck += 1

            if stuck >= 2:
                self.messages.append(ChatMessage("user", prompts.REFLECT_TEMPLATE.format(
                    stuck=stuck, plan=self.plan.render(),
                    recent=f"last tool {tname} -> ok={ok}")))
                self._emit({"type": "reflect", "reason": "repeated failures"})
                stuck = 0

        # ---- wrap up: evidence-grounded synthesis (no hallucinated findings) ----
        if final is None:
            evidence = "\n".join(
                f"- {sig.split('|', 1)[0]}: {snippet}" for sig, snippet in executed.items()
            ) or "(no tool produced confirmed evidence)"
            final = self._summarize(
                "Write the FINAL ANSWER for the goal now. Report ONLY findings that are "
                "SUPPORTED by the EVIDENCE listed below (actual tool results). If no tool "
                "confirmed a vulnerability, say so explicitly and do NOT invent findings, "
                "CVEs, or proof-of-concepts.\n\nGoal: " + goal
                + "\n\nEVIDENCE (real tool results collected this session):\n" + evidence
            ) or "(no final answer produced)"
            self._emit({"type": "forced_final", "evidence_items": len(executed)})

        self.messages.append(ChatMessage("assistant", final))
        self._emit({"type": "final", "text": final, "plan": self.plan.render(),
                    "evidence_items": len(executed)})
        return {"final": final, "plan": self.plan.render(),
                "evidence": dict(executed), "transcript": str(self.session.path)}

    def close(self) -> None:
        self.session.close()
