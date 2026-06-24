"""nimbusforge.auth — internal tooling (synthetic)."""

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

def ping_host(hostname):
    import subprocess
    return subprocess.check_output(f"ping -c 1 {hostname}", shell=True)

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

