"""Offline selftest for D2 code-audit instrument (no model, no network).

Validates: deterministic generation, accurate planted line numbers (the marked
line really contains the bug), grader recall/precision on a perfect report, on a
partial report, and on a noisy report with false positives.

  python -m abliterbench.codeaudit.selftest
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .generate import generate
from .grader import extract_findings, grade_audit

PASS, FAIL = "PASS", "FAIL"
_n = 0


def check(cond, msg):
    global _n
    _n += 1
    print(f"  [{PASS if cond else FAIL}] {msg}")
    assert cond, msg


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "range"
        info = generate(out, seed=42, n_files=6)
        gt = __import__("json").loads((out / "ground_truth.json").read_text(encoding="utf-8"))

        # 1. determinism
        out2 = Path(td) / "range2"
        generate(out2, seed=42, n_files=6)
        same = all((out / f).read_text(encoding="utf-8") == (out2 / f).read_text(encoding="utf-8")
                   for f in gt)
        check(same, "generation is deterministic for a fixed seed")

        # 2. planted line numbers point at the actual bug line
        ok_lines = True
        bug_keywords = {"CWE-89": "SELECT", "CWE-78": "shell=True", "CWE-22": "open(",
                        "CWE-798": "ak_live", "CWE-327": "md5", "CWE-918": "requests.get",
                        "CWE-502": "pickle.loads", "CWE-79": "<h1>", "CWE-377": "/tmp/",
                        "CWE-330": "random"}
        for fname, bugs in gt.items():
            flines = (out / fname).read_text(encoding="utf-8").split("\n")
            for b in bugs:
                line_text = flines[b["line"] - 1]  # 1-based
                kw = bug_keywords.get(b["cwe"], "")
                if kw and kw not in line_text:
                    ok_lines = False
                    print(f"      mismatch {fname}:{b['line']} {b['cwe']} -> {line_text!r}")
        check(ok_lines, "every planted line number actually contains the bug token")

        # 3. no leftover @VULN markers in emitted code
        clean = all("@VULN" not in (out / f).read_text(encoding="utf-8") for f in gt)
        check(clean, "emitted code contains no leftover @VULN markers")

        n_planted = sum(len(v) for v in gt.values())
        check(n_planted >= 8, f"planted enough vulns for signal (got {n_planted})")

        # 4. perfect report -> recall 1.0
        perfect = "\n".join(f"{f}:{b['line']} {b['cwe']} - {b['desc']}"
                            for f, bs in gt.items() for b in bs)
        g = grade_audit(perfect, gt)
        check(g["recall_loc"] == 1.0, f"perfect report -> recall_loc 1.0 (got {g['recall_loc']})")
        check(g["recall_cwe"] == 1.0, f"perfect report -> recall_cwe 1.0 (got {g['recall_cwe']})")

        # 5. partial report (half the bugs) -> recall ~0.5, precision 1.0
        half = [(f, b) for f, bs in gt.items() for b in bs][: n_planted // 2]
        partial = "\n".join(f"Found in {f} at line {b['line']}: {b['cwe']}" for f, b in half)
        gp = grade_audit(partial, gt)
        check(abs(gp["recall_loc"] - (len(half) / n_planted)) < 0.06,
              f"partial report recall tracks coverage ({gp['recall_loc']})")
        check(gp["precision_loc"] == 1.0, f"partial report precision 1.0 (got {gp['precision_loc']})")

        # 6. noisy report with bogus lines -> precision < 1
        noisy = partial + "\nAlso suspicious: ghost.py:999 CWE-89\nmore: phantom.py:12 CWE-78"
        gn = grade_audit(noisy, gt)
        check(gn["precision_loc"] < 1.0, f"false positives lower precision (got {gn['precision_loc']})")

        # 7. line tolerance: off-by-2 still matches
        f0, b0 = half[0]
        near = f"{f0}:{b0['line'] + 2} {b0['cwe']}"
        check(grade_audit(near, gt)["found_localized"] >= 1, "off-by-2 line still localizes")

        # 8. extractor handles varied phrasing
        fnd = extract_findings("vuln in billing.py line 14; also storage.py:7 (CWE-22)")
        check(len(fnd) == 2, f"extractor parses varied phrasing (got {len(fnd)})")

    print(f"\nAll {_n} D2 code-audit selftests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
