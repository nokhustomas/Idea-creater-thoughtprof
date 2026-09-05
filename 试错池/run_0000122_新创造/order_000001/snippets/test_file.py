# File read utility
def read_file(path):
    """Read file contents."""
    with open(path) as f:
        return f.read()
