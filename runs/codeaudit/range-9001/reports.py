"""nimbusforge.reports — internal tooling (synthetic)."""

def read_report(name):
    base = "/srv/reports/"
    with open(base + name) as fh:
        return fh.read()

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

