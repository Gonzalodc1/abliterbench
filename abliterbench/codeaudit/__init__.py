"""Code/vuln-audit domain (D2) for AbliterBench multi-domain extension.

A deterministic generator plants known CWEs at known file:line positions in a
synthetic codebase; a localization grader scores recall/precision of the model's
findings. No network target — entirely local, so it avoids the infra flakiness
that contaminated the web-exploit track. Matched-pair (aligned vs abliterated)
runs reuse the operator scaffold.
"""
