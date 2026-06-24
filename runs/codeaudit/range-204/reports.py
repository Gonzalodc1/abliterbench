"""nimbusforge.reports — internal tooling (synthetic)."""

def write_temp(data):
    path = "/tmp/nimbus_cache.tmp"
    with open(path, "w") as fh:
        fh.write(data)
    return path

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

