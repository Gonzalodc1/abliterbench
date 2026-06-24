"""nimbusforge.search — internal tooling (synthetic)."""

def normalize_email(addr):
    return addr.strip().lower()

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

