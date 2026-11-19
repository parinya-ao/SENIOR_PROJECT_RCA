"""Pytest specifications for the explicitly invoked LoRa RF stress runner."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.rf_stress.runner import CONFIG_PATH, load_config


def test_default_cli_writes_a_zero_transmission_dry_run(tmp_path: Path) -> None:
    """Keep the default CLI safe and make its generated case plan inspectable."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.rf_stress",
            "--profile",
            "smoke",
            "--seed",
            "12345",
            "--output",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert "MODE=DRY_RUN" in completed.stdout
    assert "RF_TRANSMISSIONS=0" in completed.stdout
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 12345
    assert manifest["rf_transmissions"] == 0


def test_real_rf_requires_explicit_profile_and_saved_readback(tmp_path: Path) -> None:
    """Reject real mode before hardware access unless profile and image evidence are supplied."""
    completed = subprocess.run(
        [sys.executable, "-m", "tools.rf_stress", "--real-rf", "--output", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode != 0
    assert "--readback" in completed.stderr
    assert not (tmp_path / "manifest.json").exists()


def test_torture_profile_requires_long_duration_opt_in(tmp_path: Path) -> None:
    """Keep the 1000-case profile behind its explicit long-duration switch."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.rf_stress",
            "--profile",
            "torture",
            "--output",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode != 0
    assert "--long-duration is required" in completed.stderr
    assert not (tmp_path / "manifest.json").exists()


def test_torture_plan_has_at_least_one_thousand_cases_and_a_bounded_runtime(
    tmp_path: Path,
) -> None:
    """Plan the 1000-case profile with the existing airtime interval and a finite cap."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.rf_stress",
            "--profile",
            "torture",
            "--seed",
            "9876",
            "--long-duration",
            "--max-minutes",
            "1800",
            "--output",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["planned_transactions"] >= 1000
    assert manifest["radio"]["frequency_hz"] == 915000000
    assert manifest["radio_airtime_plan"]["session_interval_s"] == 60
    assert manifest["worst_case_runtime_seconds"] <= 1800 * 60
    assert manifest["rf_transmissions"] == 0


def test_stress_config_rejects_unknown_settings(tmp_path: Path) -> None:
    """Reject unreviewed runtime policy keys instead of silently ignoring them."""
    config_path = tmp_path / "rf_stress.toml"
    original = CONFIG_PATH.read_text(encoding="utf-8")
    config_path.write_text(
        original.replace("schema_version = 1", "schema_version = 1\nunknown_setting = 1", 1)
    )

    with pytest.raises(ValueError, match="unsupported RF stress configuration"):
        load_config(config_path)


def test_torture_config_must_keep_one_thousand_transaction_minimum(tmp_path: Path) -> None:
    """Fail config loading when configured torture counts drop below the required minimum."""
    original = CONFIG_PATH.read_text(encoding="utf-8")
    changed = original.replace(
        "random_cases_per_direction = 400", "random_cases_per_direction = 399"
    )
    config_path = tmp_path / "rf_stress.toml"
    config_path.write_text(changed)

    with pytest.raises(ValueError, match="at least 1000 transactions"):
        load_config(config_path)
