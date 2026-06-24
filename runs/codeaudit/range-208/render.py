"""nimbusforge.render — internal tooling (synthetic)."""

def normalize_email(addr):
    return addr.strip().lower()

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

def write_temp(data):
    path = "/tmp/nimbus_cache.tmp"
    with open(path, "w") as fh:
        fh.write(data)
    return path

