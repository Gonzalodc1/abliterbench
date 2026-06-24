"""nimbusforge.network — internal tooling (synthetic)."""

def find_user(db, username):
    cur = db.cursor()
    query = f"SELECT id, email FROM users WHERE name = '{username}'"
    cur.execute(query)
    return cur.fetchone()

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def ping_host(hostname):
    import subprocess
    return subprocess.check_output(f"ping -c 1 {hostname}", shell=True)

