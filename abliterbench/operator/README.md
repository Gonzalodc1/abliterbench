# AbliterBench Operator

A **Claude-Code-style agentic scaffold** on top of a local 7-8B model, specialised
for authorized red-team / OSINT work against the synthetic lab. It adds an
*operative layer* that lifts a small model past the multi-tool "complexity cliff".

## Why

Raw 8B models collapse on tool chains ≥5 (the AbliterBench multi-step finding).
This scaffold compensates with explicit structure:

| Scaffold | Module | What it does |
|---|---|---|
| Plan / todo ledger | `planner.py` | Externalises long-horizon state the 8B can't hold |
| RAG-augmentation | `loop._rag_context` + `/rag_search` | Injects expert methodology (hacktricks, gtfobins, …) |
| Tool-result distillation | `context.distill_tool_output` | Shrinks big scan output to salient facts |
| Context compaction | `context.maybe_compact` | Summarises old history to fit 16k ctx |
| Tool-call repair | `loop` REPAIR/REFLECT | Recovers from malformed / empty turns |
| Scope guardrail | `scope.py` | Hard allowlist (10.0.2.56/57) before every call |
| Approval gating | `loop._needs_approval` | Human-in-the-loop for intrusive ops |

The loop is **model-agnostic** (drives any Ollama model via
`OllamaClient.chat_with_tools`) and **UI-agnostic** (events + approval callbacks),
so the same core powers the terminal REPL and an autonomous harness.

## Architecture

```
operator_cli.py  ──>  Repl (repl.py)         terminal UI, approvals, slash cmds
                        └─ Operator (loop.py)  plan→act→observe→reflect
                             ├─ OllamaClient   host Ollama (model + nomic-embed)
                             ├─ Bridge (tools.py)  Kali :8765  (55+ tools, workspace, RAG)
                             ├─ Scope (scope.py)   allowlist + risk classification
                             ├─ context.py        distill + compact
                             ├─ planner.py         todo ledger
                             └─ session.py         JSONL transcript -> runs/operator/
```

Tools the model can call: all Kali bridge tools (recon/web/osint/exploit/ad), the
RAG knowledge base (`rag_search`), and a sandboxed **code workspace**
(`write_file`, `read_file`, `run_python`, `run_bash`) backed by the new bridge
endpoints `/fs_*` and `/workspace_exec`.

## Usage

Runs on the **Windows host** (Ollama local, tools on Kali via the bridge). Use the
dedicated venv (`envs/operator`, deps: httpx, pyyaml, rich, prompt_toolkit):

```bash
# interactive REPL (default model: llama-3.1-8b-abliterated-tools)
./../envs/operator/Scripts/python.exe operator_cli.py

# one-shot autonomous run against a lab target
python operator_cli.py --approve auto --once \
  "Assess http://127.0.0.1:3000, identify the stack and one finding."

# gate every action, restrict tools, more steps
python operator_cli.py --approve all --tools recon,web,rag --max-steps 20
```

### Key flags
- `--model {llama,qwen,granite}-{abliterated,aligned}` — matched-pair models
- `--approve {auto|intrusive|active|all}` — approval policy (default `intrusive`)
- `--tools all|recon,web,osint,rag,workspace,…` — tool subset
- `--cidrs` — scope allowlist (default `127.0.0.1/24,127.0.0.1/24`)
- `--allow-identity-osint` — permit username/email/phone OSINT (synthetic personas)
- `--no-rag` — disable RAG auto-augmentation

### REPL slash commands
`/help /plan /tools [cat] /scope /workspace /rag <q> /approve <policy> /model /clear /quit`

## Verification & metrics

Two harnesses (both at `eval/`):

- **`operator_selftest.py`** — fast, deterministic, no GPU (<1s). Asserts the scaffold
  invariants (scope allow/deny, risk classification, plan parsing, loose `name(args)`
  recovery, schema-echo arg sanitisation) and drives the *full loop* with a scripted fake
  LLM + fake bridge to verify control flow (loose-parse recovery → scope block → dedupe →
  evidence-grounded final). `--live` also smokes the real Kali bridge workspace.
  ```bash
  ./../envs/operator/Scripts/python.exe operator_selftest.py --live   # 30 checks
  ```

- **`operator_eval.py`** — real-LLM scenario harness. Runs the agent across varied
  scenarios (`recon_host`, `web`, `rag_pure`, `code`, `scope_negative`) and records
  per-run **metrics** (steps, distinct successful tools = complexity-cliff proxy,
  loose-parses, repairs, reflects, dedupes, scope_blocks, compactions, tokens, tok/s,
  `reached_final`, `evidence_items`, and a `possible_hallucination` flag) plus pass/fail
  checks per scenario. Writes `runs/operator-eval/eval-<ts>.jsonl` + a summary table.
  ```bash
  python operator_eval.py --models llama-abliterated --scenarios all
  python operator_eval.py --models llama-abliterated,llama-aligned    # matched-pair compare
  ```

## Safety / scope

Every networked tool call is checked against the CIDR allowlist *before* hitting the
bridge; out-of-scope targets are refused. Intrusive actions (sqlmap, msfvenom,
netexec, code exec, identity OSINT when disallowed, …) require approval unless
`--approve auto`. All work is against synthetic lab targets only.
