"""nimbusforge.tokens — internal tooling (synthetic)."""

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

