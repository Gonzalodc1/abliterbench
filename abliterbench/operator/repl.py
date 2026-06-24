"""Terminal REPL (Claude-Code-style) for the operator.

Streams the agent's plan, steps, tool calls and results live, and prompts the
human for approval before intrusive actions. Slash commands give manual control.
"""
from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    _HAS_PTK = True
except Exception:  # pragma: no cover
    _HAS_PTK = False

from .loop import Operator, OperatorConfig
from .scope import Scope
from .tools import CATALOG

HELP = """[bold]Slash commands[/bold]
  /help              this help
  /plan              show the current plan
  /tools [cat]       list available tools (optionally by category)
  /scope             show the scope allowlist
  /workspace         list files in the code workspace
  /rag <query>       quick RAG lookup (hacktricks)
  /approve <policy>  set approval policy: auto | intrusive | active | all
  /model             show the active model
  /clear             reset the conversation + plan
  /quit              exit
Anything else is a task for the agent."""


class Repl:
    def __init__(self, cfg: OperatorConfig, scope: Scope) -> None:
        self.console = Console()
        self.cfg = cfg
        self.scope = scope
        self.op = Operator(cfg, scope=scope, on_event=self._render, approval_cb=self._approve)
        # PromptSession is created lazily on first interactive read: instantiating
        # it requires a real console (fails under non-Windows-console shells), and
        # one-shot (--once) mode never needs it.
        self._session = None
        self._ptk = _HAS_PTK

    # ---- event rendering --------------------------------------------------
    def _render(self, ev: dict) -> None:
        c = self.console
        t = ev.get("type")
        if t == "preflight":
            ok = "[ok]" if ev["llm"] and ev["bridge"] else "[!!]"
            c.print(f"[dim]{ok} llm={ev['llm']} bridge={ev['bridge']} "
                    f"({ev['endpoints']} eps) native_tools={ev['native_tools']}[/dim]")
        elif t == "rag":
            c.print(f"[dim]* RAG: {ev['chars']} chars from {', '.join(ev['corpora'])}[/dim]")
        elif t == "plan":
            c.print(Panel(ev["render"], title="plan", border_style="blue", expand=False))
        elif t == "step_start":
            d, n = ev["progress"]
            c.print(Rule(f"step {ev['step']}  ·  plan {d}/{n}", style="magenta"))
        elif t == "assistant":
            if ev["text"]:
                c.print(Text(ev["text"], style="grey70"))
            c.print(f"[dim]  mode={ev['mode']} {ev['tok_s']} tok/s[/dim]")
        elif t == "tool_call":
            c.print(f"[cyan]>> {ev['tool']}[/cyan]([dim]{json.dumps(ev['args'])[:200]}[/dim]) "
                    f"[dim]risk={ev['risk']}[/dim]")
        elif t == "tool_result":
            style = "green" if ev["ok"] else "red"
            tag = " (distilled)" if ev.get("distilled") else ""
            c.print(f"[{style}]<< ok={ev['ok']} exit={ev['exit']}{tag}[/{style}]")
            if ev.get("preview"):
                c.print(Text("  " + ev["preview"], style="grey50"))
        elif t == "scope_block":
            c.print(f"[bold red][BLOCK] scope: {ev['reason']}[/bold red]")
        elif t == "denied":
            c.print(f"[yellow][denied] {ev['tool']}[/yellow]")
        elif t in ("repair", "reflect"):
            c.print(f"[dim italic]~ {t}: {ev.get('reason','')}[/dim italic]")
        elif t == "compact":
            c.print("[dim italic]~ context compacted[/dim italic]")
        elif t == "forced_final":
            c.print("[dim italic]~ max steps - forcing final answer[/dim italic]")
        elif t == "final":
            c.print(Panel(ev["text"], title="FINAL ANSWER", border_style="green"))
        elif t == "error":
            c.print(f"[bold red]error: {ev['error']}[/bold red]")

    # ---- approval ---------------------------------------------------------
    def _approve(self, action: dict) -> bool:
        self.console.print(
            f"[bold yellow]approve {action['risk']} action[/bold yellow] "
            f"[cyan]{action['tool']}[/cyan]({json.dumps(action['args'])[:240]}) ?")
        ans = self._ask("  [y/N/auto] > ").strip().lower()
        if ans in ("auto", "a"):
            self.cfg.approval_policy = "auto"
            return True
        return ans in ("y", "yes")

    def _ask(self, prompt: str) -> str:
        if self._ptk and self._session is None:
            try:
                self._session = PromptSession(history=InMemoryHistory())
            except Exception:
                self._ptk = False  # no real console; fall back to input()
        if self._session is not None:
            try:
                return self._session.prompt(prompt)
            except (EOFError, KeyboardInterrupt):
                return ""
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return ""

    # ---- slash commands ---------------------------------------------------
    def _slash(self, line: str) -> bool:
        """Return True if handled as a command (loop should continue)."""
        parts = line.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        c = self.console
        if cmd in ("/quit", "/exit", "/q"):
            return False
        if cmd == "/help":
            c.print(HELP)
        elif cmd == "/plan":
            c.print(Panel(self.op.plan.render(), title="plan", border_style="blue", expand=False))
        elif cmd == "/tools":
            items = [t for t in CATALOG if (not arg or t.category == arg)]
            for t in items:
                c.print(f"  [cyan]{t.name:<20}[/cyan] [dim]{t.category:<10}[/dim] {t.description[:70]}")
        elif cmd == "/scope":
            c.print(f"  cidrs: {self.scope.cidrs}\n  hosts: {sorted(self.scope.hosts)}\n"
                    f"  identity_osint: {self.scope.allow_identity_osint}")
        elif cmd == "/workspace":
            res = self.op.bridge.call("list_files", {"path": "."})
            c.print(Text(res.get("stdout", "") or res.get("stderr", ""), style="grey70"))
        elif cmd == "/rag":
            if not arg:
                c.print("[dim]usage: /rag <query>[/dim]")
            else:
                res = self.op.bridge.call("rag_search", {"query": arg, "corpus": "hacktricks", "top_k": 3})
                for ch in res.get("chunks", []):
                    c.print(f"  [dim]{ch.get('source')}[/dim] {str(ch.get('text',''))[:200]}")
        elif cmd == "/approve":
            if arg in ("auto", "intrusive", "active", "all"):
                self.cfg.approval_policy = arg
                c.print(f"[green]approval policy = {arg}[/green]")
            else:
                c.print(f"[dim]current: {self.cfg.approval_policy}  (auto|intrusive|active|all)[/dim]")
        elif cmd == "/model":
            c.print(f"  {self.cfg.model_alias}  →  {self.cfg.model_tag}  @ {self.cfg.host}")
        elif cmd == "/clear":
            self.op.messages = self.op.messages[:1] + [self.op.messages[1].__class__("system", "[plan]\n(no plan yet)")]
            from .planner import Plan
            self.op.plan = Plan()
            c.print("[dim]conversation reset[/dim]")
        else:
            c.print(f"[dim]unknown command {cmd} — /help[/dim]")
        return True

    # ---- main loop --------------------------------------------------------
    def run(self) -> int:
        c = self.console
        c.print(Panel.fit(
            f"[bold]AbliterBench Operator[/bold]  ·  model [cyan]{self.cfg.model_alias}[/cyan]  ·  "
            f"approve=[yellow]{self.cfg.approval_policy}[/yellow]  ·  rag={'on' if self.cfg.rag_auto else 'off'}\n"
            f"[dim]{len(self.op.tools)} tools · bridge {self.cfg.bridge_url} · /help for commands[/dim]",
            border_style="green"))
        self.op.preflight()
        try:
            while True:
                line = self._ask("\n[operator] > ")
                if not line.strip():
                    continue
                if line.strip().startswith("/"):
                    if not self._slash(line):
                        break
                    continue
                self.op.run_task(line.strip())
        except (EOFError, KeyboardInterrupt):
            c.print("\n[dim]bye[/dim]")
        finally:
            self.op.close()
        return 0

    def run_once(self, goal: str) -> int:
        self.op.preflight()
        self.op.run_task(goal)
        self.op.close()
        return 0
