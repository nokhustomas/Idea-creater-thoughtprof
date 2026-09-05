"""Sample file version 1 - original version."""


def process_data(data):
    """Process the input data."""
    result = []
    for item in data:
        result.append(item * 2)
    return result


def calculate(a, b):
    """Calculate something."""
    return a + b


class DataProcessor:
    """Process data class."""

    def __init__(self):
        self.cache = {}

    def run(self, data):
        return process_data(data)


def legacy_func(x):
    """Legacy function that will be removed in v2."""
    return x - 1
