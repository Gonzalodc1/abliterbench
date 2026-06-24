"""Persistent session transcript (JSONL) + run metadata.

Mirrors the existing eval/runs logging convention so operator sessions are
queryable alongside benchmark runs.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "runs" / "operator"


class Session:
    def __init__(self, model_alias: str, out_dir: Path | str | None = None,
                 started_iso: str | None = None) -> None:
        self.dir = Path(out_dir) if out_dir else DEFAULT_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        stamp = started_iso or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.model_alias = model_alias
        self.path = self.dir / f"session-{stamp}-{model_alias.replace('/', '_')}.jsonl"
        self._fh = self.path.open("a", encoding="utf-8")
        self.write({"type": "session_start", "model": model_alias, "ts": self._now()})

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def write(self, record: dict[str, Any]) -> None:
        record.setdefault("ts", self._now())
        try:
            self._fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            self._fh.flush()
        except Exception:
            pass

    def event(self, ev: dict[str, Any]) -> None:
        self.write({"type": "event", **ev})

    def close(self) -> None:
        self.write({"type": "session_end", "ts": self._now()})
        try:
            self._fh.close()
        except Exception:
            pass
