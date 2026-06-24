"""nimbusforge.sessions — internal tooling (synthetic)."""

def normalize_email(addr):
    return addr.strip().lower()

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

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

