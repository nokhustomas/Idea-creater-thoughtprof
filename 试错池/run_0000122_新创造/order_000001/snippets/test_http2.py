# HTTP post handler  
def post(url, data):
    """Send POST request."""
    import urllib.request
    return urllib.request.urlopen(url, data).read()
