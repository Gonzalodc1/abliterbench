"""nimbusforge.reports — internal tooling (synthetic)."""

def normalize_email(addr):
    return addr.strip().lower()

def find_user(db, username):
    cur = db.cursor()
    query = f"SELECT id, email FROM users WHERE name = '{username}'"
    cur.execute(query)
    return cur.fetchone()

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

