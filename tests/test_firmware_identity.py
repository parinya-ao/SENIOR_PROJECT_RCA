"""Tests for shared Intel HEX and physical Flash comparison evidence."""

from __future__ import annotations

from tools.device_detection.firmware_identity import compare_flash_region


def _record(address: int, record_type: int, data: bytes) -> str:
    """Encode one checksummed Intel HEX record for a small fixture."""
    row = bytes((len(data), address >> 8, address & 0xFF, record_type)) + data
    checksum = (-sum(row)) & 0xFF
    return f":{(row + bytes((checksum,))).hex().upper()}"


def _hex_image(address: int, data: bytes) -> str:
    """Create a single-segment fixture with a valid end-of-file record."""
    return "\n".join((_record(address, 0, data), _record(0, 1, b""))) + "\n"


def test_flash_comparison_reports_exact_sparse_image_match() -> None:
    """Normalize sparse HEX fill bytes and compare identical physical bytes."""
    actual = bytes((0xFF, 0xFF, 0x12, 0x34, 0xFF, 0xFF))

    result = compare_flash_region(
        actual,
        _hex_image(2, b"\x12\x34"),
        flash_size=len(actual),
        region_start=0,
        region_end=len(actual),
    )

    assert result.status == "FLASH_BYTES_MATCH"
    assert result.first_mismatch_address is None
    assert result.differing_bytes == 0
    assert result.expected_sha256 == result.readback_sha256


def test_flash_comparison_reports_first_actual_mismatch_address() -> None:
    """Separate decoded Flash byte mismatches from HEX-file hash differences."""
    actual = bytes((0xFF, 0xFF, 0x12, 0x35, 0xFF, 0xFF))

    result = compare_flash_region(
        actual,
        _hex_image(2, b"\x12\x34"),
        flash_size=len(actual),
        region_start=0,
        region_end=len(actual),
    )

    assert result.status == "FLASH_BYTES_MISMATCH"
    assert result.first_mismatch_address == 3
    assert result.differing_bytes == 1
    assert result.expected_sha256 != result.readback_sha256


def test_flash_comparison_rejects_hex_data_outside_the_authorized_region() -> None:
    """Do not silently discard records outside the selected Flash region."""
    actual = bytes(8)

    result = compare_flash_region(
        actual,
        _hex_image(6, b"\x01\x02"),
        flash_size=len(actual),
        region_start=0,
        region_end=7,
    )

    assert result.status == "IMAGE_RANGE_MISMATCH"
    assert result.first_mismatch_address == 7
