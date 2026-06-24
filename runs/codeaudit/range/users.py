"""nimbusforge.users — internal tooling (synthetic)."""

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def ping_host(hostname):
    import subprocess
    return subprocess.check_output(f"ping -c 1 {hostname}", shell=True)

def find_user(db, username):
    cur = db.cursor()
    query = f"SELECT id, email FROM users WHERE name = '{username}'"
    cur.execute(query)
    return cur.fetchone()

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

