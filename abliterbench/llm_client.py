"""Ollama HTTP client wrapper for AbliterBench.

Wraps the Ollama API to provide:
- Deterministic sampling (seed control)
- Connection pooling
- Retry on transient errors
- Token counting and timing
- Compatibility with both host Windows and Kali VM endpoints
- Uniform tool calling across models with and without native tools support
  (auto-detects capability and falls back to prompted JSON mode)

Usage:
    from abliterbench.llm_client import OllamaClient

    client = OllamaClient()  # auto-detects host
    resp = client.generate("llama3.1:8b-instruct-q4_K_M", "hello", seed=42)
    print(resp.text)

    # Uniform tool calling (works on any model):
    resp = client.chat_with_tools(
        model="mannix/llama3.1-8b-abliterated:latest",
        messages=[ChatMessage("user", "search for X")],
        tools=[{"type": "function", "function": {...}}],
    )
    print(resp.tool_calling_mode)   # "native" | "prompted"
    for c in resp.parsed_tool_calls:
        print(c.name, c.arguments)
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from .config import Sampling, detect_ollama_host, load_config


@dataclass
class GenerateResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_duration_s: float
    load_duration_s: float
    eval_count: int
    eval_duration_s: float
    raw: dict[str, Any]

    @property
    def tokens_per_second(self) -> float:
        if self.eval_duration_s > 0:
            return self.eval_count / self.eval_duration_s
        return 0.0


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str


@dataclass
class ToolCall:
    """Normalised representation of a tool call regardless of source format."""

    name: str
    arguments: dict[str, Any]
    raw: str = ""  # The raw text/JSON the model emitted, for debugging

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": self.arguments}


ToolCallingMode = Literal["native", "prompted", "unknown"]


@dataclass
class ChatWithToolsResponse:
    """Result of chat_with_tools — uniform regardless of underlying mode."""

    text: str
    tool_calling_mode: ToolCallingMode
    parsed_tool_calls: list[ToolCall]
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_duration_s: float
    eval_duration_s: float
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def tokens_per_second(self) -> float:
        if self.eval_duration_s > 0:
            return self.completion_tokens / self.eval_duration_s
        return 0.0


class OllamaClient:
    """HTTP client for Ollama API."""

    def __init__(self, host: str | None = None, timeout_s: float = 300.0):
        self.host = host or detect_ollama_host()
        self.timeout_s = timeout_s
        self.client = httpx.Client(base_url=self.host, timeout=timeout_s)
        self._cfg = load_config()
        # Cache of (model, supports_tools_native) — avoids repeated /api/show
        self._capability_cache: dict[str, bool] = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def list_models(self) -> list[dict]:
        """GET /api/tags - lista de modelos descargados."""
        r = self.client.get("/api/tags")
        r.raise_for_status()
        return r.json().get("models", [])

    def model_exists(self, model: str) -> bool:
        for m in self.list_models():
            if m.get("name") == model or m.get("model") == model:
                return True
        return False

    def generate(
        self,
        model: str,
        prompt: str,
        seed: int | None = None,
        system: str | None = None,
        sampling: Sampling | None = None,
        max_retries: int = 3,
    ) -> GenerateResponse:
        """Non-streaming generation via /api/generate."""
        s = sampling or self._cfg.models.sampling
        opts: dict[str, Any] = {
            "temperature": s.temperature,
            "top_p": s.top_p,
            "top_k": s.top_k,
            "num_predict": s.max_tokens,
        }
        if seed is not None:
            opts["seed"] = seed

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "options": opts,
            "stream": False,
        }
        if system:
            payload["system"] = system

        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                r = self.client.post("/api/generate", json=payload)
                r.raise_for_status()
                data = r.json()
                return GenerateResponse(
                    text=data.get("response", ""),
                    model=data.get("model", model),
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    total_duration_s=data.get("total_duration", 0) / 1e9,
                    load_duration_s=data.get("load_duration", 0) / 1e9,
                    eval_count=data.get("eval_count", 0),
                    eval_duration_s=data.get("eval_duration", 0) / 1e9,
                    raw=data,
                )
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_err = e
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
        raise RuntimeError(f"generate failed after {max_retries} retries: {last_err}")

    def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        seed: int | None = None,
        sampling: Sampling | None = None,
        tools: list[dict] | None = None,
    ) -> GenerateResponse:
        """Multi-turn chat via /api/chat (supports tool calls)."""
        s = sampling or self._cfg.models.sampling
        opts: dict[str, Any] = {
            "temperature": s.temperature,
            "top_p": s.top_p,
            "top_k": s.top_k,
            "num_predict": s.max_tokens,
        }
        if seed is not None:
            opts["seed"] = seed

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": opts,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        r = self.client.post("/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {})
        return GenerateResponse(
            text=msg.get("content", ""),
            model=data.get("model", model),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_duration_s=data.get("total_duration", 0) / 1e9,
            load_duration_s=data.get("load_duration", 0) / 1e9,
            eval_count=data.get("eval_count", 0),
            eval_duration_s=data.get("eval_duration", 0) / 1e9,
            raw=data,
        )

    def embed(self, model: str, prompt: str) -> list[float]:
        """Vector embedding via /api/embed (Ollama >=0.24).

        Falls back to legacy /api/embeddings if the new endpoint returns 404.
        """
        # Modern endpoint
        r = self.client.post("/api/embed", json={"model": model, "input": prompt})
        if r.status_code == 404:
            # Legacy fallback for older Ollama
            r2 = self.client.post("/api/embeddings", json={"model": model, "prompt": prompt})
            r2.raise_for_status()
            return r2.json().get("embedding", [])
        r.raise_for_status()
        data = r.json()
        # /api/embed returns {"embeddings": [[...]]} (batch-style even for single input)
        embs = data.get("embeddings") or []
        if embs and isinstance(embs[0], list):
            return embs[0]
        # fall through if older shape
        return data.get("embedding", [])

    def preload(self, model: str) -> None:
        """Force model load into VRAM (empty prompt with max_tokens=0)."""
        self.client.post(
            "/api/generate",
            json={"model": model, "prompt": "", "options": {"num_predict": 0}, "stream": False},
        )

    def health(self) -> bool:
        try:
            r = self.client.get("/", timeout=5.0)
            return r.status_code == 200
        except Exception:
            return False

    # ========================================================================
    # Uniform tool calling — works across models with/without native support
    # ========================================================================

    def supports_native_tools(self, model: str) -> bool:
        """Probe /api/show for `capabilities` list. Caches result.

        Some abliterated models advertise only `completion` because their
        Modelfile templates dropped the .Tools section. Those need fallback.
        """
        if model in self._capability_cache:
            return self._capability_cache[model]
        try:
            r = self.client.post("/api/show", json={"model": model}, timeout=10.0)
            r.raise_for_status()
            caps = r.json().get("capabilities", []) or []
            supports = "tools" in caps
        except Exception:
            supports = False
        self._capability_cache[model] = supports
        return supports

    @staticmethod
    def _format_tools_for_system_prompt(tools: list[dict]) -> str:
        """Render JSON-schema tools as instructions for prompted-mode."""
        lines = ["You have access to the following tools:\n"]
        for t in tools:
            fn = t.get("function", t)
            name = fn.get("name", "?")
            desc = fn.get("description", "")
            params = fn.get("parameters", {}) or {}
            props = params.get("properties", {}) or {}
            required = params.get("required", []) or []
            arg_lines = []
            for arg_name, arg_spec in props.items():
                t_str = arg_spec.get("type", "any")
                d = arg_spec.get("description", "")
                req_marker = " (required)" if arg_name in required else ""
                arg_lines.append(f"    - {arg_name}: {t_str}{req_marker}  {d}".rstrip())
            args_block = "\n".join(arg_lines) if arg_lines else "    (no arguments)"
            lines.append(f"- **{name}**: {desc}\n  Arguments:\n{args_block}")
        lines.append(
            "\nTo call a tool, emit exactly one JSON object on a line by itself, in this format:\n"
            '{"tool":"<tool_name>","args":{...}}\n'
            "After your tool call, STOP and wait for the result. "
            "Do not chain multiple tool calls in one turn. "
            "When you have enough information, write your final answer as plain text "
            'starting with "## Answer".'
        )
        return "\n".join(lines)

    @staticmethod
    def _parse_tool_calls_multi(text: str) -> list[ToolCall]:
        """Extract tool calls from free-form text in 4 known formats.

        Supports:
          1. JSON inline:        {"name":"X","parameters":{...}}
          2. Custom inline:      {"tool":"X","args":{...}}
          3. Qwen XML:           <tool_call>{"name":"X","arguments":{...}}</tool_call>
          4. Markdown code:      ```json\\n{"name":"X",...}\\n```
        """
        text = text or ""
        calls: list[ToolCall] = []

        # 3. Qwen XML <tool_call>...</tool_call>
        for m in re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.DOTALL):
            try:
                obj = json.loads(m.group(1))
                name = obj.get("name") or obj.get("tool") or obj.get("function", {}).get("name", "")
                args = obj.get("arguments") or obj.get("args") or obj.get("parameters") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                if name:
                    calls.append(ToolCall(name=name, arguments=args, raw=m.group(0)))
            except json.JSONDecodeError:
                pass
        if calls:
            return calls

        # 4. Markdown code blocks ```json ... ```
        for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL):
            try:
                obj = json.loads(m.group(1))
                name = obj.get("name") or obj.get("tool") or obj.get("function", {}).get("name", "")
                args = obj.get("arguments") or obj.get("args") or obj.get("parameters") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                if name:
                    calls.append(ToolCall(name=name, arguments=args, raw=m.group(0)))
            except json.JSONDecodeError:
                pass
        if calls:
            return calls

        # 1 + 2. Raw JSON objects in text (greedy balanced)
        # Find candidate {..} blocks and try to parse
        candidates: list[str] = []
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}" and depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    candidates.append(text[start : i + 1])
                    start = -1
        for cand in candidates:
            try:
                obj = json.loads(cand)
                name = obj.get("name") or obj.get("tool") or obj.get("function", {}).get("name", "")
                args = obj.get("arguments") or obj.get("args") or obj.get("parameters") or obj.get("function", {}).get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                if name and isinstance(args, dict):
                    calls.append(ToolCall(name=name, arguments=args, raw=cand))
            except json.JSONDecodeError:
                continue
        return calls

    def chat_with_tools(
        self,
        model: str,
        messages: list[ChatMessage],
        tools: list[dict],
        seed: int | None = None,
        sampling: Sampling | None = None,
        force_mode: ToolCallingMode | None = None,
    ) -> ChatWithToolsResponse:
        """Uniform tool calling: picks native API if supported, else prompted JSON.

        Args:
            model:      Ollama tag
            messages:   Conversation so far (system, user, assistant, tool)
            tools:      OpenAI-style function schemas (as in /api/chat tools field)
            seed:       Deterministic sampling
            sampling:   Override defaults
            force_mode: Skip detection (for benchmarking each mode separately)

        Returns:
            ChatWithToolsResponse with `parsed_tool_calls` populated regardless
            of underlying transport, plus `tool_calling_mode` for metrics.
        """
        s = sampling or self._cfg.models.sampling
        opts: dict[str, Any] = {
            "temperature": s.temperature,
            "top_p": s.top_p,
            "top_k": s.top_k,
            "num_predict": s.max_tokens,
        }
        if seed is not None:
            opts["seed"] = seed

        # Decide mode
        if force_mode and force_mode != "unknown":
            mode = force_mode
        else:
            mode = "native" if self.supports_native_tools(model) else "prompted"

        if mode == "native":
            payload: dict[str, Any] = {
                "model": model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "tools": tools,
                "options": opts,
                "stream": False,
            }
            try:
                r = self.client.post("/api/chat", json=payload)
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400 and force_mode is None:
                    # Capability cache was wrong; fall back to prompted
                    self._capability_cache[model] = False
                    return self.chat_with_tools(model, messages, tools, seed, sampling, force_mode="prompted")
                raise
            data = r.json()
            msg = data.get("message", {}) or {}
            text = msg.get("content", "") or ""
            native_calls = msg.get("tool_calls", []) or []

            parsed: list[ToolCall] = []
            for tc in native_calls:
                fn = tc.get("function", {}) or {}
                name = fn.get("name", "")
                args = fn.get("arguments", {}) or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                if name:
                    parsed.append(ToolCall(name=name, arguments=args, raw=json.dumps(tc)))

            # Even in native mode, parse content as fallback (some models emit inline anyway)
            if not parsed and text:
                parsed = self._parse_tool_calls_multi(text)

            return ChatWithToolsResponse(
                text=text,
                tool_calling_mode="native",
                parsed_tool_calls=parsed,
                model=data.get("model", model),
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_duration_s=data.get("total_duration", 0) / 1e9,
                eval_duration_s=data.get("eval_duration", 0) / 1e9,
                raw=data,
            )

        # mode == "prompted"
        # Inject tool schema into system message
        tool_instructions = self._format_tools_for_system_prompt(tools)
        adjusted: list[dict] = []
        injected = False
        for m in messages:
            if m.role == "system" and not injected:
                adjusted.append(
                    {"role": "system", "content": f"{m.content}\n\n{tool_instructions}"}
                )
                injected = True
            else:
                adjusted.append({"role": m.role, "content": m.content})
        if not injected:
            adjusted.insert(0, {"role": "system", "content": tool_instructions})

        payload = {
            "model": model,
            "messages": adjusted,
            "options": opts,
            "stream": False,
        }
        r = self.client.post("/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {}) or {}
        text = msg.get("content", "") or ""
        parsed = self._parse_tool_calls_multi(text)

        return ChatWithToolsResponse(
            text=text,
            tool_calling_mode="prompted",
            parsed_tool_calls=parsed,
            model=data.get("model", model),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_duration_s=data.get("total_duration", 0) / 1e9,
            eval_duration_s=data.get("eval_duration", 0) / 1e9,
            raw=data,
        )
