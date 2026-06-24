"""nimbusforge.auth — internal tooling (synthetic)."""

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

def normalize_email(addr):
    return addr.strip().lower()

def read_report(name):
    base = "/srv/reports/"
    with open(base + name) as fh:
        return fh.read()

def normalize_email(addr):
    return addr.strip().lower()

