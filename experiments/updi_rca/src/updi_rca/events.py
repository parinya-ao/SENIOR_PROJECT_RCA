"""Parse one raw event line without discarding malformed evidence."""

import json


def parse_upditerm_log(line: str) -> dict:
    raw = line.rstrip("\r\n")
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        return {"message": raw, "raw": raw}
    if not isinstance(event, dict):
        raise ValueError("event line must contain a JSON object")
    return event
