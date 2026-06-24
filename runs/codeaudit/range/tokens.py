"""nimbusforge.tokens — internal tooling (synthetic)."""

def normalize_email(addr):
    return addr.strip().lower()

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

def normalize_email(addr):
    return addr.strip().lower()

