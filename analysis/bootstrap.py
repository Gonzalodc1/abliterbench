"""Bootstrap confidence intervals + aggregation over OSINT eval CSVs (E1/E2).

Pure stdlib (deterministic with a fixed seed). Groups rows by (model, framing)
and reports mean + 95% bootstrap CI for recall, precision and refusal-rate.

  python -m analysis.bootstrap --glob "runs/osint-eval/osint-llama-*.csv"
"""
from __future__ import annotations

import argparse
import csv
import glob as globmod
import random
import statistics as st


def bootstrap_ci(values: list[float], iters: int = 5000, alpha: float = 0.05,
                 seed: int = 1234) -> tuple[float, float, float]:
    """Return (mean, lo, hi) for a 1-alpha bootstrap CI of the mean."""
    if not values:
        return 0.0, 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0], values[0]
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(iters):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((alpha / 2) * iters)]
    hi = means[int((1 - alpha / 2) * iters)]
    return st.mean(values), lo, hi


def paired_permutation_test(diffs: list[float], iters: int = 20000,
                            seed: int = 1234) -> tuple[float, float]:
    """Two-sided paired permutation (sign-flip) test on paired differences
    diffs[i] = score_aligned[i] - score_abliterated[i] for matched units (the
    same persona/seed under both twins). Returns (mean_diff, p_value). The pairing
    is the matched-pair design, so sign-flipping is the correct exchangeability."""
    if not diffs:
        return 0.0, 1.0
    rng = random.Random(seed)
    n = len(diffs)
    obs = sum(diffs) / n
    if obs == 0:
        return 0.0, 1.0
    count = 0
    for _ in range(iters):
        s = sum(d if rng.random() < 0.5 else -d for d in diffs) / n
        if abs(s) >= abs(obs) - 1e-12:
            count += 1
    return obs, (count + 1) / (iters + 1)


def _num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def load_rows(glob_pat: str) -> list[dict]:
    rows = []
    for f in sorted(globmod.glob(glob_pat)):
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            r["_file"] = f
            rows.append(r)
    return rows


def aggregate(rows: list[dict]) -> dict[tuple, dict]:
    """Group by (model, framing) -> metric -> (mean, lo, hi). Also refusal-rate."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        key = (r.get("model", "?"), r.get("framing", "-"))
        groups.setdefault(key, []).append(r)
    out = {}
    for key, rs in groups.items():
        recall = [_num(r.get("recall_pct")) for r in rs if r.get("recall_pct") not in (None, "")]
        prec = [_num(r.get("precision_pct")) for r in rs if r.get("precision_pct") not in (None, "")]
        refused = [1.0 if str(r.get("refused")).lower() in ("true", "1") else 0.0
                   for r in rs if "refused" in r]
        out[key] = {
            "n": len(rs),
            "recall": bootstrap_ci(recall),
            "precision": bootstrap_ci(prec),
            "refusal_rate": (st.mean(refused) * 100 if refused else 0.0),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="runs/osint-eval/osint-llama-*.csv")
    args = ap.parse_args()
    rows = load_rows(args.glob)
    agg = aggregate(rows)
    print(f"{'model':<22}{'framing':<12}{'n':<4}{'recall% (95% CI)':<26}{'prec%':<8}{'refusal%'}")
    print("-" * 86)
    for (model, framing), m in sorted(agg.items()):
        rm, rlo, rhi = m["recall"]
        pm, _, _ = m["precision"]
        print(f"{model:<22}{framing:<12}{m['n']:<4}"
              f"{f'{rm:.0f} [{rlo:.0f},{rhi:.0f}]':<26}{pm:<8.0f}{m['refusal_rate']:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
