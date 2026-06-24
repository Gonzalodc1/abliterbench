"""Evidence-grounded mission report.

Deterministic by default: the report lists ONLY verified findings with their
evidence, plus what was rejected and why. This is the structural guarantee
against the single-agent failure where the model invents a polished report.
An optional LLM executive summary is constrained to the verified set.
"""
from __future__ import annotations

from collections.abc import Callable

from .blackboard import Blackboard
from .schemas import MissionState

_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def build_report(state: MissionState, bb: Blackboard,
                 summary_fn: Callable[[str], str] | None = None) -> str:
    verified = sorted(state.verified_findings, key=lambda f: _SEV_ORDER.get(f.severity, 9))
    rejected = state.rejected_findings

    lines = [f"# Red-team mission report — {state.target}", ""]
    lines.append(f"Phase reached: {state.phase} | subtasks: {state.subtasks_run} | "
                 f"scope blocks: {state.scope_blocks}")
    s = bb.summary()
    lines.append(f"Attack surface: {len(s['hosts'])} host(s), {len(s['services'])} service(s), "
                 f"{len(s['urls'])} URL(s).")
    lines.append("")
    lines.append(f"## Verified findings ({len(verified)})")
    if not verified:
        lines.append("- None confirmed by tool evidence. (No fabricated findings included.)")
    for f in verified:
        lines.append(f"- [{f.severity.upper()}] {f.title}  (host={f.host or '?'}, via {f.source_tool or f.role})")
        lines.append(f"    evidence: {f.evidence_quote[:200]}")
    lines.append("")
    lines.append(f"## Rejected / unverified claims ({len(rejected)})  — excluded from findings")
    for v in state.verdicts:
        if not v.accepted:
            lines.append(f"- {v.finding.title}  → {v.reason}")
    report = "\n".join(lines)

    if summary_fn and verified:
        try:
            ev = "\n".join(f"- [{f.severity}] {f.title}: {f.evidence_quote[:150]}" for f in verified)
            summ = summary_fn(
                "Write a 3-4 sentence executive summary of this red-team engagement using ONLY the "
                "VERIFIED findings below. Do not add findings, CVEs, or claims not listed.\n\n"
                f"Target: {state.target}\nVERIFIED FINDINGS:\n{ev}").strip()
            if summ:
                report = f"# Executive summary\n{summ}\n\n" + report
        except Exception:
            pass
    return report
