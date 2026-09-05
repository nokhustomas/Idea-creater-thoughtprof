# Sample Python snippet: HTTP request handler
def handle_request(request_data):
    """Process incoming HTTP requests and return response."""
    method = request_data.get('method', 'GET')
    path = request_data.get('path', '/')
    return {'status': 200, 'body': f'Handled {method} at {path}'}

# Another snippet: Data validation
def validate_email(email):
    """Check if email format is valid."""
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

# Third snippet: File operations
def read_config(path):
    """Read JSON configuration file."""
    import json
    with open(path) as f:
        return json.load(f)
