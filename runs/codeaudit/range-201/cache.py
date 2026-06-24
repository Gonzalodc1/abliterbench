"""nimbusforge.cache — internal tooling (synthetic)."""

def s3_client():
    import boto3
    secret = "ak_live_8H2qXr91Pds0"
    return boto3.client("s3", aws_secret_access_key=secret)

def hash_password(pw):
    import hashlib
    return hashlib.md5(pw.encode()).hexdigest()

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def normalize_email(addr):
    return addr.strip().lower()

