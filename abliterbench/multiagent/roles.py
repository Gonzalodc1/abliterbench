"""Specialised worker roles. Each role is a thin spec the controller turns into
an `operator.Operator` with a focused persona + a restricted tool subset. Small
tool sets + a role-specific persona reduce the tool-confusion errors a single
generalist 8B makes when juggling all 31 tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_BASE = ("You are a specialist agent on an AUTHORIZED red-team engagement against SYNTHETIC "
         "lab targets only (127.0.0.1/24 and 127.0.0.1/24). Work the single objective you "
         "are given, one tool call per turn, with concrete arguments. Prefer evidence over memory; "
         "never invent tool output. When done, reply 'FINAL ANSWER:' summarising ONLY what the "
         "tools actually returned, and explicitly QUOTE the evidence line for any claim you make.")


@dataclass
class Role:
    name: str
    description: str
    tools_filter: str
    persona: str
    max_steps: int = 8
    approval_policy: str = "auto"           # workers auto-run; the controller gates intrusive roles
    rag_corpora: list[str] = field(default_factory=lambda: ["hacktricks"])
    min_tools: int = 1                      # refuse to finalise before N distinct tools succeed


ROLES: dict[str, Role] = {
    "recon": Role(
        name="recon", description="footprint discovery",
        tools_filter="recon,rag",
        persona=_BASE + " Your job: discover the attack surface — live hosts, open ports, "
                "services, HTTP stack and crawlable URLs. Use httpx_probe/nmap/subfinder/naabu/"
                "dnsx/katana. Do not exploit; just enumerate and report what exists.",
        max_steps=8, min_tools=2),
    "web_exploit": Role(
        name="web_exploit", description="web vulnerability identification",
        tools_filter="web,rag,workspace",
        persona=_BASE + " Your job: identify web vulnerabilities on the given URL(s) using "
                "nuclei/ffuf/gobuster_dir/nikto/sqlmap/searchsploit. Report each candidate finding "
                "with the exact tool output line that evidences it. Run httpx_probe AND nuclei_scan "
                "(at minimum) before concluding.",
        max_steps=10, min_tools=2),
    "osint": Role(
        name="osint", description="identity OSINT + correlation",
        tools_filter="osint,recon,rag",
        persona=_BASE + " Your job: build a footprint for the given identity (handle/email) with "
                "maigret/sherlock/holehe/theharvester, then correlate. Only report accounts the "
                "tools actually confirmed; flag low-confidence hits as unconfirmed.",
        max_steps=10),
    "ad_net": Role(
        name="ad_net", description="AD / network exploitation",
        tools_filter="ad,rag",
        persona=_BASE + " Your job: enumerate/abuse AD & network services with netexec/impacket/"
                "kerbrute/certipy against the given host. Report only confirmed access/findings.",
        max_steps=10),
    "code_exploit": Role(
        name="code_exploit", description="exploit research + PoC in the workspace",
        tools_filter="exploit,workspace,rag",
        persona=_BASE + " Your job: research a known issue (searchsploit/searchsploit_show) and, if "
                "asked, build/run a minimal PoC in the code workspace (run_python/run_bash). Report "
                "only what executed and its real output.",
        max_steps=10),
}

# Which roles are 'intrusive' enough that the controller should gate them behind
# the human approval callback even though the worker itself runs auto.
INTRUSIVE_ROLES = {"ad_net", "code_exploit"}
