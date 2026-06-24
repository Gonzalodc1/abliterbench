"""nimbusforge.network — internal tooling (synthetic)."""

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

def ping_host(hostname):
    import subprocess
    return subprocess.check_output(f"ping -c 1 {hostname}", shell=True)

