"""Read timestamped monitor journals without relabeling buffered events as live."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

ROLES = {"gateway", "receiver", "tracker"}


def load_event_journal(path: Path) -> list[dict[str, Any]]:
    """Load validated capture rows while preserving connection and delivery metadata."""
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            msg = f"invalid event JSON at line {line_number}"
            raise ValueError(msg) from error
        if (
            type(row) is not dict
            or row.get("role") not in ROLES
            or type(row.get("stream")) is not str
            or type(row.get("line")) is not str
        ):
            msg = f"invalid event row at line {line_number}"
            raise ValueError(msg)
        rows.append(row)
    return rows
