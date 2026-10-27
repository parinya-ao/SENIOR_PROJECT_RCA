"""CSV output with fixed, validated schemas for investigation evidence."""

import csv
from pathlib import Path


DEVICE_INVENTORY_COLUMNS = tuple("timestamp run_id lane board_id current_tty by_id by_path id_path sysfs_path usb_bus usb_device vid pid adapter_serial sib device_signature revid target_serial firmware_sha256 fuse_sha256 status notes".split())
RUN_COLUMNS = tuple("timestamp run_id test_id lane board_id adapter_id current_tty baud cpu_state firmware_sha256 attempt result latency_ms failure_stage error_type expected_hex observed_hex rstfr_raw ocd_status_raw sys_status_raw kernel_usb_error source_log raw_sha256".split())
EVENT_COLUMNS = tuple("timestamp_monotonic run_id event_id lane board_id stage direction operation address tx_hex echo_hex response_hex expected_len actual_len status_raw errno classification raw_log_path".split())
HYPOTHESIS_COLUMNS = tuple("hypothesis_id domain cause status evidence_score confidence_label predictions discriminator evidence_for evidence_against next_test requires_flash requires_physical_measurement last_updated".split())
PAIRWISE_COLUMNS = tuple("test_id metric board_a_value board_b_value absolute_delta relative_delta interpretation n_a n_b".split())
FUSE_COLUMNS = tuple("field side_a side_b value_a value_b comparison_status source_run_a source_run_b notes".split())
FLASH_COLUMNS = tuple("timestamp board_id write_number reason image_sha256 verify_result fuses_changed userrow_changed eeprom_changed approved_by_rule notes".split())
RANKING_COLUMNS = tuple("rank hypothesis_id domain cause status evidence_score decisive_evidence contrary_evidence remaining_uncertainty next_required_measurement".split())
HYPOTHESIS_SEED_COLUMNS = tuple("hypothesis_id domain text observable_prediction cheapest_discriminator requires_instrument requires_flash risk evidence_score current_status".split())


def _check_header(path: Path, columns: tuple[str, ...]) -> None:
    if path.exists() and path.stat().st_size:
        with path.open(newline="", encoding="utf-8") as stream:
            header = next(csv.reader(stream), [])
        if tuple(header) != columns:
            raise ValueError(f"CSV header mismatch in {path}")


def append_csv(path: str | Path, columns: tuple[str, ...], row: dict) -> None:
    path = Path(path)
    extra = set(row) - set(columns)
    if extra:
        raise ValueError(f"unexpected CSV fields: {', '.join(sorted(extra))}")
    _check_header(path, columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise", lineterminator="\n")
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def append_run_csv(path: str | Path, row: dict) -> None:
    append_csv(path, RUN_COLUMNS, row)


def write_csv(path: str | Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    path = Path(path)
    for row in rows:
        extra = set(row) - set(columns)
        if extra:
            raise ValueError(f"unexpected CSV fields: {', '.join(sorted(extra))}")
    _check_header(path, columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render_summary(metrics: dict, title: str = "Run Summary") -> str:
    lower, upper = metrics["wilson_95"]
    return "\n".join([
        f"## {title}",
        "",
        f"- N = {metrics['attempts']}",
        f"- Pass/fail = {metrics['successes']}/{metrics['failures']}",
        f"- Success/failure rate = {metrics['success_rate']:.1%}/{metrics['failure_rate']:.1%}",
        f"- Wilson 95% success interval = [{lower:.1%}, {upper:.1%}]",
        f"- Median/p95 latency = {metrics['median_latency_ms']} / {metrics['p95_latency_ms']} ms",
    ])
