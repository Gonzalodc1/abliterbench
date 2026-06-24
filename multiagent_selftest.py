"""Deterministic self-tests for the multi-agent layer — no LLM/GPU, <1s.

Verifies the orchestration and the anti-hallucination gate with fake workers +
fake LLM:
  * Blackboard auto-extracts hosts/URLs/services from recon evidence.
  * Verifier's deterministic gate REJECTS a finding whose quoted evidence is not
    in the collected corpus (the fabrication case) and ACCEPTS a grounded one.
  * The controller state machine runs RECON->...->VERIFY and computes the
    hallucination delta; scope is honoured.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from abliterbench.multiagent.blackboard import Blackboard           # noqa: E402
from abliterbench.multiagent.controller import MissionController     # noqa: E402
from abliterbench.multiagent.extract import extract_findings         # noqa: E402
from abliterbench.multiagent.schemas import Finding, WorkerResult    # noqa: E402
from abliterbench.multiagent.verifier import Verifier, quote_supported  # noqa: E402

_FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _FAILS.append(name)


def test_blackboard() -> None:
    print("blackboard:")
    bb = Blackboard(target="127.0.0.1")
    bb.ingest_evidence({
        "nmap|t": "22/tcp open ssh\n3000/tcp open http",
        "httpx|t": "http://127.0.0.1:3000 [200] [OWASP Juice Shop]",
    })
    check("extracts host", "127.0.0.1" in bb.hosts)
    check("extracts url", any("3000" in u for u in bb.urls))
    check("extracts services", any(s["port"] == 3000 for s in bb.services))
    check("web_targets found", any(":3000" in w for w in bb.web_targets()))


def test_verifier() -> None:
    print("verifier (deterministic gate):")
    corpus = "[nuclei] exposed .git/ directory found at /.git/HEAD\n[httpx] 200 OWASP Juice Shop"
    check("real quote supported", quote_supported("exposed .git/ directory found", corpus))
    check("fabricated quote rejected", not quote_supported("remote code execution confirmed via shell", corpus))
    v = Verifier(skeptic_fn=None)
    real = v.verify(Finding(title="exposed git", evidence_quote="exposed .git/ directory found"), corpus)
    fake = v.verify(Finding(title="rce", evidence_quote="remote code execution confirmed via shell"), corpus)
    check("grounded finding accepted", real.accepted)
    check("fabricated finding rejected", not fake.accepted)
    # skeptic panel: even grounded can be voted down
    vs = Verifier(skeptic_fn=lambda p: "FALSE", n_votes=3)
    check("skeptic panel can reject grounded", not vs.verify(
        Finding(title="x", evidence_quote="exposed .git/ directory found"), corpus).accepted)


def test_extract() -> None:
    print("extraction:")
    wr = WorkerResult(role="web_exploit", goal="g", final_text="found exposed git",
                      evidence={"nuclei|u": "exposed .git/ directory at /.git/"})
    fake_gen = lambda p: ('[{"title":"Exposed .git","host":"h","severity":"medium",'
                          '"source_tool":"nuclei","evidence_quote":"exposed .git/ directory at /.git/"}]')
    fs = extract_findings(wr, fake_gen)
    check("extracted one finding", len(fs) == 1 and fs[0].title.startswith("Exposed"))
    check("empty on no-json", extract_findings(wr, lambda p: "no findings here") == [])


def test_controller() -> None:
    print("controller (fake workers, config 4):")
    mc = MissionController(config=4, model_tag="fake", host="http://x", bridge_url="http://y")

    # fake worker results: recon finds a service; web worker claims 2 findings
    canned = {
        "recon": WorkerResult(role="recon", goal="", final_text="found web on 3000",
                              evidence={"httpx|t": "http://127.0.0.1:3000 [200] [OWASP Juice Shop]"},
                              tools_ok=["httpx_probe"], steps=2),
        "web_exploit": WorkerResult(role="web_exploit", goal="", final_text="found .git and claimed rce",
                                    evidence={"nuclei|u": "exposed .git/ directory found at /.git/HEAD"},
                                    tools_ok=["nuclei_scan"], steps=3),
    }
    mc._run_worker = lambda role, goal, context="": (canned.get(role.name, canned["web_exploit"]), 0)

    def fake_gen(prompt: str) -> str:
        if "JSON array" in prompt:   # extraction
            return ('[{"title":"Exposed .git directory","host":"127.0.0.1","severity":"medium",'
                    '"source_tool":"nuclei","evidence_quote":"exposed .git/ directory found at /.git/HEAD"},'
                    '{"title":"Remote code execution","host":"127.0.0.1","severity":"critical",'
                    '"source_tool":"nuclei","evidence_quote":"shell obtained via deserialization"}]')
        if "REAL or FALSE" in prompt or "REAL/FALSE" in prompt:
            return "REAL"
        return "executive summary"
    mc._gen = fake_gen
    mc.verifier = Verifier(skeptic_fn=fake_gen, n_votes=3)

    r = mc.run_mission("127.0.0.1", "Assess the lab web app and report findings.")
    m = r.metrics
    check("ran recon + enumerate subtasks", m["subtasks"] >= 2)
    check("collected candidate findings", m["candidate_findings"] == 2)
    check("verified the grounded finding", m["verified_findings"] == 1)
    check("rejected the fabricated finding", m["rejected_findings"] == 1)
    check("hallucination_delta = 1", m["hallucination_delta"] == 1)
    check("report excludes fabricated rce", "Remote code execution" not in r.report.split("Rejected")[0])
    check("report includes verified git finding", "Exposed .git" in r.report)


def main() -> int:
    test_blackboard()
    test_verifier()
    test_extract()
    test_controller()
    print()
    if _FAILS:
        print(f"FAILED ({len(_FAILS)}): {', '.join(_FAILS)}")
        return 1
    print("ALL MULTIAGENT SELFTESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
