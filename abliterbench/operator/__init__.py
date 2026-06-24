"""AbliterBench Operator — a Claude-Code-style agentic scaffold on top of a
local 7-8B model, specialised for authorized red-team / OSINT work.

The scaffold adds an *operative layer* over the raw LLM:
  - explicit plan/todo ledger (attacks the chain>=5 "complexity cliff")
  - RAG-augmented reasoning from the local Kali knowledge base
  - tool-result distillation + context compaction for the 16k ctx window
  - malformed tool-call repair
  - scope guardrail (target allowlist) + approval gating for intrusive ops
  - persistent JSONL session transcript

Model-agnostic: drives any Ollama model through
`abliterbench.llm_client.OllamaClient.chat_with_tools`, so the same operator can
run the matched-pair models for the paper.
"""

from .loop import Operator, OperatorConfig
from .scope import Scope
from .tools import CATALOG, Bridge, Tool, filter_catalog, schemas_for

__all__ = [
    "Operator",
    "OperatorConfig",
    "Scope",
    "Bridge",
    "Tool",
    "CATALOG",
    "filter_catalog",
    "schemas_for",
]
