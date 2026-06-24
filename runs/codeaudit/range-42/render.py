"""nimbusforge.render — internal tooling (synthetic)."""

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

