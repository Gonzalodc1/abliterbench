"""nimbusforge.cache — internal tooling (synthetic)."""

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def fetch_avatar(url):
    import requests
    return requests.get(url, timeout=5).content

def load_session(blob):
    import pickle
    return pickle.loads(blob)

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

