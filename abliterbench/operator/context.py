"""Context management for a small (16k) context window.

Two scaffolds live here:
  - distill: shrink large tool outputs to operationally useful facts
  - compact: summarise old history when the running token budget is exceeded

Both can use the LLM (via a summariser callable) or fall back to cheap
head/tail truncation when the LLM is unavailable or output is small.
"""
from __future__ import annotations

from collections.abc import Callable

from ..llm_client import ChatMessage
from . import prompts


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token); good enough for budgeting."""
    return max(1, len(text) // 4)


def messages_tokens(messages: list[ChatMessage]) -> int:
    return sum(estimate_tokens(m.content) for m in messages)


def truncate_headtail(s: str, max_chars: int = 2400) -> str:
    if not s or len(s) <= max_chars:
        return s or ""
    half = max_chars // 2
    return s[:half] + f"\n…[truncated {len(s) - max_chars} chars]…\n" + s[-half:]


def distill_tool_output(
    text: str,
    tool: str,
    summarizer: Callable[[str], str] | None = None,
    distill_over_chars: int = 1800,
    max_chars: int = 2400,
) -> tuple[str, bool]:
    """Return (text_for_context, was_distilled).

    Large outputs are summarised by the LLM into salient facts; otherwise we
    keep the raw (optionally head/tail-truncated) output.
    """
    text = text or ""
    if len(text) <= distill_over_chars or summarizer is None:
        return truncate_headtail(text, max_chars), False
    try:
        prompt = prompts.DISTILL_TEMPLATE.format(tool=tool, output=truncate_headtail(text, 6000))
        summary = summarizer(prompt).strip()
        if summary:
            return f"[distilled {tool} output]\n{summary}", True
    except Exception:
        pass
    return truncate_headtail(text, max_chars), False


def maybe_compact(
    messages: list[ChatMessage],
    summarizer: Callable[[str], str] | None,
    budget_tokens: int = 9000,
    keep_recent: int = 6,
) -> tuple[list[ChatMessage], bool]:
    """Compact history if over budget.

    Keeps the system message(s) and the most recent `keep_recent` messages,
    replacing the middle with a single summary message. Returns
    (new_messages, did_compact).
    """
    if messages_tokens(messages) <= budget_tokens or summarizer is None:
        return messages, False

    system = [m for m in messages if m.role == "system"]
    body = [m for m in messages if m.role != "system"]
    if len(body) <= keep_recent:
        return messages, False

    head = body[:-keep_recent]
    tail = body[-keep_recent:]
    transcript = "\n".join(f"{m.role}: {truncate_headtail(m.content, 800)}" for m in head)
    try:
        summary = summarizer(prompts.COMPACT_TEMPLATE.format(transcript=transcript)).strip()
    except Exception:
        return messages, False
    if not summary:
        return messages, False

    compacted = list(system)
    compacted.append(ChatMessage("system", f"[engagement state so far]\n{summary}"))
    compacted.extend(tail)
    return compacted, True
