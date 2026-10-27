import importlib
import importlib.util


def rows(record, **metadata):
    assert importlib.util.find_spec("updi_rca.continuation") is not None, "missing continuation module"
    continuation = importlib.import_module("updi_rca.continuation")
    converter = getattr(continuation, "attempt_rows", None)
    assert callable(converter), "missing continuation attempt-row converter"
    return converter(record, **metadata)


def test_run_event_rows_preserve_local_echo_failure_and_pairing_identity():
    run, events = rows(
        {
            "utc": "2026-10-26T21:18:32Z",
            "baud": 38400,
            "mode": "sib",
            "events": [
                {"kind": "tx", "ns": 10, "end_ns": 11, "hex": "5585", "count": 2},
                {"kind": "echo", "ns": 12, "end_ns": 13, "hex": "80", "requested": 2},
            ],
            "exit": 1,
            "failure_stage": "LOCAL_ECHO",
            "latency_ms": 5.0,
        },
        epoch_id="RCA_CROSSOVER_01",
        run_id="pre-lane-b-sib",
        lane="lane_b",
        attempt=1,
        adapter_id_path="path-q",
        current_tty="/dev/ttyUSB7",
        adapter_fingerprint="10c4:ea60|0001|path-q",
        target_fingerprint="UNKNOWN_TARGET",
        pairing_state="Q+Y",
        raw_log_path="raw.json",
        raw_sha256="abc",
    )

    assert run["failure_stage"] == "LOCAL_ECHO"
    assert run["current_tty"] == "/dev/ttyUSB7"
    assert run["target_fingerprint"] == "UNKNOWN_TARGET"
    assert run["pairing_state"] == "Q+Y"
    assert run["echo_error_class"] == "ECHO_SHORT"
    assert [event["stage"] for event in events] == ["HOST_TX", "LOCAL_ECHO"]
    assert len({event["event_id"] for event in events}) == len(events)


def test_acc_timeout_after_exact_echo_stays_later_than_local_echo():
    run, events = rows(
        {
            "utc": "2026-10-26T21:18:32Z",
            "baud": 38400,
            "mode": "read",
            "address": 30,
            "events": [
                {"kind": "tx", "ns": 20, "end_ns": 21, "hex": "55001e", "count": 3},
                {"kind": "echo", "ns": 22, "end_ns": 23, "hex": "55001e", "requested": 3},
                {"kind": "response", "ns": 24, "end_ns": 25, "hex": "", "requested": 1,
                 "stage": "ACC_DATA_RESPONSE"},
            ],
            "exit": 1,
            "failure_stage": "ACC_DATA_RESPONSE",
            "latency_ms": 1.0,
        },
        epoch_id="RCA_CROSSOVER_01",
        run_id="historical-acc-class",
        lane="lane_a",
        attempt=2,
        adapter_id_path="path-p",
        current_tty="/dev/ttyUSB2",
        adapter_fingerprint="10c4:ea60|0001|path-p",
        target_fingerprint="UNKNOWN_TARGET",
        pairing_state="P+X",
        raw_log_path="raw.json",
        raw_sha256="def",
    )

    assert run["failure_stage"] == "ACC_DATA_RESPONSE"
    assert events[1]["classification"] == "EXACT_ECHO"
    assert events[2]["stage"] == "ACC_DATA_RESPONSE"
