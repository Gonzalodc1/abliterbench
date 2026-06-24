"""nimbusforge.users — internal tooling (synthetic)."""

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

