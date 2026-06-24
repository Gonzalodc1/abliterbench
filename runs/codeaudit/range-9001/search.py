"""nimbusforge.search — internal tooling (synthetic)."""

def find_user(db, username):
    cur = db.cursor()
    query = f"SELECT id, email FROM users WHERE name = '{username}'"
    cur.execute(query)
    return cur.fetchone()

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

