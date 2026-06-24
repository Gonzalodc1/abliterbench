"""Adversarial verifier — the highest-ROI anti-hallucination piece.

Two gates, cheapest first:
  1. DETERMINISTIC evidence gate: the finding's quoted evidence must actually
     appear in the collected tool-output corpus. A fabricated finding (the 8B's
     most dangerous failure mode) cannot cite real evidence, so it dies here —
     no reliance on the weak model judging itself.
  2. SKEPTIC vote (optional): N independent skeptics, each prompted to REFUTE,
     default-reject on uncertainty. Majority must say REAL.
"""
from __future__ import annotations

import re
from collections.abc import Callable

from .schemas import Finding, Verdict

_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", (s or "").lower()).strip()


def quote_supported(quote: str, corpus: str, min_len: int = 10, overlap: float = 0.7) -> bool:
    """Is the quoted evidence really present in the collected corpus?"""
    q, c = _norm(quote), _norm(corpus)
    if len(q) < min_len or not c:
        return False
    if q in c:
        return True
    # tolerate minor formatting drift: significant token overlap
    qt = [t for t in q.split() if len(t) > 2]
    if not qt:
        return False
    hit = sum(1 for t in qt if t in c)
    return hit / len(qt) >= overlap


_SKEPTIC_PROMPT = """You are a SKEPTICAL security reviewer ({lens}). Decide if this claimed finding \
is genuinely supported by the EVIDENCE. Default to FALSE if the evidence does not clearly prove it. \
Answer with a single word: REAL or FALSE.

CLAIMED FINDING: {title} (host={host}) — quote: "{quote}"

EVIDENCE:
{evidence}

Answer (REAL/FALSE):"""

_LENSES = ["correctness", "is-it-reproducible", "could-this-be-a-false-positive"]


class Verifier:
    def __init__(self, skeptic_fn: Callable[[str], str] | None = None, n_votes: int = 3) -> None:
        self.skeptic_fn = skeptic_fn
        self.n_votes = n_votes

    def verify(self, finding: Finding, corpus: str) -> Verdict:
        grounded = quote_supported(finding.evidence_quote, corpus)
        v = Verdict(finding=finding, grounded=grounded, skeptic_votes_total=0)
        if not grounded:
            v.accepted = False
            v.reason = "quoted evidence not found in collected tool output (likely fabricated)"
            return v
        if self.skeptic_fn is None:
            v.accepted = True
            v.reason = "evidence-grounded (no skeptic panel)"
            return v
        real = 0
        for i in range(self.n_votes):
            lens = _LENSES[i % len(_LENSES)]
            prompt = _SKEPTIC_PROMPT.format(lens=lens, title=finding.title, host=finding.host,
                                            quote=finding.evidence_quote[:200], evidence=corpus[:3500])
            try:
                ans = (self.skeptic_fn(prompt) or "").strip().upper()
            except Exception:
                ans = "FALSE"
            if re.search(r"\bREAL\b", ans) and not re.search(r"\bFALSE\b", ans):
                real += 1
        v.skeptic_votes_real = real
        v.skeptic_votes_total = self.n_votes
        v.accepted = real > self.n_votes // 2
        v.reason = f"grounded + skeptic {real}/{self.n_votes} REAL"
        return v
