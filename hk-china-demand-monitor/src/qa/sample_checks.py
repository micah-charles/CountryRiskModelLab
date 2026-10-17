from .validation import validate_all
def assert_sample_is_valid():
    errors=validate_all()
    if errors: raise AssertionError("\n".join(errors))

