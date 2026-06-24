"""Config loader for AbliterBench.

Loads `eval/config.yaml` and exposes dataclasses for type-safe access.

Usage:
    from abliterbench.config import load_config
    cfg = load_config()
    print(cfg.models.pairs[0].aligned)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml


@dataclass
class ModelPair:
    name: str
    family: str
    params_b: int
    vram_q4_gb: float
    aligned: str
    abliterated: str  # Canonical "abliterated" model for the benchmark
    # Optional: if the original abliterated as published has a broken Modelfile
    # template (no tool calling), point `abliterated` at the tools-fixed version
    # and keep the original here for "as shipped" comparison.
    abliterated_original: str | None = None
    abliterated_original_note: str | None = None


@dataclass
class Sampling:
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 50
    max_tokens: int = 4096
    seeds: list[int] = field(default_factory=lambda: [42, 1337, 9001])


@dataclass
class Models:
    pairs: list[ModelPair]
    sampling: Sampling


@dataclass
class Track:
    enabled: bool
    timeout_per_task_sec: int
    difficulty_split: dict[str, float] = field(default_factory=dict)
    n_tasks_target: int | None = None
    n_tasks_vulnhub: int | None = None
    n_tasks_custom_ood: int | None = None
    n_tasks: int | None = None
    agent_configs: list[int] | None = None


@dataclass
class Tracks:
    track1_osint: Track
    track2_exploit: Track
    track3_multiagent: Track


@dataclass
class RAGConfig:
    embedding_model: str = "nomic-embed-text:latest"
    vector_store: Literal["chroma", "qdrant"] = "chroma"
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5
    corpora: list[str] = field(default_factory=list)
    corpora_dir: str = "~/abliterbench/rag-corpora"


@dataclass
class Network:
    attacker_kali_ip: str
    target_vm_subnet: str
    target_container_subnet: str


@dataclass
class Targets:
    containers: dict[str, str]
    vms: list[dict] = field(default_factory=list)


@dataclass
class OllamaServer:
    host_from_kali: str = "http://127.0.0.1:11434"
    host_from_windows: str = "http://localhost:11434"


@dataclass
class LLMServer:
    primary: str
    ollama: OllamaServer
    vllm: dict[str, str]


@dataclass
class Logging:
    inspect_log_dir: str
    log_compress: bool
    full_trace_seed_idx: int
    truncate_tool_output_lines: int
    archive_failed_runs_after_days: int


@dataclass
class Config:
    models: Models
    tracks: Tracks
    conditions: dict[str, list[str]]
    rag: RAGConfig
    network: Network
    targets: Targets
    llm_server: LLMServer
    logging: Logging


def find_config_yaml() -> Path:
    """Locate config.yaml searching up the dir tree from this file."""
    here = Path(__file__).resolve().parent
    for candidate in [here / "config.yaml", here.parent / "config.yaml", here.parent.parent / "eval" / "config.yaml"]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No config.yaml found in expected locations")


def load_config(path: str | Path | None = None) -> Config:
    """Load and parse config.yaml into a Config dataclass."""
    p = Path(path) if path else find_config_yaml()
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    pairs = [ModelPair(**p) for p in raw["models"]["pairs"]]
    sampling = Sampling(**raw["models"]["sampling"])
    models = Models(pairs=pairs, sampling=sampling)

    tracks = Tracks(
        track1_osint=Track(**raw["tracks"]["track1_osint"]),
        track2_exploit=Track(**raw["tracks"]["track2_exploit"]),
        track3_multiagent=Track(**raw["tracks"]["track3_multiagent"]),
    )

    rag_cfg = RAGConfig(**raw["rag"])
    network = Network(**raw["network"])
    targets = Targets(**raw["targets"])
    ollama_server = OllamaServer(**raw["llm_server"]["ollama"])
    llm_server = LLMServer(
        primary=raw["llm_server"]["primary"],
        ollama=ollama_server,
        vllm=raw["llm_server"]["vllm"],
    )
    logging_cfg = Logging(**raw["logging"])

    return Config(
        models=models,
        tracks=tracks,
        conditions=raw["conditions"],
        rag=rag_cfg,
        network=network,
        targets=targets,
        llm_server=llm_server,
        logging=logging_cfg,
    )


def detect_ollama_host() -> str:
    """Auto-detect Ollama host based on environment.

    Priority order:
      1. OLLAMA_HOST env var if set (most explicit)
      2. If any local interface has IP in 127.0.0.1/24 -> Kali VM, use host_from_kali
      3. Windows/macOS host or other Linux -> host_from_windows (localhost)
    """
    import os
    import platform
    import socket

    # 1. Explicit override via env var
    env_host = os.environ.get("OLLAMA_HOST", "").strip()
    if env_host:
        # Normalise: add http:// if missing
        if not env_host.startswith("http"):
            env_host = f"http://{env_host}"
        return env_host

    cfg = load_config()

    # 2. Iterate over all local interfaces to find host-only subnet membership
    try:
        for iface_info in socket.getaddrinfo("", None):
            ip = iface_info[4][0]
            if ip.startswith("10.0.2.56."):
                return cfg.llm_server.ollama.host_from_kali
    except Exception:
        pass

    # Fallback: iterate via psutil-style if available, else use ifconfig parsing
    try:
        import subprocess

        out = subprocess.run(["ip", "-o", "-4", "addr"], capture_output=True, text=True, timeout=2)
        if "10.0.2.56." in (out.stdout or ""):
            return cfg.llm_server.ollama.host_from_kali
    except Exception:
        pass

    # 3. Default to localhost (host Windows or other Linux assumed to have local Ollama)
    if platform.system() in {"Windows", "Darwin"}:
        return cfg.llm_server.ollama.host_from_windows
    return cfg.llm_server.ollama.host_from_windows
