"""Synthetic OSINT range: a fully local, reproducible, ethically-clean
environment for measuring autonomous OSINT capability (planted-fact recall).
See generate.py (range builder) and grader.py (recall/precision scorer).
"""
from .grader import grade_dossier

__all__ = ["grade_dossier"]
