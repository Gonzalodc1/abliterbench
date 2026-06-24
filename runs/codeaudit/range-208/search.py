"""nimbusforge.search — internal tooling (synthetic)."""

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def load_session(blob):
    import pickle
    return pickle.loads(blob)

def ping_host(hostname):
    import subprocess
    return subprocess.check_output(f"ping -c 1 {hostname}", shell=True)

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

