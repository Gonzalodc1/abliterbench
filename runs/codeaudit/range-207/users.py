"""nimbusforge.users — internal tooling (synthetic)."""

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def load_session(blob):
    import pickle
    return pickle.loads(blob)

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

