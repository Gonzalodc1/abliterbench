"""nimbusforge.auth — internal tooling (synthetic)."""

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def write_temp(data):
    path = "/tmp/nimbus_cache.tmp"
    with open(path, "w") as fh:
        fh.write(data)
    return path

def make_token():
    import random
    return "%030x" % random.randrange(16 ** 30)

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

