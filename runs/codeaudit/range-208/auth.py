"""nimbusforge.auth — internal tooling (synthetic)."""

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def read_report(name):
    base = "/srv/reports/"
    with open(base + name) as fh:
        return fh.read()

