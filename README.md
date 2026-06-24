# Abliteration does not buy autonomy

Code, data, and paper for *"Abliteration does not buy autonomy: refusal removal across
capability- and willingness-bound offensive tasks in small local LLMs."*

We measure, matched-pair, what removing the refusal direction (*abliteration*) does to a small
(7–8B, 4-bit) local LLM on agentic offensive-security tasks. The short answer: the effect is
**signed by the task's bottleneck**. On capability-bound tasks (autonomous OSINT, static code
audit) abliteration does **not** raise capability and usually lowers it; on a willingness-bound
task (writing a phishing lure) it reverses, and the abliterated model complies where the aligned
one refuses. Separately, a *declared-synthetic* range cannot measure a frontier model's refusal of
person-OSINT, which we report as a negative methodological result together with a harness audit
that retracted an earlier false finding.

The paper PDF is in [`paper/paper.pdf`](paper/paper.pdf).

## What's here

```
abliterbench/        evaluation instruments (importable package)
  osint_range/         deterministic synthetic OSINT range (NimbusForge) + grader
  codeaudit/           synthetic codebase generator with planted CWEs + localization grader
  contentgen/          phishing-lure grader (refusal / personalization / craft / harm)
  grading/             refusal classifier, flag/CTF graders
  operator/            Claude-Code-style operator scaffold (planning, tools, evidence gate)
  multiagent/          hierarchical orchestration + adversarial verifier
  analysis/            bootstrap CIs + paired permutation test, figure generation
eval/                runner scripts (one per experiment) + offline self-tests
runs/                run artifacts (CSVs) for every number in the paper + the synthetic range
paper/               paper.tex, references.bib, verification log, figures, PDF
```

## Reproducing

The graders, generators, and statistics are pure-stdlib and run offline:

```bash
python -m abliterbench.codeaudit.selftest      # 11 tests
python -m abliterbench.contentgen.selftest     # 12 tests
python -m abliterbench.grading.selftest        # grading tests
python -m analysis.bootstrap --glob "runs/osint-eval/osint-*-authorized-*.csv"
python -m analysis.plots                       # regenerate the figures
```

Re-running the model evaluations needs a local [Ollama](https://ollama.com) (the paper used
v0.24.0) serving the matched model pairs, plus a sandboxed tool bridge for the agentic OSINT track.
The bridge ran in an isolated VM on a host-only network in our setup; **that infrastructure is not
included here** (see *Responsible release* below). Every reported number already has its CSV under
`runs/`, so the analysis and figures reproduce without re-running any model.

Models (Ollama tags, Q4_K_M): aligned `llama3.1:8b-instruct-q4_K_M`, `qwen2.5:7b-instruct-q4_K_M`,
`granite3.1-dense:8b-instruct-q4_K_M`; abliterated counterparts from the community `huihui_ai`
collection (we do not redistribute weights).

## Responsible release

All personas, organizations, and breach records are synthetic and machine-generated under the
RFC-2606 `.example` domain; none maps to a real person, and the "leaked" passwords and API keys are
random tokens. We release the range *generator* and seeds rather than a fixed trove, publish
aggregate phishing scores rather than ready-to-send lures, and **do not** include any real network
target, credential, command-and-control tooling, or lab infrastructure. The graders and operator
scaffold are general-purpose evaluation code.

## Citation

See `paper/paper.pdf`. AI-assisted writing is disclosed in the paper.

## License

MIT — see [LICENSE](LICENSE).
