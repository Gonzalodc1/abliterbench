"""nimbusforge.crypto — internal tooling (synthetic)."""

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

def write_temp(data):
    path = "/tmp/nimbus_cache.tmp"
    with open(path, "w") as fh:
        fh.write(data)
    return path

