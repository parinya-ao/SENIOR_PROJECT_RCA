"""Build epoch-tagged run and protocol-event rows from bounded raw probes."""


def _echo_class(expected: bytes, observed: bytes) -> str:
    if observed == expected:
        return "EXACT_ECHO"
    if not observed:
        return "ECHO_EMPTY"
    if len(observed) < len(expected):
        return "ECHO_SHORT"
    if len(observed) > len(expected):
        return "ECHO_EXTRA"
    return "ECHO_WRONG_BYTE"


def attempt_rows(
    record: dict,
    *,
    epoch_id: str,
    run_id: str,
    lane: str,
    attempt: int,
    adapter_id_path: str,
    current_tty: str,
    adapter_fingerprint: str,
    target_fingerprint: str,
    pairing_state: str,
    raw_log_path: str,
    raw_sha256: str,
) -> tuple[dict, list[dict]]:
    """Convert one hashed probe record without merging echo and target failures."""
    if not epoch_id or not run_id or attempt < 1:
        raise ValueError("epoch_id, run_id and a positive attempt number are required")

    mode = record.get("mode", "UNKNOWN").upper()
    raw_events = record.get("events", [])
    tx, echo, response = [], [], []
    protocol_events = []
    pending_tx = b""
    echo_classes = []

    for index, event in enumerate(raw_events, 1):
        kind = event.get("kind")
        payload = bytes.fromhex(event.get("hex", ""))
        tx_hex = echo_hex = response_hex = ""
        expected_len = event.get("requested")
        actual_len = len(payload)
        status = event.get("status_raw", "")

        if kind == "tx":
            tx.append(payload)
            pending_tx = payload
            stage, direction, operation = "HOST_TX", "HOST_TO_ADAPTER", mode
            tx_hex = payload.hex()
            expected_len = len(payload)
            actual_len = event.get("count", len(payload))
            classification = "HOST_WRITE_RECORDED" if actual_len == expected_len else "HOST_WRITE_SHORT"
        elif kind == "echo":
            echo.append(payload)
            stage, direction, operation = "LOCAL_ECHO", "SERIAL_ECHO_TO_HOST", "half_duplex_echo"
            tx_hex, echo_hex = pending_tx.hex(), payload.hex()
            classification = _echo_class(pending_tx, payload)
            echo_classes.append(classification)
            pending_tx = b""
        elif kind == "response":
            response.append(payload)
            stage = event.get("stage") or (
                "ACC_DATA_RESPONSE" if mode == "READ" else "UPDI_CONTROL_RESPONSE"
            )
            direction, operation = "TARGET_TO_HOST", mode
            response_hex = payload.hex()
            classification = "RESPONSE_RECEIVED" if len(payload) == expected_len else "RESPONSE_MISSING"
        else:
            stage, direction, operation = "UNKNOWN", "UNKNOWN", str(kind or "UNKNOWN")
            classification = "UNCLASSIFIED_EVENT"

        protocol_events.append({
            "epoch_id": epoch_id,
            "run_id": run_id,
            "event_id": f"{epoch_id}:{run_id}:{attempt:04d}:{index:03d}",
            "timestamp_wall": record.get("utc", ""),
            "timestamp_monotonic_ns": event.get("ns", ""),
            "lane": lane,
            "adapter_id_path": adapter_id_path,
            "current_tty": current_tty,
            "physical_usb_path": adapter_id_path,
            "adapter_fingerprint": adapter_fingerprint,
            "target_fingerprint": target_fingerprint,
            "pairing_id": f"{epoch_id}|{adapter_id_path}|{target_fingerprint}",
            "pairing_state": pairing_state,
            "test_condition": mode,
            "attempt": attempt,
            "stage": stage,
            "direction": direction,
            "operation": operation,
            "address": record.get("address") if record.get("address") is not None else "",
            "tx_hex": tx_hex,
            "echo_hex": echo_hex,
            "response_hex": response_hex,
            "expected_len": expected_len if expected_len is not None else "",
            "actual_len": actual_len,
            "status_raw": status,
            "errno": event.get("errno", ""),
            "classification": classification,
            "raw_log_path": raw_log_path,
            "raw_sha256": raw_sha256,
        })

    failure_stage = record.get("failure_stage", "")
    run_row = {
        "epoch_id": epoch_id,
        "run_id": run_id,
        "timestamp_wall": record.get("utc", ""),
        "timestamp_monotonic_ns": raw_events[0].get("ns", "") if raw_events else "",
        "lane": lane,
        "adapter_id_path": adapter_id_path,
        "current_tty": current_tty,
        "physical_usb_path": adapter_id_path,
        "adapter_fingerprint": adapter_fingerprint,
        "target_fingerprint": target_fingerprint,
        "pairing_id": f"{epoch_id}|{adapter_id_path}|{target_fingerprint}",
        "pairing_state": pairing_state,
        "test_condition": mode,
        "attempt": attempt,
        "baud": record.get("baud", ""),
        "cpu_state": "UNKNOWN_OR_UNCONTROLLED",
        "firmware_sha256": "UNKNOWN_NOT_SNAPSHOTTED",
        "result": "PASS" if record.get("exit") == 0 else "FAIL",
        "failure_stage": failure_stage,
        "error_type": record.get("first_anomaly", ""),
        "latency_ms": record.get("latency_ms", ""),
        "tx_hex": "".join(item.hex() for item in tx),
        "echo_hex": "".join(item.hex() for item in echo),
        "response_hex": "".join(item.hex() for item in response),
        "echo_error_class": next((item for item in echo_classes if item != "EXACT_ECHO"), ""),
        "raw_log_path": raw_log_path,
        "raw_sha256": raw_sha256,
    }
    return run_row, protocol_events
