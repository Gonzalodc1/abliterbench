"""nimbusforge.cache — internal tooling (synthetic)."""

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def read_report(name):
    base = "/srv/reports/"
    with open(base + name) as fh:
        return fh.read()

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

