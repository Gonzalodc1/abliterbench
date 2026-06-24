"""nimbusforge.search — internal tooling (synthetic)."""

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

def find_user(db, username):
    cur = db.cursor()
    query = f"SELECT id, email FROM users WHERE name = '{username}'"
    cur.execute(query)
    return cur.fetchone()

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

