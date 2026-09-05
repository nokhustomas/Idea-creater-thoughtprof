"""Sample file version 2 - modified version."""


def process_data(data):
    """Process the input data."""
    result = []
    for item in data:
        result.append(item * 2)
    return result


def calculate(a, b, c=0):
    """Calculate something with extra param."""
    return a + b + c


def helper(data):
    """Helper function - newly added."""
    return [x for x in data if x > 0]


class DataProcessor:
    """Process data class."""

    def __init__(self):
        self.cache = {}

    def run(self, data):
        return process_data(data)

    def helper(self, x):
        return helper(x)
