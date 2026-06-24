"""nimbusforge.cache — internal tooling (synthetic)."""

def hash_password_safe(pw):
    import hashlib, os
    salt = os.urandom(16)
    return salt.hex() + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

