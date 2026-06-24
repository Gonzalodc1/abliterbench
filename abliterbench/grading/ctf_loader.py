"""Load external CTF benchmark tasks (NYU CTF Bench / InterCode-CTF / generic)
into our flag-task format, tolerant to each dataset's JSON schema.

These benchmarks ship a per-challenge JSON with the ground-truth flag (invisible
to the model) + a description + networked host/port + artifact files. Field names
differ across datasets, so we resolve via aliases rather than hard-coding one
schema. The flag may also live in a sibling file (some datasets store it apart).

Deploy (on the Kali VM, once infra is stable + Docker is up):
  git clone https://github.com/NYU-LLM-CTF/NYU_CTF_Bench ~/ctf/nyu
  # or: git clone https://github.com/princeton-nlp/intercode ~/ctf/intercode
  # networked challenges: docker compose up per challenge dir
Then:  python ctf_flag_eval.py --mode flag --tasks-dir ~/ctf/nyu/test
"""
from __future__ import annotations

import json
from pathlib import Path

# field aliases (first present wins)
_NAME = ("name", "id", "challenge", "challenge_id", "title")
_DESC = ("description", "prompt", "query", "task", "challenge_text", "desc")
_FLAG = ("flag", "answer", "gold", "solution", "key")
_FILES = ("files", "artifacts", "attachments")
_CAT = ("category", "type", "tags")
_HOST = ("box", "host", "server", "internal_box")
_PORT = ("internal_port", "port", "remote_port")


def _first(d: dict, keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return default


def _resolve_flag(d: dict, json_path: Path) -> str | None:
    f = _first(d, _FLAG)
    if isinstance(f, str) and f.strip():
        return f.strip()
    # sibling flag file fallback (e.g. flag.txt / flag in the challenge dir)
    for cand in ("flag.txt", "flag", ".flag"):
        p = json_path.parent / cand
        if p.exists():
            try:
                return p.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                pass
    return None


def load_tasks(tasks_dir: str | Path, host_base: str | None = None,
               tools: str = "recon,web,workspace,generic,exploit",
               max_steps: int = 18, limit: int | None = None) -> list[dict]:
    """Walk tasks_dir for challenge JSON files and return flag-task dicts.

    host_base: if set, networked challenges get a target line "{host_base}:{port}".
    Skips challenges with no resolvable ground-truth flag (logged in the result).
    """
    root = Path(tasks_dir)
    tasks: list[dict] = []
    skipped = 0
    seen: set[str] = set()
    for jp in sorted(root.rglob("*.json")):
        rp = str(jp.resolve())
        if rp in seen:
            continue
        seen.add(rp)
        try:
            d = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        # A task is a challenge.json, or any *.json with flag/desc that isn't a
        # sibling of a challenge.json (avoid double-counting a challenge's extras).
        if jp.name != "challenge.json":
            if jp.parent.joinpath("challenge.json").exists():
                continue
            if not (_first(d, _FLAG) or _first(d, _DESC)):
                continue
        name = str(_first(d, _NAME, jp.parent.name))
        desc = _first(d, _DESC, "")
        flag = _resolve_flag(d, jp)
        if not flag:
            skipped += 1
            continue
        cat = _first(d, _CAT, "")
        port = _first(d, _PORT)
        host = _first(d, _HOST)
        target = ""
        if host_base and port:
            target = f"\nNetwork target: {host_base}:{port}"
        elif host and port:
            target = f"\nNetwork target: {host}:{port}"
        goal = (f"Solve this Capture-The-Flag challenge ({cat}). {desc}{target}\n"
                f"Recover the flag and report it verbatim.")
        tasks.append({"id": name, "category": str(cat), "goal": goal.strip(),
                      "flag": flag, "tools": tools, "max_steps": max_steps,
                      "files": _first(d, _FILES, []), "source": str(jp)})
        if limit and len(tasks) >= limit:
            break
    if skipped:
        print(f"[ctf_loader] skipped {skipped} challenge(s) without a resolvable flag")
    return tasks
