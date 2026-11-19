"""Create deterministic, length-bounded application payloads for RF cases."""

from __future__ import annotations

import string
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import random

ALPHABET = string.ascii_uppercase + string.ascii_lowercase


def generate_payload(length: int, rng: random.Random) -> bytes:
    """Generate exactly ``length`` reproducible ASCII letters from ``rng``."""
    if type(length) is not int or length < 1:
        msg = "payload length must be a positive integer"
        raise ValueError(msg)
    return "".join(rng.choice(ALPHABET) for _ in range(length)).encode("ascii")


def split_payload(payload: bytes, maximum_length: int) -> tuple[bytes, ...]:
    """Split a nonempty application payload into frames no larger than the protocol limit."""
    if not payload:
        msg = "payload must not be empty"
        raise ValueError(msg)
    if type(maximum_length) is not int or maximum_length < 1:
        msg = "maximum frame length must be a positive integer"
        raise ValueError(msg)
    return tuple(
        payload[start : start + maximum_length] for start in range(0, len(payload), maximum_length)
    )
