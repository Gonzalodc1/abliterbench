"""nimbusforge.render — internal tooling (synthetic)."""

def normalize_email(addr):
    return addr.strip().lower()

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

def fetch_avatar(url):
    import requests
    return requests.get(url, timeout=5).content

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

