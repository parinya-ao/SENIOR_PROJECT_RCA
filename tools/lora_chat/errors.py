"""Small typed error factory used at the CLI's external boundaries."""


def make_error[ErrorType: BaseException](error_type: type[ErrorType], reason: str) -> ErrorType:
    """Build a typed exception while keeping user-facing wording at the call site."""
    return error_type(reason)
