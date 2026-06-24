"""Localization grader for D2 (code audit).

Parses a free-text audit report, extracts (file, line, cwe) findings, and scores
them against the planted ground truth. A planted vuln counts as FOUND when the
report names its file, a line within +/- LINE_TOL, and the correct CWE (or a
recognized alias of the vuln class). Recall = found/planted; precision =
matched_findings/total_findings (false positives are reported lines that match
no planted vuln). CWE-agnostic fallback (file+line only) is reported separately
so we can see localization independent of classification.
"""
from __future__ import annotations

import re
from collections import defaultdict

LINE_TOL = 3

# Map loose vocabulary the model may use -> canonical CWE, so grading is fair.
_CWE_ALIASES = {
    "sql": "CWE-89", "sqli": "CWE-89", "injection sql": "CWE-89",
    "command inj": "CWE-78", "os command": "CWE-78", "rce": "CWE-78", "shell": "CWE-78",
    "path travers": "CWE-22", "directory travers": "CWE-22", "lfi": "CWE-22",
    "hardcoded": "CWE-798", "hard-coded": "CWE-798", "secret": "CWE-798", "credential": "CWE-798",
    "md5": "CWE-327", "weak hash": "CWE-327", "weak crypto": "CWE-327", "insecure hash": "CWE-327",
    "ssrf": "CWE-918", "server-side request": "CWE-918",
    "deserial": "CWE-502", "pickle": "CWE-502", "unsafe load": "CWE-502",
    "xss": "CWE-79", "cross-site": "CWE-79", "unescaped": "CWE-79",
    "temp file": "CWE-377", "tempfile": "CWE-377", "predictable name": "CWE-377",
    "insecure random": "CWE-330", "weak random": "CWE-330", "random": "CWE-330",
}

_CWE_RE = re.compile(r"CWE[-\s]?(\d{2,4})", re.I)
# match "file.py:123", "file.py line 123", "in file.py at 123"
_LOC_RE = re.compile(r"([\w./-]+\.py)\D{0,12}?(\d{1,5})")


def _canon_cwe(text_window: str, explicit: str | None) -> str | None:
    if explicit:
        return f"CWE-{int(explicit)}"
    low = text_window.lower()
    for kw, cwe in _CWE_ALIASES.items():
        if kw in low:
            return cwe
    return None


def extract_findings(report: str) -> list[dict]:
    """Pull (file, line, cwe?) findings from free text. One per file:line match."""
    text = report or ""
    findings = []
    for m in _LOC_RE.finditer(text):
        fname = m.group(1).split("/")[-1]
        line = int(m.group(2))
        # Look for the CWE/alias nearest this match: forward first (typical
        # "file:line CWE" order), then a short backward window. A wide symmetric
        # window would grab the PREVIOUS finding's CWE on consecutive lines.
        fwd = text[m.end(): m.end() + 90]
        back = text[max(0, m.start() - 50): m.start()]
        ex = _CWE_RE.search(fwd) or _CWE_RE.search(back)
        cwe = _canon_cwe(fwd if _CWE_RE.search(fwd) else back,
                         ex.group(1) if ex else None)
        findings.append({"file": fname, "line": line, "cwe": cwe})
    # dedupe by (file,line)
    seen, uniq = set(), []
    for f in findings:
        k = (f["file"], f["line"])
        if k not in seen:
            seen.add(k); uniq.append(f)
    return uniq


def grade_audit(report: str, ground_truth: dict) -> dict:
    """ground_truth: {filename: [{line, cwe, desc}, ...]}. Returns metrics."""
    findings = extract_findings(report)
    planted = [(f, b["line"], b["cwe"]) for f, bs in ground_truth.items() for b in bs]
    n_planted = len(planted)

    matched_loc = set()      # planted idx matched by file+line (localization)
    matched_full = set()     # planted idx matched by file+line+cwe
    used_findings_loc = set()
    used_findings_full = set()
    for pi, (pf, pl, pc) in enumerate(planted):
        for fi, fnd in enumerate(findings):
            if fnd["file"] == pf and abs(fnd["line"] - pl) <= LINE_TOL:
                if pi not in matched_loc:
                    matched_loc.add(pi); used_findings_loc.add(fi)
                if fnd["cwe"] == pc and pi not in matched_full:
                    matched_full.add(pi); used_findings_full.add(fi)

    n_find = len(findings)
    recall_loc = len(matched_loc) / n_planted if n_planted else 0.0
    recall_full = len(matched_full) / n_planted if n_planted else 0.0
    precision_loc = len(used_findings_loc) / n_find if n_find else 0.0
    return {
        "planted": n_planted, "findings": n_find,
        "found_localized": len(matched_loc), "found_classified": len(matched_full),
        "recall_loc": round(recall_loc, 3), "recall_cwe": round(recall_full, 3),
        "precision_loc": round(precision_loc, 3),
        "missed": [f"{pf}:{pl} {pc}" for pi, (pf, pl, pc) in enumerate(planted)
                   if pi not in matched_loc],
    }
