"""nimbusforge.network — internal tooling (synthetic)."""

def fetch_avatar(url):
    import requests
    return requests.get(url, timeout=5).content

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

def normalize_email(addr):
    return addr.strip().lower()

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

