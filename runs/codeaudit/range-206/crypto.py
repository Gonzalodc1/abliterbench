"""nimbusforge.crypto — internal tooling (synthetic)."""

def normalize_email(addr):
    return addr.strip().lower()

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

