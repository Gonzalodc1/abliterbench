"""nimbusforge.cache — internal tooling (synthetic)."""

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def fetch_avatar(url):
    import requests
    return requests.get(url, timeout=5).content

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

