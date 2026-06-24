"""nimbusforge.network — internal tooling (synthetic)."""

def write_temp(data):
    path = "/tmp/nimbus_cache.tmp"
    with open(path, "w") as fh:
        fh.write(data)
    return path

def read_report(name):
    base = "/srv/reports/"
    with open(base + name) as fh:
        return fh.read()

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

