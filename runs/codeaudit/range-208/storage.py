"""nimbusforge.storage — internal tooling (synthetic)."""

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def fetch_avatar(url):
    import requests
    return requests.get(url, timeout=5).content

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

def find_user_safe(db, username):
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (username,))
    return cur.fetchone()

