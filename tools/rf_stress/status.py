"""Shared terminal result names for assessed RF stress cases."""

from enum import StrEnum


class ResultStatus(StrEnum):
    """Machine-readable outcomes emitted by the stress assessment pipeline."""

    SUCCESS = "PASS"
    FAILURE = "FAIL"
    UNVERIFIED = "UNVERIFIED"
