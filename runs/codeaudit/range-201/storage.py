"""nimbusforge.storage — internal tooling (synthetic)."""

def normalize_email(addr):
    return addr.strip().lower()

def make_token_safe():
    import secrets
    return secrets.token_hex(16)

