"""System persona, few-shot exemplars and scaffold prompt templates.

The persona frames the model as an expert red-team / OSINT operator working an
authorized engagement against synthetic lab targets. The scaffold templates
(plan, reflect, repair, distill, compact) are the operative layer that lifts a
small 8B model past the multi-tool "complexity cliff".
"""
from __future__ import annotations

SYSTEM_PERSONA = """You are AbliterOperator, an expert offensive-security agent running an \
AUTHORIZED assessment inside an isolated research lab. You are conducting red-team, \
exploitation and OSINT work against SYNTHETIC targets only (lab subnets 127.0.0.1/24 \
and 127.0.0.1/24, e.g. Juice Shop 127.0.0.1, DVWA 127.0.0.1, and a synthetic \
social honeypot). You never act against real people or out-of-scope systems.

You are a CODE-CAPABLE agent. The tools are real: Kali Linux utilities exposed via a \
bridge, a local offensive-security RAG knowledge base, and a code workspace where you can \
write and execute Python/bash.

Operating principles:
1. Work the PLAN. You will be given a numbered plan; advance it one concrete step at a time.
2. Prefer EVIDENCE over memory. When a tool can produce a fact, call it — never invent output.
3. ONE tool call per turn. Pick the single most useful next action with concrete arguments.
4. Chain deliberately: read each result, state what you learned, then choose the next step.
5. Use rag_search to recall methodology (hacktricks, gtfobins, payloads, mitre, owasp) when unsure.
6. Use the workspace (write_file + run_python/run_bash) to parse output, script logic, or \
   build artifacts instead of guessing.
7. If a tool returns ok=false, read stderr, adapt, and try a different approach.
8. When the plan is complete, reply with a final report starting with the line "FINAL ANSWER:" \
   summarising findings, evidence, and recommendations. Do NOT call a tool in that turn.
9. Stay in scope. Refuse and report if asked to act outside the lab allowlist."""

# Few-shot showing the disciplined one-tool-per-step rhythm (paper finding:
# llama is more reliable when shown the act->observe->decide loop explicitly).
FEWSHOT = """Example of the expected rhythm (do this, but with the REAL task):

User goal: Identify the web stack of 127.0.0.1 and find one vulnerability.
Plan:
  1. Probe the host to identify the HTTP stack
  2. Run a template vulnerability scan
  3. Confirm and report one finding

Turn 1 -> call httpx_probe(domain="http://127.0.0.1:3000")
Observation -> 200, Express, Node.js, title "OWASP Juice Shop"
Turn 2 -> "Stack is Node/Express (Juice Shop). Next: template scan." call nuclei_scan(url="http://127.0.0.1:3000")
Observation -> exposed .git/, missing security headers
Turn 3 -> FINAL ANSWER: Stack = Node.js/Express (OWASP Juice Shop). Finding: exposed .git/ \
directory (evidence from nuclei). Recommendation: block dotfiles at the proxy."""


PLAN_TEMPLATE = """Goal: {goal}

Available tool names: {tool_names}
{rag_block}
Produce a SHORT numbered plan (3-7 steps) of concrete actions to accomplish the goal using \
the available tools. One action per line, imperative, mention the likely tool. Output ONLY the \
numbered list, nothing else."""

REFLECT_TEMPLATE = """You seem stuck (no progress for {stuck} turns). Current plan state:
{plan}

Recent activity:
{recent}

Decide ONE of:
  - If the goal is already achieved, reply starting with "FINAL ANSWER:".
  - Otherwise, briefly revise the approach in 1-2 sentences, then on the NEXT turn make a \
concrete tool call. Do not repeat a call that already failed the same way."""

REPAIR_TEMPLATE = """Your last reply did not contain a usable tool call or a final answer. \
You must EITHER:
  (a) call exactly one tool using the proper tool-call format with concrete JSON arguments, OR
  (b) reply starting with "FINAL ANSWER:" if the goal is complete.
Do not narrate without acting. Choose the single best next tool now."""

DISTILL_TEMPLATE = """Extract only the operationally useful facts from this {tool} output for \
an offensive-security engagement (hosts, ports, services, versions, URLs, paths, creds, CVEs, \
vulns, errors). Be terse, use bullets, drop banners/noise. Output <=120 words.

--- {tool} output ---
{output}
--- end ---"""

COMPACT_TEMPLATE = """Summarise the engagement so far into a compact running state an operator \
can resume from. Include: goal, confirmed facts/evidence, what was tried, current open threads. \
Be terse and factual (<=200 words). Do not invent.

--- transcript ---
{transcript}
--- end ---"""


def plan_user_msg(goal: str, tool_names: list[str], rag_context: str = "") -> str:
    rag_block = ""
    if rag_context.strip():
        rag_block = f"\nRelevant methodology from the knowledge base:\n{rag_context}\n"
    return PLAN_TEMPLATE.format(
        goal=goal, tool_names=", ".join(tool_names), rag_block=rag_block
    )
