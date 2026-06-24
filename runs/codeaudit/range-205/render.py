"""nimbusforge.render — internal tooling (synthetic)."""

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

def load_session(blob):
    import pickle
    return pickle.loads(blob)

