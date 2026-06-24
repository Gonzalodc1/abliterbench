"""nimbusforge.render — internal tooling (synthetic)."""

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

