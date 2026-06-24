"""Typed messages passed between the controller, workers and verifier.

Communication is structured (these dataclasses), never free-form chat — that is
what keeps the orchestrator deterministic and avoids re-introducing the
long-horizon coherence problem at the coordination layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Subtask:
    """A unit of work the controller dispatches to one worker role."""
    role: str               # e.g. "recon", "web_exploit"
    goal: str               # natural-language objective for the worker
    context: str = ""       # relevant blackboard slice injected into the worker


@dataclass
class WorkerResult:
    """What a worker returns after running its subtask."""
    role: str
    goal: str
    final_text: str
    evidence: dict[str, str] = field(default_factory=dict)  # tool-signature -> result snippet
    tools_ok: list[str] = field(default_factory=list)
    steps: int = 0
    error: str | None = None

    def evidence_blob(self) -> str:
        return "\n".join(f"[{k.split('|', 1)[0]}] {v}" for k, v in self.evidence.items())


@dataclass
class Finding:
    """A candidate security finding claimed by a worker."""
    title: str
    detail: str = ""
    host: str = ""
    severity: str = "info"          # info|low|medium|high|critical
    source_tool: str = ""
    evidence_quote: str = ""        # text the worker says supports it (cross-checked by Verifier)
    role: str = ""

    def key(self) -> str:
        return f"{self.host}|{self.title}".lower().strip()


@dataclass
class Verdict:
    """Verifier decision on one finding."""
    finding: Finding
    grounded: bool                  # deterministic: evidence_quote actually present in collected evidence
    skeptic_votes_real: int = 0
    skeptic_votes_total: int = 0
    accepted: bool = False
    reason: str = ""


@dataclass
class MissionState:
    """The controller's externalised mission state (anti-cliff)."""
    target: str
    phase: str = "SCOPE"
    subtasks_run: int = 0
    worker_results: list[WorkerResult] = field(default_factory=list)
    candidate_findings: list[Finding] = field(default_factory=list)
    verdicts: list[Verdict] = field(default_factory=list)
    scope_blocks: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def verified_findings(self) -> list[Finding]:
        return [v.finding for v in self.verdicts if v.accepted]

    @property
    def rejected_findings(self) -> list[Finding]:
        return [v.finding for v in self.verdicts if not v.accepted]
