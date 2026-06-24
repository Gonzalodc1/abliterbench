"""Plan / todo ledger.

A small explicit plan the operator maintains and advances. This is the single
highest-impact scaffold for small models: it externalises long-horizon state
that an 8B model cannot reliably hold in-context, directly mitigating the
multi-tool "complexity cliff".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_NUM_RE = re.compile(r"^\s*(\d+)[.)\]:-]\s+(.*\S)\s*$")


@dataclass
class Step:
    text: str
    status: str = "pending"  # pending | done | failed


@dataclass
class Plan:
    steps: list[Step] = field(default_factory=list)

    @classmethod
    def from_text(cls, text: str) -> "Plan":
        steps: list[Step] = []
        for line in (text or "").splitlines():
            m = _NUM_RE.match(line)
            if m:
                steps.append(Step(text=m.group(2).strip()))
        # Fallback: if the model didn't number, take non-empty lines.
        if not steps:
            for line in (text or "").splitlines():
                s = line.strip("-* \t")
                if s and len(s) > 3:
                    steps.append(Step(text=s))
        return cls(steps=steps[:8])

    def render(self) -> str:
        if not self.steps:
            return "(no plan)"
        marks = {"pending": "[ ]", "done": "[x]", "failed": "[!]"}
        return "\n".join(
            f"{i+1}. {marks.get(s.status, '[ ]')} {s.text}" for i, s in enumerate(self.steps)
        )

    @property
    def current(self) -> Step | None:
        for s in self.steps:
            if s.status == "pending":
                return s
        return None

    @property
    def current_index(self) -> int:
        for i, s in enumerate(self.steps):
            if s.status == "pending":
                return i
        return -1

    def all_done(self) -> bool:
        return bool(self.steps) and all(s.status != "pending" for s in self.steps)

    def advance(self, ok: bool = True) -> None:
        """Mark the current pending step done/failed."""
        s = self.current
        if s is not None:
            s.status = "done" if ok else "failed"

    def progress(self) -> tuple[int, int]:
        done = sum(1 for s in self.steps if s.status != "pending")
        return done, len(self.steps)
