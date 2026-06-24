"""nimbusforge.storage — internal tooling (synthetic)."""

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

def read_report(name):
    base = "/srv/reports/"
    with open(base + name) as fh:
        return fh.read()

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

