"""Extract candidate Findings from a worker's report.

The worker is asked to QUOTE the evidence line for each claim; we parse those
into Finding objects. The quote is later cross-checked by the Verifier against
the real evidence corpus (deterministic anti-hallucination gate), so even if the
extractor is lenient, fabricated findings cannot survive.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable

from .schemas import Finding, WorkerResult

_EXTRACT_PROMPT = """From the WORKER REPORT and its EVIDENCE, extract concrete security findings as a \
JSON array. Each item: {{"title": str, "host": str, "severity": "info|low|medium|high|critical", \
"source_tool": str, "evidence_quote": str}}. The evidence_quote MUST be copied VERBATIM from the \
EVIDENCE block (a real line proving the finding). If a claim has no supporting evidence line, DO \
NOT include it. If there are no real findings, output [].

WORKER REPORT:
{report}

EVIDENCE:
{evidence}

Output ONLY the JSON array."""


def _parse_json_array(text: str) -> list[dict]:
    m = re.search(r"\[.*\]", text or "", re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def extract_findings(wr: WorkerResult, generate_fn: Callable[[str], str]) -> list[Finding]:
    """Use an LLM call to pull structured findings; robust to malformed output."""
    if wr.error:
        return []
    evidence = wr.evidence_blob()[:4000]
    try:
        raw = generate_fn(_EXTRACT_PROMPT.format(report=(wr.final_text or "")[:2000], evidence=evidence))
    except Exception:
        raw = ""
    out: list[Finding] = []
    for d in _parse_json_array(raw):
        if not isinstance(d, dict) or not d.get("title"):
            continue
        out.append(Finding(
            title=str(d.get("title", ""))[:160],
            detail=str(d.get("detail", ""))[:400],
            host=str(d.get("host", ""))[:64],
            severity=str(d.get("severity", "info")).lower(),
            source_tool=str(d.get("source_tool", ""))[:40],
            evidence_quote=str(d.get("evidence_quote", ""))[:300],
            role=wr.role,
        ))
    return out
