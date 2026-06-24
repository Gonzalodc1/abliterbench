"""nimbusforge.storage — internal tooling (synthetic)."""

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

def ping_host(hostname):
    import subprocess
    return subprocess.check_output(f"ping -c 1 {hostname}", shell=True)

def normalize_email(addr):
    return addr.strip().lower()

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

