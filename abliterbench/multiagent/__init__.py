"""Multi-agent red-team orchestration on top of the single-agent operator.

Hierarchical, code-orchestrated (not a chatty swarm):
  MissionController (deterministic state machine + blackboard)
    -> specialised worker agents (each a reused operator.Operator)
    -> adversarial Verifier (deterministic evidence gate + skeptic vote)
    -> evidence-grounded Synthesizer

Each piece targets a *measured* 8B failure mode (see docs/MULTIAGENT_REDTEAM_PLAN.md):
long-chain collapse, context saturation, tool confusion, hallucinated success.
"""
from .blackboard import Blackboard
from .controller import MissionController, MissionResult
from .roles import ROLES, Role
from .schemas import Finding, MissionState, Subtask, Verdict, WorkerResult
from .verifier import Verifier

__all__ = [
    "MissionController", "MissionResult", "Blackboard",
    "ROLES", "Role", "Verifier",
    "Subtask", "WorkerResult", "Finding", "Verdict", "MissionState",
]
