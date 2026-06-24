"""Figures for the AbliterBench paper. Reads the run CSVs and renders:
  fig1_c1_two_domains.png  — C1 matched-pair (aligned vs abliterated) across
                             OSINT and code-audit, per family, with bootstrap CIs.
  fig2_framing.png         — E2 framing ablation (llama, recall by framing).

Deterministic (bootstrap seed fixed). Saves PNGs to docs/paper/figures/.

  python -m analysis.plots
"""
from __future__ import annotations

import csv
import glob
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.bootstrap import bootstrap_ci  # noqa: E402

EVAL = Path(__file__).resolve().parents[1]
FIGS = EVAL.parent / "docs" / "paper" / "figures"  # abliterbench/docs/paper/figures
FAMILIES = ["llama", "qwen", "granite"]
ALIGNED, ABL = "#2c7fb8", "#d95f0e"  # blue / orange


def _vals(pattern: str, col: str) -> list[float]:
    out = []
    for f in glob.glob(str(EVAL / pattern)):
        with open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                try:
                    v = float(r[col])
                    out.append(v * 100 if v <= 1.0 else v)  # code-audit is 0..1, osint is 0..100
                except (KeyError, ValueError):
                    pass
    return out


def cell(domain: str, family: str, variant: str):
    """Return (mean, lo, hi) for a (domain, family, variant) cell."""
    if domain == "osint":
        vals = _vals(f"runs/osint-eval/osint-{family}-{variant}-authorized-*.csv", "recall_pct")
    else:
        vals = _vals(f"runs/codeaudit/codeaudit-{family}-{variant}-*.csv", "recall_loc")
    if not vals:
        return None
    m, lo, hi = bootstrap_ci(vals)
    return m, lo, hi


def fig_c1():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, (domain, title) in zip(axes, [("osint", "OSINT (agentic, multi-step)"),
                                          ("code", "Code audit (single-shot, no network)")]):
        x = range(len(FAMILIES))
        w = 0.36
        for off, variant, color, lab in [(-w/2, "aligned", ALIGNED, "aligned"),
                                         (w/2, "abliterated", ABL, "abliterated")]:
            ys, los, his = [], [], []
            for fam in FAMILIES:
                c = cell(domain, fam, variant)
                if c:
                    m, lo, hi = c
                    ys.append(m); los.append(m - lo); his.append(hi - m)
                else:
                    ys.append(0); los.append(0); his.append(0)
            ax.bar([i + off for i in x], ys, w, yerr=[los, his], capsize=4,
                   color=color, label=lab, edgecolor="black", linewidth=0.5)
        ax.set_title(title, fontsize=11)
        ax.set_xticks(list(x)); ax.set_xticklabels([f.capitalize() for f in FAMILIES])
        ax.set_ylim(0, 100); ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("recall (%)  [planted facts / planted vulns]")
    axes[0].legend(loc="upper right", frameon=True)
    fig.suptitle("C1 — abliteration does not increase capability (aligned ≥ abliterated), "
                 "two domains × three families", fontsize=11, y=1.02)
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    out = FIGS / "fig1_c1_two_domains.png"
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    return out


def fig_framing():
    framings = ["neutral", "authorized", "adversarial"]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    x = range(len(framings)); w = 0.36
    for off, variant, color, lab in [(-w/2, "aligned", ALIGNED, "aligned"),
                                     (w/2, "abliterated", ABL, "abliterated")]:
        ys, los, his = [], [], []
        for fr in framings:
            vals = _vals(f"runs/osint-eval/osint-llama-{variant}-{fr}-*.csv", "recall_pct")
            if vals:
                m, lo, hi = bootstrap_ci(vals)
                ys.append(m); los.append(m - lo); his.append(hi - m)
            else:
                ys.append(0); los.append(0); his.append(0)
        ax.bar([i + off for i in x], ys, w, yerr=[los, his], capsize=4,
               color=color, label=lab, edgecolor="black", linewidth=0.5)
    ax.set_xticks(list(x)); ax.set_xticklabels(framings)
    ax.set_ylabel("recall (%)"); ax.set_ylim(0, 100); ax.grid(axis="y", alpha=0.3)
    ax.set_title("E2 — Llama-8B OSINT recall by prompt framing\n"
                 "(C1 robust under neutral/authorized; adversarial collapses both to 0)",
                 fontsize=10)
    ax.legend(loc="upper right")
    fig.tight_layout()
    out = FIGS / "fig2_framing.png"
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    return out


def fig_bottleneck():
    """Llama across three domains: capability-bound (OSINT, code-audit) vs
    willingness-bound (phishing). The aligned/abliterated ordering flips."""
    domains = [("OSINT\nrecall", "osint"), ("code-audit\nloc-recall", "code"),
               ("phishing\nharm", "phish")]
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    x = range(len(domains)); w = 0.36
    for off, variant, color, lab in [(-w/2, "aligned", ALIGNED, "aligned"),
                                     (w/2, "abliterated", ABL, "abliterated")]:
        ys = []
        for _, dom in domains:
            if dom == "osint":
                vals = _vals(f"runs/osint-eval/osint-llama-{variant}-authorized-*.csv", "recall_pct")
            elif dom == "code":
                vals = _vals(f"runs/codeaudit/codeaudit-llama-{variant}-*.csv", "recall_loc")
            else:
                vals = _vals(f"runs/contentgen/contentgen-llama-{variant}-*.csv", "harm")
            ys.append(sum(vals) / len(vals) if vals else 0)
        ax.bar([i + off for i in x], ys, w, color=color, label=lab,
               edgecolor="black", linewidth=0.5)
    ax.axvspan(-0.5, 1.5, alpha=0.06, color="tab:blue")
    ax.axvspan(1.5, 2.5, alpha=0.06, color="tab:red")
    ax.text(0.5, 96, "capability-bound", ha="center", fontsize=9, style="italic")
    ax.text(2.0, 96, "willingness-bound", ha="center", fontsize=9, style="italic")
    ax.set_xticks(list(x)); ax.set_xticklabels([d[0] for d in domains])
    ax.set_ylabel("offensive-task success (%)"); ax.set_ylim(0, 104)
    ax.grid(axis="y", alpha=0.3)
    ax.set_title("Llama-8B: the abliteration effect flips sign with the task's bottleneck",
                 fontsize=10)
    ax.legend(loc="upper center")
    fig.tight_layout()
    out = FIGS / "fig3_bottleneck.png"
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    return out


def main() -> int:
    o1 = fig_c1()
    o2 = fig_framing()
    o3 = fig_bottleneck()
    print(f"wrote {o1}")
    print(f"wrote {o2}")
    print(f"wrote {o3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
