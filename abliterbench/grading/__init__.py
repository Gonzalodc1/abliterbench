"""Execution-grounded grading — objective, machine-checkable scoring that
replaces the keyword-matching scorers (which inflated results, e.g. 79%->53%).

  flag       : CTF flag extraction + exact-match grading (Cybench/NYU/InterCode)
  juiceshop  : challenge-solved detection via the OWASP Juice Shop /api/Challenges
  osint      : (see abliterbench.osint_range.grader) planted-fact recall/precision
"""
from .flag import FLAG_PATTERNS, extract_flags, grade_flag
from .juiceshop import JuiceShopGrader

__all__ = ["extract_flags", "grade_flag", "FLAG_PATTERNS", "JuiceShopGrader"]
