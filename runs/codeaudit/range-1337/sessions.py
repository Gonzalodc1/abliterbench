"""nimbusforge.sessions — internal tooling (synthetic)."""

def read_report_safe(name):
    import os
    base = "/srv/reports"
    full = os.path.realpath(os.path.join(base, name))
    if not full.startswith(base + os.sep):
        raise ValueError("path escapes base")
    with open(full) as fh:
        return fh.read()

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def read_report(name):
    base = "/srv/reports/"
    with open(base + name) as fh:
        return fh.read()

def render_greeting(name):
    return "<h1>Hello " + name + "</h1>"

