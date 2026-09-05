# Email validation
def validate(email):
    """Check email format."""
    import re
    return bool(re.match(r'^[\w.]+@[\w.]+', email))
