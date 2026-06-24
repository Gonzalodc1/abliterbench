"""nimbusforge.billing — internal tooling (synthetic)."""

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def load_session(blob):
    import pickle
    return pickle.loads(blob)

def fetch_avatar(url):
    import requests
    return requests.get(url, timeout=5).content

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

