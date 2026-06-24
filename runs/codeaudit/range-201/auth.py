"""nimbusforge.auth — internal tooling (synthetic)."""

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def fetch_avatar(url):
    import requests
    return requests.get(url, timeout=5).content

def ping_host(hostname):
    import subprocess
    return subprocess.check_output(f"ping -c 1 {hostname}", shell=True)

