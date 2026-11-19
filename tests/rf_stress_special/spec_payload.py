"""Pytest specifications for deterministic LoRa stress payload planning."""

import json
import subprocess
import sys
from pathlib import Path


def _run_smoke_plan(output: Path, seed: int, profile: str = "smoke") -> list[dict[str, object]]:
    """Run the public dry-run interface and load its reproducible case rows."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.rf_stress",
            "--profile",
            profile,
            "--seed",
            str(seed),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    case_file = output / "cases.jsonl"
    assert case_file.is_file(), "dry run must write the generated case plan"
    return [json.loads(line) for line in case_file.read_text(encoding="utf-8").splitlines()]


def test_seed_reproduces_bounded_payloads_and_both_direction_character_coverage(
    tmp_path: Path,
) -> None:
    """Generate identical payload plans for the same seed and cover all letters twice."""
    first = _run_smoke_plan(tmp_path / "first", 12345)
    second = _run_smoke_plan(tmp_path / "second", 12345)

    assert first == second
    for direction in ("gateway_to_tracker", "tracker_to_gateway"):
        character_cases = [
            row
            for row in first
            if row["direction"] == direction and row["scenario"] == "character_coverage"
        ]
        assert {bytes.fromhex(str(row["payload_hex"])) for row in character_cases} == {
            character.encode("ascii")
            for character in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        }
    assert all(len(bytes.fromhex(str(row["payload_hex"]))) <= 32 for row in first)


def test_random_ascii_changes_with_seed_and_boundary_patterns_stay_frame_bounded(
    tmp_path: Path,
) -> None:
    """Cover reproducible random bytes, actual boundary lengths, split data and binary framing."""
    first = _run_smoke_plan(tmp_path / "seed-one", 1)
    second = _run_smoke_plan(tmp_path / "seed-two", 2)
    first_random = [row["payload_hex"] for row in first if row["scenario"] == "random_ascii"]
    second_random = [row["payload_hex"] for row in second if row["scenario"] == "random_ascii"]
    assert first_random != second_random

    for direction in ("gateway_to_tracker", "tracker_to_gateway"):
        lengths = {
            len(bytes.fromhex(str(row["payload_hex"])))
            for row in first
            if row["direction"] == direction and row["scenario"] == "boundary_length"
        }
        assert lengths == {1, 2, 15, 16, 31, 32}
        repeated = [
            row
            for row in first
            if row["direction"] == direction and row["scenario"] == "repeated_maximum"
        ]
        assert [bytes.fromhex(str(row["payload_hex"])) for row in repeated] == [b"Z" * 32]

        alternating = [
            row
            for row in first
            if row["direction"] == direction and row["scenario"] == "alternating_case"
        ]
        alternating.sort(key=lambda row: int(row["part_index"]))
        assert [len(bytes.fromhex(str(row["payload_hex"]))) for row in alternating] == [32, 20]
        combined = b"".join(bytes.fromhex(str(row["payload_hex"])) for row in alternating)
        expected = "".join(chr(65 + index) + chr(97 + index) for index in range(26)).encode("ascii")
        assert combined == expected

    binary_case = [row for row in first if row["scenario"] == "binary_framing"]
    assert len(binary_case) == 1
    assert bytes.fromhex(str(binary_case[0]["payload_hex"])) == b"\x00A\xff"


def test_smoke_fault_cases_are_ten_total_and_cover_each_direction(tmp_path: Path) -> None:
    """Schedule ten NACK and duplicate cases each, split evenly across both directions."""
    cases = _run_smoke_plan(tmp_path / "smoke", 3)

    for scenario in ("controlled_nack", "duplicate_data"):
        rows = [row for row in cases if row["scenario"] == scenario]
        assert len(rows) == 10
        assert {
            direction: sum(row["direction"] == direction for row in rows)
            for direction in ("gateway_to_tracker", "tracker_to_gateway")
        } == {"gateway_to_tracker": 5, "tracker_to_gateway": 5}


def test_full_fifty_two_letter_alphabet_is_split_without_byte_loss(tmp_path: Path) -> None:
    """Split the ordered uppercase/lowercase alphabet at the configured frame boundary."""
    cases = _run_smoke_plan(tmp_path / "alphabet", 5)

    for direction in ("gateway_to_tracker", "tracker_to_gateway"):
        frames = [
            row
            for row in cases
            if row["direction"] == direction and row["scenario"] == "full_alphabet"
        ]
        frames.sort(key=lambda row: int(row["part_index"]))
        assert [len(bytes.fromhex(str(row["payload_hex"]))) for row in frames] == [32, 20]
        assert b"".join(bytes.fromhex(str(row["payload_hex"])) for row in frames) == (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz".encode("ascii")
        )


def test_stress_plan_contains_sequence_255_to_zero_rollover_case(tmp_path: Path) -> None:
    """Make sequence rollover explicit in the planned session and expected payloads."""
    cases = _run_smoke_plan(tmp_path / "stress", 6, profile="stress")
    rollover = [row for row in cases if row["fault"] == "SEQUENCE_ROLLOVER"]

    assert sum(row["scenario"] == "random_ascii" for row in cases) == 200
    assert sum(row["scenario"] == "controlled_nack" for row in cases) == 100
    assert sum(row["scenario"] == "duplicate_data" for row in cases) == 100
    assert len(rollover) == 1
    assert rollover[0].get("expected_sequences") == [255, 0]
    payloads = rollover[0].get("payloads_hex", [])
    assert [bytes.fromhex(str(value)) for value in payloads] == [b"R", b"0"]
