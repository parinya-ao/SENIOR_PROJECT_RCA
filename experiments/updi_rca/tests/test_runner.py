import json

import pytest

from updi_rca.probes import ProbeResult
from updi_rca.runner import run_campaign


def test_campaign_persists_each_attempt_and_keeps_failure_stages_separate(tmp_path):
    seen = []

    def probe(path):
        attempt = len(seen) + 1
        seen.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"attempt": attempt}), encoding="utf-8")
        return ProbeResult(
            success=attempt != 2,
            stage="PASS" if attempt != 2 else "LOCAL_ECHO",
            tx=b"\x55\x85",
            echo=b"" if attempt == 2 else b"\x55\x85",
            response=b"",
            latency_ms=1.25 * attempt,
            error_type=None if attempt != 2 else "echo empty",
            raw_path=str(path),
            raw_sha256=f"hash-{attempt}",
        )

    rows = run_campaign(probe, 3, tmp_path / "raw", "RUN-A")

    assert [row["attempt"] for row in rows] == [1, 2, 3]
    assert [row["failure_stage"] for row in rows] == ["", "LOCAL_ECHO", ""]
    assert [row["echo_hex"] for row in rows] == ["5585", "", "5585"]
    assert [row["response_hex"] for row in rows] == ["", "", ""]
    assert len(set(seen)) == 3
    assert all(path.exists() for path in seen)


def test_campaign_rejects_zero_attempts(tmp_path):
    with pytest.raises(ValueError, match="at least one"):
        run_campaign(lambda _: None, 0, tmp_path, "RUN-A")
