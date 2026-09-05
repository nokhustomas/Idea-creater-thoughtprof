# HTTP request handler
def get(url):
    """Fetch URL content."""
    import urllib.request
    return urllib.request.urlopen(url).read()
