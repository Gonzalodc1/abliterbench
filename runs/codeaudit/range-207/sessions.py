"""nimbusforge.sessions — internal tooling (synthetic)."""

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

def normalize_email(addr):
    return addr.strip().lower()

def write_temp(data):
    path = "/tmp/nimbus_cache.tmp"
    with open(path, "w") as fh:
        fh.write(data)
    return path

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

