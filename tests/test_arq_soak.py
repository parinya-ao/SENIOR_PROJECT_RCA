import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools import arq_trial
from tools.config.arq_config import load_arq
from typing import Never


def confirmed_rf_preflight():
    return SimpleNamespace(
        physical_mapping_verified=True,
        power_verified=True,
        rf_hardware_verified=True,
        rf_path_confirmed=True,
        authorize_rf_test=True,
    )


def write_soak_progress(run_dir, plan, *, span_ns=1_000_000_000) -> None:
    progress = run_dir / "soak/soak-progress.jsonl"
    progress.parent.mkdir(parents=True)
    rows = []
    for index in range(plan["sessions"]):
        started = 100 + span_ns * index // max(1, plan["sessions"] - 1)
        rows.extend(
            (
                dict(event="SESSION_START", index=index + 1, monotonic_ns=started),
                dict(event="SESSION_COMPLETE", index=index + 1, monotonic_ns=started + 1),
            )
        )
    rows.append(dict(event="RESTORE_VERIFIED"))
    progress.write_text("".join(json.dumps(row) + "\n" for row in rows))


class ArqSoakPlanTests(unittest.TestCase):
    def test_sf7_airtime_uses_max_wire_frame_and_response_lengths(self) -> None:
        estimate = getattr(arq_trial, "lora_time_on_air_us", None)
        self.assertTrue(callable(estimate), "Semtech airtime calculation is required")
        config = load_arq()
        self.assertEqual(estimate(44, config), 92416)
        self.assertEqual(estimate(12, config), 41216)

    def test_stage_plan_is_paced_for_worst_case_retries(self) -> None:
        build_plan = getattr(arq_trial, "build_soak_plan", None)
        self.assertTrue(callable(build_plan), "bounded soak plan is required")
        plan = build_plan("1-hour", load_arq())
        self.assertEqual(plan["sessions"], 61)
        self.assertEqual(plan["session_interval_s"], 60)
        self.assertEqual(plan["max_attempts"], 5)
        self.assertEqual(plan["gateway_worst_case_session_airtime_us"], 462080)
        self.assertEqual(plan["tracker_worst_case_session_airtime_us"], 206080)
        self.assertLessEqual(plan["gateway_duty_percent_at_interval"], 1.0)
        self.assertLessEqual(plan["tracker_duty_percent_at_interval"], 1.0)

    def test_soak_plan_rejects_unknown_stage(self) -> None:
        build_plan = getattr(arq_trial, "build_soak_plan", None)
        self.assertTrue(callable(build_plan), "bounded soak plan is required")
        with self.assertRaises(ValueError):
            build_plan("unbounded", load_arq())

    def test_soak_stages_cannot_skip_failed_or_unrun_predecessors(self) -> None:
        prerequisites = getattr(arq_trial, "missing_soak_prerequisites", None)
        self.assertTrue(callable(prerequisites), "soak stage progression gate is required")
        completed = {"1-session": "PASS", "10-sessions": "PASS"}
        self.assertEqual(prerequisites("100-sessions", completed), [])
        self.assertEqual(prerequisites("1-hour", completed), ["100-sessions", "1000-sessions"])
        self.assertEqual(
            prerequisites("24-hours", {}),
            ["1-session", "10-sessions", "100-sessions", "1000-sessions", "1-hour", "8-hours"],
        )

    def test_soak_campaign_blocks_a_later_stage_without_prior_pass_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "artifacts/arq").mkdir(parents=True)
            with (
                patch.object(arq_trial, "ROOT", root),
                patch.object(arq_trial, "campaign") as campaign,
            ):
                with self.assertRaisesRegex(ValueError, "1-session"):
                    arq_trial.soak_campaign("100-sessions", confirmed_rf_preflight())
            campaign.assert_not_called()

    def test_soak_summary_reports_success_ci_retries_and_sample_limits(self) -> None:
        summarize = getattr(arq_trial, "summarize_soak_results", None)
        self.assertTrue(callable(summarize), "soak reliability summary is required")
        rows = [
            dict(
                complete=True,
                delivered=1,
                first_attempt=1,
                attempts=1,
                retries=0,
                session_duration_s=2.0,
                rtt=dict(count=1, average=55),
            )
            for _ in range(10)
        ]
        summary = summarize(rows, 10)
        self.assertEqual(summary["successes"], 10)
        self.assertEqual(summary["failures"], 0)
        self.assertEqual(summary["retransmissions"], 0)
        self.assertEqual(summary["first_attempt_successes"], 10)
        self.assertAlmostEqual(summary["success_rate"], 1.0)
        self.assertAlmostEqual(summary["success_rate_95_ci"]["lower"], 0.722, places=3)
        self.assertIsNone(summary["ack_rtt_ms"]["p95"])
        self.assertIsNone(summary["ack_rtt_ms"]["p99"])
        self.assertEqual(summary["ack_rtt_ms"]["mean"], 55)
        self.assertEqual(summary["ack_rtt_ms"]["p90"], None)

    def test_soak_metrics_derive_attempts_and_timeouts_from_validated_events(self) -> None:
        derive = getattr(arq_trial, "soak_result_metrics", None)
        self.assertTrue(callable(derive), "soak metrics must be bound to the raw transaction")
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "bundle.json"
            bundle.write_text(
                json.dumps(
                    {
                        "events": [
                            {"role": "sender", "e": "RX_TIMEOUT"},
                            {"role": "sender", "e": "TX", "bytes": "010101020100000000000000"},
                            {"role": "sender", "e": "TX", "bytes": "010101020100000000000000"},
                            {"role": "sender", "e": "DELIVERED", "q": "0", "v": "2"},
                        ]
                    }
                )
            )
            result = derive(dict(complete=True, delivered=1), bundle, 3.5)
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["retries"], 1)
        self.assertEqual(result["ack_timeouts"], 1)
        self.assertEqual(result["unexpected_resets"], 0)
        self.assertEqual(result["session_duration_s"], 3.5)

    def test_soak_campaign_persists_pass_receipt_for_next_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts/arq"
            artifacts.mkdir(parents=True)
            ledger = artifacts / "soak-ledger.json"
            ledger.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "stages": {"1-session": {"status": "PASS", "sessions_completed": 1}},
                    }
                )
            )

            def fake_campaign(*, soak_plan, run_dir):
                run_dir.mkdir(parents=True)
                rows = [
                    dict(
                        complete=True,
                        delivered=1,
                        first_attempt=1,
                        attempts=1,
                        retries=0,
                        session_duration_s=2.0,
                        rtt=dict(count=1, average=55),
                    )
                    for _ in range(soak_plan["sessions"])
                ]
                (run_dir / "campaign.json").write_text(json.dumps(rows))
                write_soak_progress(run_dir, soak_plan)
                return run_dir

            with (
                patch.object(arq_trial, "ROOT", root),
                patch.object(arq_trial, "campaign", side_effect=fake_campaign),
            ):
                run = arq_trial.soak_campaign("10-sessions", confirmed_rf_preflight())
            record = json.loads(ledger.read_text())["stages"]["10-sessions"]
            self.assertEqual(record["status"], "PASS")
            self.assertEqual(record["summary"]["successes"], 10)
            self.assertEqual(record["run_directory"], str(run))

    def test_soak_campaign_does_not_pass_when_any_session_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts/arq"
            artifacts.mkdir(parents=True)
            (artifacts / "soak-ledger.json").write_text(
                json.dumps({"schema_version": 1, "stages": {"1-session": {"status": "PASS"}}})
            )

            def fake_campaign(*, soak_plan, run_dir):
                run_dir.mkdir(parents=True)
                rows = [
                    dict(
                        complete=True,
                        delivered=1,
                        first_attempt=1,
                        attempts=1,
                        session_duration_s=2.0,
                        rtt=dict(count=1, average=55),
                    )
                    for _ in range(soak_plan["sessions"])
                ]
                rows[-1]["delivered"] = 0
                (run_dir / "campaign.json").write_text(json.dumps(rows))
                write_soak_progress(run_dir, soak_plan)
                return run_dir

            with (
                patch.object(arq_trial, "ROOT", root),
                patch.object(arq_trial, "campaign", side_effect=fake_campaign),
            ):
                with self.assertRaisesRegex(ValueError, "acceptance criteria"):
                    arq_trial.soak_campaign("10-sessions", confirmed_rf_preflight())
            record = json.loads((artifacts / "soak-ledger.json").read_text())["stages"][
                "10-sessions"
            ]
            self.assertEqual(record["status"], "FAILED")
            self.assertEqual(record["summary"]["failures"], 1)
            self.assertIn("acceptance criteria", record["failure"])

    def test_duration_stage_requires_recorded_monotonic_span(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts/arq"
            artifacts.mkdir(parents=True)
            (artifacts / "soak-ledger.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "stages": {
                            name: {"status": "PASS"} for name in arq_trial.SOAK_SESSION_STAGES
                        },
                    }
                )
            )

            def fake_campaign(*, soak_plan, run_dir):
                run_dir.mkdir(parents=True)
                rows = [
                    dict(
                        complete=True,
                        delivered=1,
                        first_attempt=1,
                        attempts=1,
                        session_duration_s=2.0,
                        rtt=dict(count=1, average=55),
                    )
                    for _ in range(soak_plan["sessions"])
                ]
                (run_dir / "campaign.json").write_text(json.dumps(rows))
                write_soak_progress(run_dir, soak_plan, span_ns=200)
                return run_dir

            with (
                patch.object(arq_trial, "ROOT", root),
                patch.object(arq_trial, "campaign", side_effect=fake_campaign),
            ):
                with self.assertRaisesRegex(ValueError, "acceptance criteria"):
                    arq_trial.soak_campaign("1-hour", confirmed_rf_preflight())
            record = json.loads((artifacts / "soak-ledger.json").read_text())["stages"]["1-hour"]
            self.assertEqual(record["status"], "FAILED")

    def test_interrupted_soak_keeps_partial_progress_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts/arq"
            artifacts.mkdir(parents=True)

            def interrupted_campaign(*, soak_plan, run_dir) -> Never:
                run_dir.mkdir(parents=True)
                (run_dir / "campaign.json").write_text("[]\n")
                progress = run_dir / "soak/soak-progress.jsonl"
                progress.parent.mkdir()
                progress.write_text(
                    json.dumps(dict(event="SESSION_START", index=1, monotonic_ns=100)) + "\n"
                )
                raise KeyboardInterrupt

            with (
                patch.object(arq_trial, "ROOT", root),
                patch.object(arq_trial, "campaign", side_effect=interrupted_campaign),
            ):
                with self.assertRaises(KeyboardInterrupt):
                    arq_trial.soak_campaign("1-session", confirmed_rf_preflight())
            record = json.loads((artifacts / "soak-ledger.json").read_text())["stages"]["1-session"]
            self.assertEqual(record["status"], "INTERRUPTED")
            self.assertEqual(record["completed_sessions"], 0)
            self.assertEqual(record["summary"]["sessions_attempted"], 0)

    def test_rerun_keeps_the_previous_interrupted_stage_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts/arq"
            artifacts.mkdir(parents=True)
            ledger = artifacts / "soak-ledger.json"
            ledger.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "stages": {
                            "1-session": {
                                "status": "INTERRUPTED",
                                "run_directory": "old-run",
                                "completed_sessions": 0,
                            }
                        },
                    }
                )
            )

            def fake_campaign(*, soak_plan, run_dir):
                run_dir.mkdir(parents=True)
                row = dict(
                    complete=True,
                    delivered=1,
                    first_attempt=1,
                    attempts=1,
                    retries=0,
                    session_duration_s=2.0,
                    rtt=dict(count=1, average=55),
                )
                (run_dir / "campaign.json").write_text(json.dumps([row]))
                write_soak_progress(run_dir, soak_plan)
                return run_dir

            with (
                patch.object(arq_trial, "ROOT", root),
                patch.object(arq_trial, "campaign", side_effect=fake_campaign),
            ):
                arq_trial.soak_campaign("1-session", confirmed_rf_preflight())
            record = json.loads(ledger.read_text())["stages"]["1-session"]
            self.assertEqual(record["status"], "PASS")
            self.assertEqual(record["history"][0]["status"], "INTERRUPTED")
            self.assertEqual(record["history"][0]["run_directory"], "old-run")

    def test_soak_rerun_refuses_to_replace_a_live_stage_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts/arq"
            artifacts.mkdir(parents=True)
            (artifacts / "soak-ledger.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "stages": {
                            "1-session": {
                                "status": "RUNNING",
                                "run_directory": "active-run",
                                "process_id": 12345,
                            }
                        },
                    }
                )
            )
            with (
                patch.object(arq_trial, "ROOT", root),
                patch.object(arq_trial.os, "kill") as process_alive,
                patch.object(arq_trial, "campaign") as campaign,
            ):
                with self.assertRaisesRegex(ValueError, "still active"):
                    arq_trial.soak_campaign("1-session", confirmed_rf_preflight())
            process_alive.assert_called_once_with(12345, 0)
            campaign.assert_not_called()

    def test_soak_rerun_marks_a_dead_stage_process_interrupted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts/arq"
            artifacts.mkdir(parents=True)
            ledger = artifacts / "soak-ledger.json"
            ledger.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "stages": {
                            "1-session": {
                                "status": "RUNNING",
                                "run_directory": "stale-run",
                                "process_id": 12345,
                            }
                        },
                    }
                )
            )

            def fake_campaign(*, soak_plan, run_dir):
                run_dir.mkdir(parents=True)
                row = dict(
                    complete=True,
                    delivered=1,
                    first_attempt=1,
                    attempts=1,
                    retries=0,
                    session_duration_s=2.0,
                    rtt=dict(count=1, average=55),
                )
                (run_dir / "campaign.json").write_text(json.dumps([row]))
                write_soak_progress(run_dir, soak_plan)
                return run_dir

            with (
                patch.object(arq_trial, "ROOT", root),
                patch.object(arq_trial.os, "kill", side_effect=ProcessLookupError),
                patch.object(arq_trial, "campaign", side_effect=fake_campaign),
            ):
                arq_trial.soak_campaign("1-session", confirmed_rf_preflight())
            record = json.loads(ledger.read_text())["stages"]["1-session"]
            self.assertEqual(record["status"], "PASS")
            self.assertEqual(record["history"][0]["status"], "INTERRUPTED")
            self.assertIn("termination reason unknown", record["history"][0]["failure"])

    def test_soak_plan_reports_firmware_retry_spacing_duty(self) -> None:
        plan = arq_trial.build_soak_plan("10-sessions", load_arq())
        self.assertEqual(plan.get("firmware_tx_spacing_ms"), 10000)
        self.assertAlmostEqual(plan.get("firmware_frame_duty_percent"), 0.92416, places=5)

    def test_soak_cli_fails_closed_without_power_and_rf_readiness(self) -> None:
        stderr = StringIO()
        argv = ["arq_trial.py", "--soak-stage", "10-sessions", "--rf-path-confirmed"]
        with patch.object(sys, "argv", argv), patch.object(arq_trial, "soak_campaign") as campaign:
            with redirect_stderr(stderr), self.assertRaises(SystemExit) as exit_info:
                arq_trial.main()
        self.assertEqual(exit_info.exception.code, 2)
        self.assertIn("safe power", stderr.getvalue())
        campaign.assert_not_called()

    def test_soak_cli_dispatches_the_verified_stage_plan(self) -> None:
        argv = [
            "arq_trial.py",
            "--soak-stage",
            "10-sessions",
            "--rf-path-confirmed",
            "--physical-mapping-verified",
            "--power-verified",
            "--rf-hardware-verified",
            "--authorize-rf-test",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(arq_trial, "soak_campaign", return_value="soak-run") as campaign,
            redirect_stdout(StringIO()),
        ):
            arq_trial.main()
        self.assertEqual(campaign.call_args.args[0], "10-sessions")
        self.assertTrue(campaign.call_args.args[1].power_verified)

    def test_paced_sessions_enforce_start_spacing_and_stop_on_failure(self) -> None:
        run_paced = getattr(arq_trial, "run_paced_sessions", None)
        self.assertTrue(callable(run_paced), "paced soak executor is required")

        class Clock:
            now = 0.0

            def monotonic(self):
                return self.now

            def sleep(self, seconds) -> None:
                self.now += seconds

        clock = Clock()
        starts = []

        def run_one(index):
            starts.append(clock.now)
            clock.now += 5.0
            return index

        results = run_paced(3, 60, run_one, clock=clock.monotonic, sleep=clock.sleep)
        self.assertEqual(results, [0, 1, 2])
        self.assertEqual(starts, [0.0, 60.0, 120.0])

        clock.now = 0.0
        calls = []

        def fail_on_second(index) -> None:
            calls.append(index)
            if index == 1:
                raise RuntimeError("session failed")

        with self.assertRaisesRegex(RuntimeError, "session failed"):
            run_paced(3, 60, fail_on_second, clock=clock.monotonic, sleep=clock.sleep)
        self.assertEqual(calls, [0, 1])


if __name__ == "__main__":
    unittest.main()
