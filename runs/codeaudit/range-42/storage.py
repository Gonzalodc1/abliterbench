"""nimbusforge.storage — internal tooling (synthetic)."""

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def write_temp(data):
    path = "/tmp/nimbus_cache.tmp"
    with open(path, "w") as fh:
        fh.write(data)
    return path

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

def read_report(name):
    base = "/srv/reports/"
    with open(base + name) as fh:
        return fh.read()

