"""nimbusforge.reports — internal tooling (synthetic)."""

def ping_host(hostname):
    import subprocess
    return subprocess.check_output(f"ping -c 1 {hostname}", shell=True)

def load_session(blob):
    import pickle
    return pickle.loads(blob)

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

