"""Tool catalog (OpenAI-style schemas) + bridge dispatcher.

Exposes the AbliterBench Kali bridge endpoints plus the code workspace and RAG
as tools the model can call. The catalog is self-contained so the operator does
not depend on the agent_chat CLI module.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx


@dataclass
class Tool:
    name: str
    category: str
    description: str
    schema: dict
    path: str
    keys: list[str]
    fixed: dict = field(default_factory=dict)  # constant payload fields (e.g. {"lang":"python"})


def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


CATALOG: list[Tool] = [
    # ---- RAG knowledge base ----
    Tool("rag_search", "rag",
         "Semantic search over the local offensive-security knowledge base "
         "(corpora: hacktricks, payloads, gtfobins, lolbas, mitre_attack, owasp_wstg, "
         "owasp_top10, exploitdb, cisa_kev, ired_team, pentest_book, flipper, tools).",
         _obj({"query": {"type": "string", "description": "specific natural-language query"},
               "corpus": {"type": "string", "description": "corpus name, e.g. hacktricks/gtfobins"},
               "top_k": {"type": "integer"}}, ["query"]),
         "/rag_search", ["query", "corpus", "top_k"]),

    # ---- Recon passive ----
    Tool("subfinder", "recon", "Passive subdomain enumeration for a registered domain.",
         _obj({"domain": {"type": "string"}}, ["domain"]), "/subfinder", ["domain"]),
    Tool("dnsx_lookup", "recon", "DNS record lookup (A/AAAA/MX/TXT/CNAME).",
         _obj({"domain": {"type": "string"}}, ["domain"]), "/dnsx", ["domain"]),
    Tool("web_fetch", "recon", "Fetch the raw HTTP(S) response body of a URL (follows redirects).",
         _obj({"url": {"type": "string"}}, ["url"]), "/web_fetch", ["url"]),

    # ---- Recon active ----
    Tool("httpx_probe", "recon",
         "Probe a URL/host with httpx: status, title, server, tech stack, TLS, redirects.",
         _obj({"domain": {"type": "string", "description": "host or full URL"}}, ["domain"]),
         "/httpx", ["domain"]),
    Tool("nmap_scan", "recon", "nmap port/service scan against an IP, host, or CIDR.",
         _obj({"target": {"type": "string"}, "ports": {"type": "string"},
               "flags": {"type": "string"}}, ["target"]), "/nmap", ["target", "ports", "flags"]),
    Tool("naabu", "recon", "Fast SYN port scan (ProjectDiscovery).",
         _obj({"target": {"type": "string"}, "ports": {"type": "string"}}, ["target"]),
         "/naabu", ["target", "ports"]),
    Tool("katana_crawl", "recon", "Crawl a web app and emit discovered URLs.",
         _obj({"url": {"type": "string"}}, ["url"]), "/katana", ["url"]),

    # ---- OSINT ----
    Tool("maigret", "osint", "Search a username across ~3000 platforms.",
         _obj({"username": {"type": "string"}}, ["username"]), "/maigret", ["username"]),
    Tool("sherlock", "osint", "Search a username across ~400 sites (fast).",
         _obj({"username": {"type": "string"}}, ["username"]), "/sherlock", ["username"]),
    Tool("holehe", "osint", "Check if an email is registered on ~120 services.",
         _obj({"email": {"type": "string"}}, ["email"]), "/holehe", ["email"]),
    Tool("mosint", "osint", "Email OSINT meta-tool (breaches, social, services).",
         _obj({"email": {"type": "string"}}, ["email"]), "/mosint", ["email"]),
    Tool("phoneinfoga", "osint", "OSINT for a phone number (carrier, country, reputation).",
         _obj({"phone": {"type": "string"}}, ["phone"]), "/phoneinfoga", ["phone"]),

    # ---- Synthetic OSINT range (Track 1, local seeded data only) ----
    Tool("osint_people_search", "osint_range",
         "Search the local synthetic OSINT range for profiles matching a name, username or email "
         "(local analogue of maigret). Returns matching profile URLs to fetch with web_fetch.",
         _obj({"query": {"type": "string"}}, ["query"]), "/osint_people_search", ["query"]),
    Tool("osint_breach_lookup", "osint_range",
         "Look up a leaked credential for an email in the local synthetic breach dump (analogue of "
         "holehe/breach search). Synthetic data only.",
         _obj({"email": {"type": "string"}}, ["email"]), "/osint_breach_lookup", ["email"]),

    # ---- Web pwn ----
    Tool("nuclei_scan", "web", "Template-based vulnerability scan of a URL (CVEs, misconfigs).",
         _obj({"url": {"type": "string"}}, ["url"]), "/nuclei", ["url"]),
    Tool("ffuf", "web", "Web fuzzer (dirs/params/vhosts). url must contain FUZZ.",
         _obj({"url": {"type": "string"}, "wordlist": {"type": "string"}}, ["url"]),
         "/ffuf", ["url", "wordlist"]),
    Tool("gobuster_dir", "web", "Brute-force directories/files on a web target.",
         _obj({"url": {"type": "string"}, "wordlist": {"type": "string"},
               "extensions": {"type": "string"}}, ["url"]),
         "/gobuster_dir", ["url", "wordlist", "extensions"]),
    Tool("nikto", "web", "Classic web server vulnerability scanner.",
         _obj({"url": {"type": "string"}}, ["url"]), "/nikto", ["url"]),
    Tool("sqlmap", "web", "Automatic SQL injection detection/exploitation.",
         _obj({"url": {"type": "string"}, "data": {"type": "string"},
               "cookie": {"type": "string"}}, ["url"]), "/sqlmap", ["url", "data", "cookie"]),
    Tool("wpscan", "web", "WordPress vulnerability scanner.",
         _obj({"url": {"type": "string"}}, ["url"]), "/wpscan", ["url"]),

    # ---- Exploit research ----
    Tool("searchsploit", "exploit", "Search the local Exploit-DB mirror for public exploits.",
         _obj({"query": {"type": "string"}}, ["query"]), "/searchsploit", ["query"]),
    Tool("searchsploit_show", "exploit", "Show the source/notes of a specific exploit path.",
         _obj({"query": {"type": "string", "description": "exploit path from searchsploit"}},
              ["query"]), "/searchsploit_show", ["query"]),
    Tool("msfvenom_payload", "exploit", "Generate a Metasploit payload.",
         _obj({"payload": {"type": "string"}, "lhost": {"type": "string"},
               "lport": {"type": "integer"}, "format": {"type": "string"}},
              ["payload", "lhost", "lport"]),
         "/msfvenom_payload", ["payload", "lhost", "lport", "format"]),

    # ---- AD pwn ----
    Tool("netexec_smb", "ad", "NetExec SMB: enumerate/auth/exec over SMB.",
         _obj({"targets": {"type": "string"}, "username": {"type": "string"},
               "password": {"type": "string"}, "command": {"type": "string"}}, ["targets"]),
         "/netexec_smb", ["targets", "username", "password", "command"]),
    Tool("kerbrute_userenum", "ad", "Enumerate Kerberos usernames against a DC.",
         _obj({"dc": {"type": "string"}, "domain": {"type": "string"},
               "user_list": {"type": "string"}}, ["dc", "domain", "user_list"]),
         "/kerbrute_userenum", ["dc", "domain", "user_list"]),

    # ---- Secret discovery ----
    Tool("trufflehog", "secrets", "Scan a git repo/filesystem/URL for leaked secrets.",
         _obj({"target": {"type": "string"}, "target_type": {"type": "string"}}, ["target"]),
         "/trufflehog", ["target", "target_type"]),

    # ---- Code workspace ----
    Tool("write_file", "workspace", "Write text to a file in the code workspace (sandboxed).",
         _obj({"path": {"type": "string"}, "content": {"type": "string"}},
              ["path", "content"]), "/fs_write", ["path", "content", "append"]),
    Tool("read_file", "workspace",
         "Read a file from the workspace. Extracts text from .pdf/.docx automatically.",
         _obj({"path": {"type": "string"}}, ["path"]), "/fs_read", ["path", "max_bytes"]),
    Tool("list_files", "workspace", "List files in the workspace.",
         _obj({"path": {"type": "string"}}, []), "/fs_ls", ["path"]),
    Tool("run_python", "workspace",
         "Execute Python in the workspace (cwd=workspace). Provide inline `code` "
         "or a `file` path. Use to parse tool output, script logic, build artifacts.",
         _obj({"code": {"type": "string"}, "file": {"type": "string"},
               "timeout_s": {"type": "integer"}}, []),
         "/workspace_exec", ["code", "file", "timeout_s"], {"lang": "python"}),
    Tool("run_bash", "workspace", "Execute a bash command/script in the workspace.",
         _obj({"code": {"type": "string"}, "file": {"type": "string"},
               "timeout_s": {"type": "integer"}}, []),
         "/workspace_exec", ["code", "file", "timeout_s"], {"lang": "bash"}),

    # ---- Flipper Zero (physical / RF, TIER 3) ----
    # Read ops engage the radio/NFC but don't transmit; TX ops (replay, ir_send,
    # badusb, deauth) are bridge-gated by FLIPPER_TX_ALLOW and risk=intrusive.
    Tool("flipper_status", "flipper", "Query the attached Flipper Zero (firmware, hardware).",
         _obj({}, []), "/flipper_status", []),
    Tool("flipper_subghz_read", "flipper",
         "Listen on a sub-GHz frequency and capture raw timings (RX only, no transmit). "
         "Default 433.92 MHz ISM. Use to capture a remote/key-fob signal.",
         _obj({"frequency_hz": {"type": "integer"}, "duration_s": {"type": "integer"}}, []),
         "/flipper_subghz_read", ["frequency_hz", "duration_s"]),
    Tool("flipper_subghz_replay", "flipper",
         "Replay a captured .sub file over the air (TRANSMITS). Own devices / legal bands only.",
         _obj({"path": {"type": "string", "description": "/ext/subghz/<file>.sub"}}, ["path"]),
         "/flipper_subghz_replay", ["path"]),
    Tool("flipper_ir_read", "flipper", "Listen for an IR signal and decode protocol (RX only).",
         _obj({"timeout_s": {"type": "integer"}}, []), "/flipper_ir_read", ["timeout_s"]),
    Tool("flipper_ir_universal_db", "flipper",
         "Look up matching .ir files in the local Flipper-IRDB for a brand/device (read-only).",
         _obj({"brand": {"type": "string"}, "device_type": {"type": "string"}}, ["brand"]),
         "/flipper_ir_universal_db", ["brand", "device_type"]),
    Tool("flipper_ir_send_file", "flipper",
         "Transmit a stored .ir file (TRANSMITS). Own devices only.",
         _obj({"path": {"type": "string"}}, ["path"]), "/flipper_ir_send_file", ["path"]),
    Tool("flipper_nfc_read", "flipper", "Read an NFC tag: UID, ATQA/SAK, type (RX only).",
         _obj({}, []), "/flipper_nfc_read", []),
    Tool("flipper_rfid_read", "flipper", "Read a 125 kHz LF card (EM4100, HID Prox, Indala).",
         _obj({}, []), "/flipper_rfid_read", []),
    Tool("flipper_ibutton_read", "flipper", "Read a Dallas iButton (DS1990A, Cyfral, Metakom).",
         _obj({}, []), "/flipper_ibutton_read", []),
    Tool("flipper_badusb_run", "flipper",
         "Run a DuckyScript as USB-HID on the plugged-in host (EXECUTES KEYSTROKES). Own machines only.",
         _obj({"script": {"type": "string"}}, ["script"]), "/flipper_badusb_run", ["script"]),
    Tool("marauder_scan", "flipper", "ESP32 Marauder Wi-Fi scan: list APs + clients in range (RX).",
         _obj({}, []), "/marauder_scan", []),
    Tool("marauder_deauth", "flipper",
         "ESP32 Marauder deauth a Wi-Fi client (TRANSMITS 802.11 deauth). Own Wi-Fi only.",
         _obj({"bssid": {"type": "string"}, "channel": {"type": "integer"}}, ["bssid"]),
         "/marauder_deauth", ["bssid", "client", "channel"]),

    # ---- Generic whitelisted exec ----
    Tool("kali_exec", "generic",
         "Run a whitelisted Kali binary (id, whoami, cat, dig, host, ping, curl, wget, "
         "openssl, base64, jq, python3, strings, file, exiftool, binwalk, ...).",
         _obj({"cmd": {"type": "string"}, "args": {"type": "array",
               "items": {"type": "string"}}}, ["cmd"]), "/kali_exec", ["cmd", "args"]),
]

CATEGORIES = sorted({t.category for t in CATALOG})
_BY_NAME = {t.name: t for t in CATALOG}


def find_tool(name: str) -> Tool | None:
    return _BY_NAME.get(name)


def filter_catalog(filter_str: str) -> list[Tool]:
    if not filter_str or filter_str == "all":
        return list(CATALOG)
    wanted = {s.strip() for s in filter_str.split(",")}
    out = [t for t in CATALOG if t.category in wanted or t.name in wanted]
    return out or list(CATALOG)


def schemas_for(tools: list[Tool]) -> list[dict]:
    return [{"type": "function", "function": {
        "name": t.name, "description": t.description, "parameters": t.schema}} for t in tools]


class Bridge:
    """HTTP client for the AbliterBench Kali tool bridge."""

    def __init__(self, base_url: str = "http://127.0.0.1:8765", timeout_s: float = 120.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout_s

    def health(self) -> tuple[bool, int]:
        try:
            r = httpx.get(self.base + "/", timeout=6.0)
            r.raise_for_status()
            return True, len(r.json().get("endpoints", []))
        except Exception:
            return False, 0

    def call(self, tool_name: str, args: dict, timeout_s: float | None = None) -> dict:
        tool = find_tool(tool_name)
        if tool is None:
            return {"ok": False, "exit": -1, "stdout": "", "stderr": f"unknown tool {tool_name}"}
        payload = {k: args[k] for k in tool.keys if k in args and args[k] not in (None, "")}
        payload.update(tool.fixed)
        try:
            r = httpx.post(self.base + tool.path, json=payload,
                           timeout=timeout_s or self.timeout)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            return {"ok": False, "exit": -1, "stdout": "",
                    "stderr": f"HTTP {e.response.status_code}: {e.response.text[:300]}"}
        except Exception as e:
            return {"ok": False, "exit": -1, "stdout": "", "stderr": str(e)}
