"""Fast, deterministic verification of the operator scaffolding — no LLM/GPU.

Runs in <1s. Exercises the pure logic (scope, planner, loose-parse, sanitize)
and drives the full agent loop with a SCRIPTED fake LLM + fake bridge so the
control flow (loose recovery, scope block, dedupe, evidence-grounded final) is
asserted without touching Ollama. Optionally smoke-tests the live bridge
workspace with --live.

Usage:
  ./../envs/operator/Scripts/python.exe operator_selftest.py
  python operator_selftest.py --live      # also hit the Kali bridge workspace
Exit code 0 = all pass, 1 = failure.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from abliterbench.llm_client import ToolCall  # noqa: E402
from abliterbench.operator.loop import (  # noqa: E402
    Operator, OperatorConfig, example_call, loose_calls, sanitize_args, schema_echo)
from abliterbench.operator.planner import Plan  # noqa: E402
from abliterbench.operator.scope import Scope  # noqa: E402
from abliterbench.operator import tools as T  # noqa: E402

_FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _FAILS.append(name)


# ---------------------------------------------------------------------------
# 1. Pure logic
# ---------------------------------------------------------------------------
def test_pure() -> None:
    print("pure logic:")
    s = Scope()
    check("scope allows lab IP", s.check("nmap_scan", {"target": "127.0.0.1"})[0])
    check("scope blocks external IP", not s.check("nmap_scan", {"target": "8.8.8.8"})[0])
    check("scope allows lab URL", s.check("httpx_probe", {"domain": "http://127.0.0.1:3000"})[0])
    check("scope blocks external host", not s.check("nuclei_scan", {"url": "http://example.com"})[0])
    check("no-target tool passes", s.check("rag_search", {"query": "x"})[0])
    check("risk passive", s.risk("rag_search") == "passive")
    check("risk intrusive", s.risk("sqlmap") == "intrusive")
    check("identity osint escalates", s.risk("maigret", {"username": "bob"}) == "intrusive")
    check("identity osint allowed", Scope(allow_identity_osint=True).risk("maigret", {"username": "b"}) == "active")

    p = Plan.from_text("1. Probe host\n2. Scan vulns\n3. Report")
    check("plan parses 3 steps", len(p.steps) == 3)
    p.advance(True)
    check("plan advances", p.current.text == "Scan vulns" and p.progress() == (1, 3))

    c = loose_calls('call nuclei_scan(url="http://127.0.0.1:3000")', {"nuclei_scan"})
    check("loose parse kwargs", bool(c) and c[0].name == "nuclei_scan")
    c = loose_calls('run rag_search(query="x", top_k=3)', {"rag_search"})
    check("loose parse int coercion", c[0].arguments.get("top_k") == 3)
    check("loose ignores unknown tool", loose_calls('foo(bar=1)', {"nuclei_scan"}) == [])
    a = sanitize_args({"domain": {"type": "string", "value": "http://h:3000"}})
    check("sanitize unwraps schema echo", a == {"domain": "http://h:3000"})
    check("schema_echo detects pasted schema",
          schema_echo({"query": {"type": "string", "description": "q"}}) is True)
    check("schema_echo passes real args", schema_echo({"query": "linux suid", "top_k": 3}) is False)
    check("example_call builds hint", "rag_search(" in example_call("rag_search"))

    check("catalog has workspace+rag", {"run_python", "rag_search", "write_file"} <= {t.name for t in T.CATALOG})
    check("run_python fixed lang", T.find_tool("run_python").fixed == {"lang": "python"})


# ---------------------------------------------------------------------------
# 2. Full loop with scripted fake LLM + fake bridge
# ---------------------------------------------------------------------------
class _Resp:
    def __init__(self, text="", calls=None, mode="native"):
        self.text = text
        self.parsed_tool_calls = calls or []
        self.tool_calling_mode = mode
        self.tokens_per_second = 50.0
        self.completion_tokens = 20
        self.prompt_tokens = 100


class _FakeClient:
    """Scripts a run that triggers loose-parse, scope-block, dedupe, then final."""
    def __init__(self):
        self.turn = 0
        self.script = [
            # 1: narrate a call (no native) -> loose_calls must recover it
            _Resp(text='I will run run_bash(code="echo lab")'),
            # 2: native call to out-of-scope target -> scope_block
            _Resp(text="scanning", calls=[ToolCall("nmap_scan", {"target": "8.8.8.8"})]),
            # 3: native call, in scope, succeeds
            _Resp(text="probing", calls=[ToolCall("httpx_probe", {"domain": "http://127.0.0.1:3000"})]),
            # 4: repeat identical successful call -> dedupe
            _Resp(text="again", calls=[ToolCall("httpx_probe", {"domain": "http://127.0.0.1:3000"})]),
            # 5: model finishes
            _Resp(text="FINAL ANSWER: done, in-scope probe returned 200."),
        ]

    def health(self):
        return True

    def supports_native_tools(self, model):
        return True

    def generate(self, model, prompt, seed=None, sampling=None):
        class _G:
            text = "1. recover narrated call\n2. probe host\n3. report"
        return _G()

    def chat_with_tools(self, model, messages, tools, seed=None, sampling=None):
        r = self.script[min(self.turn, len(self.script) - 1)]
        self.turn += 1
        return r


class _FakeBridge:
    def health(self):
        return True, 58

    def call(self, name, args, timeout_s=None):
        if name == "run_bash":
            return {"ok": True, "exit": 0, "stdout": "lab\n"}
        if name == "httpx_probe":
            return {"ok": True, "exit": 0, "stdout": "http://127.0.0.1:3000 [200] [Juice Shop]"}
        return {"ok": True, "exit": 0, "stdout": "ok"}


def test_loop() -> None:
    print("agent loop (scripted):")
    events: list[dict] = []
    cfg = OperatorConfig(model_tag="fake", model_alias="selftest", rag_auto=False,
                         approval_policy="auto", max_steps=8)
    op = Operator(cfg, scope=Scope(), on_event=events.append)
    op.client = _FakeClient()
    op.bridge = _FakeBridge()
    op._summarize = lambda prompt: ("1. step\n2. step" if "numbered plan" in prompt.lower()
                                    else "FINAL ANSWER: evidence-grounded summary.")
    result = op.run_task("Probe the in-scope lab host and report.")
    op.close()

    types = [e["type"] for e in events]
    check("emitted a plan", "plan" in types)
    check("loose-parse recovered narrated call", "loose_parse" in types)
    check("scope blocked out-of-scope target", "scope_block" in types)
    block = next(e for e in events if e["type"] == "scope_block")
    check("scope block was the external IP", "8.8.8.8" in block["reason"])
    check("dedupe fired on repeat call", "dedupe" in types)
    check("a tool executed ok", any(e["type"] == "tool_result" and e["ok"] for e in events))
    check("produced final", "final" in types and result.get("final"))
    check("no out-of-scope tool ran", not any(
        e["type"] == "tool_call" and str(e.get("args", {})).find("8.8.8.8") >= 0 for e in events))


# ---------------------------------------------------------------------------
# 3. Live bridge workspace smoke (optional)
# ---------------------------------------------------------------------------
def test_live(bridge_url: str) -> None:
    print("live bridge workspace:")
    b = T.Bridge(bridge_url)
    ok, n = b.health()
    check("bridge reachable", ok, f"{bridge_url}")
    if not ok:
        return
    w = b.call("write_file", {"path": "selftest.py", "content": "print(6*7)\n"})
    check("fs_write ok", w.get("ok"))
    r = b.call("run_python", {"file": "selftest.py"})
    check("run_python executes", r.get("ok") and "42" in r.get("stdout", ""))
    trav = b.call("read_file", {"path": "../../etc/passwd"})
    check("traversal blocked", not trav.get("ok"))
    rag = b.call("rag_search", {"query": "suid privilege escalation", "corpus": "gtfobins", "top_k": 1}, timeout_s=60)
    check("rag_search returns chunks", rag.get("ok") and rag.get("n", 0) >= 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="also smoke the live Kali bridge")
    ap.add_argument("--bridge", default="http://127.0.0.1:8765")
    args = ap.parse_args()

    test_pure()
    test_loop()
    if args.live:
        test_live(args.bridge)

    print()
    if _FAILS:
        print(f"FAILED ({len(_FAILS)}): {', '.join(_FAILS)}")
        return 1
    print("ALL SELFTESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
