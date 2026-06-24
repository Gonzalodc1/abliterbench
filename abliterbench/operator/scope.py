"""Scope guardrail + risk classification.

Enforces that every tool call with a network target stays inside the authorized
lab (host-only 127.0.0.1/24 and container 127.0.0.1/24 by default), and
classifies each tool by intrusiveness so the loop can gate approvals.

This is a *design invariant*: the operator only operates against synthetic lab
targets. Anything outside the allowlist is refused before reaching the bridge.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

# Per-tool intrusiveness. Anything not listed defaults to "active".
#   passive   : read-only / no packets to a target            -> never gated
#   active    : touches a target but non-destructive recon     -> gated unless policy allows
#   intrusive : exploitation / code-exec / credential / TX     -> always gated
RISK: dict[str, str] = {
    # passive
    "rag_search": "passive", "searchsploit": "passive", "searchsploit_show": "passive",
    "osint_people_search": "passive", "osint_breach_lookup": "active",
    "web_fetch": "passive", "read_file": "passive", "list_files": "passive",
    "subfinder": "passive", "dnsx_lookup": "passive", "theharvester": "passive",
    "write_file": "passive",
    # active recon / scanning
    "nmap_scan": "active", "naabu": "active", "httpx_probe": "active",
    "katana_crawl": "active", "nuclei_scan": "active", "nikto": "active",
    "gobuster_dir": "active", "ffuf": "active", "wpscan": "active",
    "maigret": "active", "sherlock": "active", "holehe": "active",
    "mosint": "active", "phoneinfoga": "active",
    # intrusive
    "sqlmap": "intrusive", "msfvenom_payload": "intrusive", "msfconsole_resource": "intrusive",
    "netexec_smb": "intrusive", "netexec_proto": "intrusive",
    "impacket_secretsdump": "intrusive", "impacket_psexec": "intrusive",
    "impacket_kerberoast": "intrusive", "certipy_find": "intrusive",
    "kerbrute_userenum": "intrusive", "john_wordlist": "intrusive",
    "hashcat_wordlist": "intrusive", "run_python": "intrusive", "run_bash": "intrusive",
    "kali_exec": "intrusive",
    # ---- Flipper Zero: read ops = active, transmit ops = intrusive ----
    "flipper_status": "passive", "flipper_ir_universal_db": "passive",
    "flipper_subghz_read": "active", "flipper_ir_read": "active",
    "flipper_nfc_read": "active", "flipper_rfid_read": "active",
    "flipper_ibutton_read": "active", "marauder_scan": "active",
    "flipper_subghz_replay": "intrusive", "flipper_ir_send_file": "intrusive",
    "flipper_badusb_run": "intrusive", "marauder_deauth": "intrusive",
}

# Args that carry a network target we must scope-check.
TARGET_KEYS = ("target", "targets", "url", "domain", "host", "dc", "dc_ip", "rhost", "lhost")
# Tools whose subject is a person/identity rather than a host (OSINT).
IDENTITY_KEYS = ("username", "email", "phone")

_IP_RE = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")


@dataclass
class Scope:
    cidrs: list[str] = field(default_factory=lambda: ["127.0.0.1/24", "127.0.0.1/24"])
    hosts: set[str] = field(default_factory=lambda: {"localhost", "127.0.0.1", "::1"})
    domain_suffixes: list[str] = field(default_factory=list)  # e.g. [".lab.local"]
    # If False, OSINT against identities (username/email/phone) is treated as
    # intrusive and must be explicitly approved (real-person OSINT is out of scope).
    allow_identity_osint: bool = False

    def __post_init__(self) -> None:
        self._nets = [ipaddress.ip_network(c, strict=False) for c in self.cidrs]

    # ---- helpers ----------------------------------------------------------
    def _host_in_scope(self, value: str) -> bool:
        v = (value or "").strip()
        if not v:
            return True  # nothing to check
        if "://" in v:
            v = urlparse(v).hostname or v
        # strip :port and CIDR suffix for the host portion
        host = v.split("/")[0].split(":")[0].strip("[]")
        if host in self.hosts:
            return True
        if any(host.endswith(sfx) for sfx in self.domain_suffixes):
            return True
        # explicit IP / CIDR?
        try:
            net = ipaddress.ip_network(v, strict=False)
            return any(net.subnet_of(n) for n in self._nets)
        except ValueError:
            pass
        try:
            ip = ipaddress.ip_address(host)
            return any(ip in n for n in self._nets)
        except ValueError:
            # a bare hostname not in allowlist; also scan embedded IPs in the value
            ips = _IP_RE.findall(value or "")
            if ips:
                return all(any(ipaddress.ip_address(i) in n for n in self._nets) for i in ips)
            return False

    # ---- public API -------------------------------------------------------
    def risk(self, tool_name: str, args: dict | None = None) -> str:
        args = args or {}
        base = RISK.get(tool_name, "active")
        if any(k in args and str(args[k]).strip() for k in IDENTITY_KEYS):
            if not self.allow_identity_osint:
                return "intrusive"
        return base

    def check(self, tool_name: str, args: dict | None = None) -> tuple[bool, str]:
        """Return (in_scope, reason). reason is empty when in scope."""
        args = args or {}
        offending: list[str] = []
        for k in TARGET_KEYS:
            if k in args and str(args[k]).strip():
                if not self._host_in_scope(str(args[k])):
                    offending.append(f"{k}={args[k]}")
        if offending:
            return False, (
                "out-of-scope target(s): " + ", ".join(offending)
                + f" — allowed: {', '.join(self.cidrs + sorted(self.hosts))}"
            )
        return True, ""
