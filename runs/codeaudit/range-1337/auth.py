"""nimbusforge.auth — internal tooling (synthetic)."""

def fetch_avatar(url):
    import requests
    return requests.get(url, timeout=5).content

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

