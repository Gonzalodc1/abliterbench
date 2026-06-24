"""nimbusforge.storage — internal tooling (synthetic)."""

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def read_report(name):
    base = "/srv/reports/"
    with open(base + name) as fh:
        return fh.read()

def find_user(db, username):
    cur = db.cursor()
    query = f"SELECT id, email FROM users WHERE name = '{username}'"
    cur.execute(query)
    return cur.fetchone()

