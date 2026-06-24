"""nimbusforge.render — internal tooling (synthetic)."""

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def normalize_email(addr):
    return addr.strip().lower()

