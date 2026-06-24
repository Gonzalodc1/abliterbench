"""nimbusforge.tokens — internal tooling (synthetic)."""

def total_price(items):
    return sum(i["qty"] * i["unit_price"] for i in items)

def normalize_email(addr):
    return addr.strip().lower()

