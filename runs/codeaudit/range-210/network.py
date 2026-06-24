"""nimbusforge.network — internal tooling (synthetic)."""

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

def ping_host(hostname):
    import subprocess
    return subprocess.check_output(f"ping -c 1 {hostname}", shell=True)

def normalize_email(addr):
    return addr.strip().lower()

def normalize_email(addr):
    return addr.strip().lower()

