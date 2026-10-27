import json
from pathlib import Path

from updi_rca.events import parse_upditerm_log
from updi_rca.classify import classify_event, is_fresh_reset, score_evidence


FIXTURE = Path(__file__).parent / "fixtures/synthetic/updi-events.jsonl"


def events():
    return [json.loads(line) for line in FIXTURE.read_text().splitlines()]


def test_json_event_line_is_preserved():
    raw = '{"operation":"LDS","tx_hex":"55001d","echo_hex":"55001d"}'
    assert parse_upditerm_log(raw) == json.loads(raw)


def test_text_log_line_is_kept_as_raw_evidence():
    event = parse_upditerm_log("UPDI link initialization failed")
    assert event["message"] == "UPDI link initialization failed"
    assert event["raw"] == "UPDI link initialization failed"


def test_local_echo_failures_are_not_target_response_failures():
    for event in events():
        if event["name"] in {"corrupted local echo", "truncated local echo", "empty local echo"}:
            assert classify_event(event) == "LOCAL_ECHO"


def test_exact_echo_missing_response_is_classified_by_target_stage():
    found = {event["name"]: classify_event(event) for event in events()}
    assert found["missing LDCS response"] == "UPDI_CONTROL_RESPONSE"
    assert found["missing STS ACK"] == "ACC_ACK"


def test_usb_errors_and_target_message_have_distinct_stages():
    found = {event["name"]: classify_event(event) for event in events()}
    assert found["initialization failure"] == "UPDI_PHY_CONTROL"
    assert found["missing tty"] == "PORT_DISCOVERY"
    assert found["serial open failure"] == "SERIAL_OPEN"
    assert found["short host write"] == "HOST_TX"
    assert found["USB protocol error"] == "USB_HOST"
    assert found["USB bit-stuff error"] == "USB_HOST"
    assert found["USB disconnect"] == "USB_HOST"
    assert found["repeated target message"] == "OCD_MESSAGE"
    assert found["OCD status missing"] == "OCD_STATUS"
    assert found["flash verify failure"] == "FLASH_VERIFY"
    assert found["flash programming failure"] == "FLASH_PROGRAM"
    assert found["new target reset"] == "TARGET_RESET"
    assert found["target runtime failure"] == "TARGET_RUNTIME"
    assert found["clean echo and response"] == "PASS"


def test_borf_alone_does_not_count_as_a_new_reset():
    assert not is_fresh_reset({"rstfr_raw": "02", "boot_id_before": 5, "boot_id_after": 5})
    assert is_fresh_reset({"rstfr_raw": "02", "boot_id_before": 5, "boot_id_after": 6})


def test_state_and_usb_evidence_use_explicit_weights():
    assert score_evidence("A", {"control_stable_running_data_failure": True}) == 7
    assert score_evidence("G", {"control_stable_running_data_failure": True}) == -5
    assert score_evidence("A", {"stopped_pass_running_failure": True}) == 8
    assert score_evidence("G", {"usb_error_correlated": True}) == 7
    assert score_evidence("G", {"clean_usb_exact_echo_target_timeout": True}) == -5
