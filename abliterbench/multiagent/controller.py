"""MissionController — deterministic orchestration of the red-team mission.

The control flow is plain Python (a state machine), NOT an LLM. The mission
state lives in the Blackboard, so no single agent has to hold the long horizon
in-context — which is the whole point (anti-cliff).

agent_configs ladder (for the Track-3 experiment):
  1 = single generalist operator, NO verification        (baseline; hallucination visible)
  2 = controller + recon + 1 generalist worker + verifier (deterministic gate)
  3 = controller + recon + SPECIALISED workers + verifier (deterministic gate)
  4 = config 3 + adversarial SKEPTIC panel on the verifier (full)
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..config import Sampling
from ..llm_client import OllamaClient
from ..operator.loop import Operator, OperatorConfig
from ..operator.scope import Scope
from .blackboard import Blackboard
from .extract import extract_findings
from .roles import INTRUSIVE_ROLES, ROLES, Role
from .schemas import MissionState, Subtask, Verdict, WorkerResult
from .synthesis import build_report
from .verifier import Verifier

GENERALIST = Role(
    name="generalist", description="single-agent operator (baseline)",
    tools_filter="all",
    persona=None or "",  # None -> Operator uses the default red-team persona
    max_steps=14, min_tools=2)


@dataclass
class MissionResult:
    target: str
    config: int
    report: str
    state: MissionState
    metrics: dict[str, Any] = field(default_factory=dict)


class MissionController:
    def __init__(self, config: int, model_tag: str, scope: Scope | None = None,
                 host: str = "http://localhost:11434", bridge_url: str = "http://127.0.0.1:8765",
                 on_event: Callable[[dict], None] | None = None,
                 approval_cb: Callable[[dict], bool] | None = None,
                 seed: int | None = 42, n_votes: int = 3, max_web_targets: int = 2) -> None:
        self.config = config
        self.model_tag = model_tag
        self.scope = scope or Scope()
        self.host = host
        self.bridge_url = bridge_url
        self.on_event = on_event or (lambda e: None)
        self.approval_cb = approval_cb
        self.seed = seed
        self.max_web_targets = max_web_targets
        self.client = OllamaClient(host=host, timeout_s=600.0)
        self.sampling = Sampling(temperature=0.3)
        self.verifier = Verifier(skeptic_fn=(self._gen if config >= 4 else None), n_votes=n_votes)

    # ---- llm helper for extraction / skeptic / summary --------------------
    def _gen(self, prompt: str) -> str:
        try:
            return self.client.generate(self.model_tag, prompt, seed=self.seed,
                                        sampling=self.sampling).text or ""
        except Exception:
            return ""

    def _emit(self, ev: dict) -> None:
        self.on_event(ev)

    # ---- run one worker (a reused Operator) -------------------------------
    def _run_worker(self, role: Role, goal: str, context: str = "") -> tuple[WorkerResult, int]:
        ev: list[dict] = []
        policy = "intrusive" if role.name in INTRUSIVE_ROLES else role.approval_policy
        cfg = OperatorConfig(
            model_tag=self.model_tag, model_alias=f"ma-{role.name}", host=self.host,
            bridge_url=self.bridge_url, tools_filter=role.tools_filter,
            system_prompt=(role.persona or None), fewshot="",
            max_steps=role.max_steps, seed=self.seed, approval_policy=policy,
            rag_auto=("rag" in role.tools_filter), rag_corpora=role.rag_corpora,
            min_successful_tools=role.min_tools)
        full_goal = (f"{goal}\n\nContext from prior recon:\n{context}" if context else goal)
        self._emit({"type": "subtask", "role": role.name, "goal": goal[:120]})
        try:
            op = Operator(cfg, scope=self.scope, on_event=ev.append, approval_cb=self.approval_cb)
            res = op.run_task(full_goal)
            op.close()
            tools_ok = sorted({e["tool"] for e in ev if e["type"] == "tool_result" and e.get("ok")})
            steps = max([e.get("step", 0) for e in ev if e["type"] == "step_start"] + [0])
            wr = WorkerResult(role=role.name, goal=goal, final_text=res.get("final", ""),
                              evidence=res.get("evidence", {}), tools_ok=tools_ok, steps=steps)
        except Exception as e:
            wr = WorkerResult(role=role.name, goal=goal, final_text="", error=str(e))
        scope_blocks = sum(1 for e in ev if e["type"] == "scope_block")
        self._emit({"type": "subtask_done", "role": role.name, "tools_ok": wr.tools_ok,
                    "evidence_items": len(wr.evidence), "error": wr.error})
        return wr, scope_blocks

    # ---- main entry -------------------------------------------------------
    def run_mission(self, target: str, goal: str) -> MissionResult:
        t0 = time.time()
        bb = Blackboard(target=target)
        state = MissionState(target=target)
        self._emit({"type": "mission_start", "config": self.config, "target": target})

        def collect(wr: WorkerResult, sb: int) -> None:
            state.worker_results.append(wr)
            state.subtasks_run += 1
            state.scope_blocks += sb
            bb.ingest_evidence(wr.evidence)
            if wr.error:
                state.errors.append(f"{wr.role}: {wr.error}")

        # ---- config 1: single generalist, no orchestration, no verification
        if self.config <= 1:
            state.phase = "SINGLE"
            wr, sb = self._run_worker(GENERALIST, goal)
            collect(wr, sb)
            cands = extract_findings(wr, self._gen)
            state.candidate_findings = cands
            for f in cands:  # baseline: claims accepted UNVERIFIED (so hallucination is visible)
                state.verdicts.append(Verdict(finding=f, grounded=False, accepted=True,
                                              reason="unverified (single-agent baseline)"))
            return self._finish(state, bb, t0)

        # ---- config >=2: orchestrated ----
        state.phase = "RECON"
        recon_wr, sb = self._run_worker(ROLES["recon"],
                                        f"Enumerate the attack surface of {target}: live ports, "
                                        f"services, HTTP stack and URLs. Do not exploit.")
        collect(recon_wr, sb)

        state.phase = "TRIAGE"
        web_targets = bb.web_targets() or [target if target.startswith("http") else f"http://{target}"]
        self._emit({"type": "triage", "web_targets": web_targets[:self.max_web_targets]})

        state.phase = "ENUMERATE"
        specialised = self.config >= 3
        role = ROLES["web_exploit"] if specialised else GENERALIST
        for t in web_targets[: self.max_web_targets]:
            wr, sb = self._run_worker(
                role, f"Assess the web application at {t}: identify the stack and any vulnerabilities. "
                      f"Quote the exact tool output evidencing each finding.",
                context=bb.slice_for(role.name))
            collect(wr, sb)
            state.candidate_findings.extend(extract_findings(wr, self._gen))

        state.phase = "VERIFY"
        corpus = "\n".join(f"[{k.split('|',1)[0]}] {v}" for k, v in bb.evidence.items())
        seen: set[str] = set()
        for f in state.candidate_findings:
            if f.key() in seen:
                continue
            seen.add(f.key())
            verdict = self.verifier.verify(f, corpus)
            state.verdicts.append(verdict)
            self._emit({"type": "verdict", "title": f.title[:80], "accepted": verdict.accepted,
                        "reason": verdict.reason})

        return self._finish(state, bb, t0)

    def _finish(self, state: MissionState, bb: Blackboard, t0: float) -> MissionResult:
        state.phase = "SYNTHESIZE"
        report = build_report(state, bb, summary_fn=(self._gen if self.config >= 2 else None))
        all_ok_tools = sorted({t for wr in state.worker_results for t in wr.tools_ok})
        claimed = len(state.candidate_findings)
        verified = len(state.verified_findings)
        metrics = {
            "config": self.config,
            "subtasks": state.subtasks_run,
            "distinct_ok_tools": len(all_ok_tools),
            "ok_tools": all_ok_tools,
            "candidate_findings": claimed,
            "verified_findings": verified,
            "rejected_findings": len(state.rejected_findings),
            # findings claimed but not evidence-verified — proxy for hallucination removed
            "hallucination_delta": claimed - verified if self.config >= 2 else None,
            "scope_blocks": state.scope_blocks,
            "errors": len(state.errors),
            "wall_s": round(time.time() - t0, 1),
        }
        self._emit({"type": "mission_done", **metrics})
        return MissionResult(target=state.target, config=self.config, report=report,
                             state=state, metrics=metrics)
