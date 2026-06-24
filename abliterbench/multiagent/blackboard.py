"""Shared structured mission state.

The blackboard externalises everything the small model cannot reliably hold
in-context across a long mission: discovered hosts, services, credentials and
the running evidence corpus. The controller passes only the relevant slice to
each worker so each one starts with a small, clean context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# crude but effective extractors over recon tool output
_URL_RE = re.compile(r"https?://[^\s\]\"'<>]+")
_HOSTPORT_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b(?::(\d+))?")
_OPENPORT_RE = re.compile(r"(\d{1,5})/tcp\s+open\s+(\S+)", re.I)


@dataclass
class Blackboard:
    target: str
    hosts: set[str] = field(default_factory=set)
    urls: set[str] = field(default_factory=set)
    services: list[dict] = field(default_factory=list)   # {host, port, service}
    creds: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)  # global evidence corpus (tool-sig -> snippet)

    def ingest_evidence(self, evidence: dict[str, str]) -> None:
        """Merge a worker's evidence and auto-extract hosts/urls/services."""
        for k, v in evidence.items():
            self.evidence[k] = v
            text = f"{k}\n{v}"
            for u in _URL_RE.findall(text):
                self.urls.add(u.rstrip(".,);"))
            for ip, port in _HOSTPORT_RE.findall(text):
                self.hosts.add(ip)
                if port:
                    self._add_service(ip, int(port), "")
            for port, svc in _OPENPORT_RE.findall(text):
                # associate with the target host if it is an IP
                host = next(iter(self.hosts), self.target)
                self._add_service(host, int(port), svc)

    def _add_service(self, host: str, port: int, svc: str) -> None:
        for s in self.services:
            if s["host"] == host and s["port"] == port:
                if svc and not s.get("service"):
                    s["service"] = svc
                return
        self.services.append({"host": host, "port": port, "service": svc})

    def web_targets(self) -> list[str]:
        """URLs / http(s) services the web worker should assess."""
        out = set(u for u in self.urls if u.startswith("http"))
        for s in self.services:
            if s.get("service", "").lower().startswith("http") or s["port"] in (80, 443, 3000, 8080, 8443):
                scheme = "https" if s["port"] in (443, 8443) else "http"
                out.add(f"{scheme}://{s['host']}:{s['port']}")
        return sorted(out)

    def slice_for(self, role: str) -> str:
        """A compact context string for a worker (only what it needs)."""
        lines = [f"Target: {self.target}"]
        if self.hosts:
            lines.append("Hosts: " + ", ".join(sorted(self.hosts)))
        if self.services:
            lines.append("Services: " + ", ".join(
                f"{s['host']}:{s['port']}/{s.get('service') or '?'}" for s in self.services[:12]))
        if role in ("web_exploit",) and self.web_targets():
            lines.append("Web targets: " + ", ".join(self.web_targets()[:8]))
        if self.notes:
            lines.append("Notes: " + " | ".join(self.notes[-5:]))
        return "\n".join(lines)

    def summary(self) -> dict:
        return {"hosts": sorted(self.hosts), "services": self.services,
                "urls": sorted(self.urls), "evidence_items": len(self.evidence)}
