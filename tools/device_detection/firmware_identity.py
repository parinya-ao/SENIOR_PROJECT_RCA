"""Strict firmware identity framing and readback fingerprint comparison."""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

from .evidence import ROLES, FirmwareIdentity

RUNTIME_IDENTITY_MATCH = "RUNTIME_IDENTITY_MATCH"
RUNTIME_IDENTITY_UNVERIFIED = "RUNTIME_IDENTITY_UNVERIFIED"

_V1_MARKER = re.compile(
    rb"^\[(SENDER|RECEIVER)\] ID V1 (sender|sender_hello|receiver) "
    rb"([A-Z][a-z]{2} {1,2}\d{1,2} \d{4}) "
    rb"(\d{2}:\d{2}:\d{2}) CRC=([0-9A-F]{2})\r\n$"
)
_LEGACY_MARKER = re.compile(
    rb"^\[(GATEWAY|RECEIVER)\] BOOT (sender_hello|receiver) "
    rb"([A-Z][a-z]{2} {1,2}\d{1,2} \d{4}) "
    rb"(\d{2}:\d{2}:\d{2})\r\n$"
)
_RECORD_DATA = 0
_RECORD_EOF = 1
_RECORD_SEGMENT_ADDRESS = 2
_RECORD_LINEAR_ADDRESS = 4
_RECORD_START_ADDRESS_TYPES = (3, 5)
_MIN_RECORD_LENGTH = 5
_ADDRESS_RECORD_LENGTH = 2


@dataclass(frozen=True)
class IdentityParseResult:
    """Status and decoded identities from one firmware log stream."""

    status: str
    identity: FirmwareIdentity | None = None
    identities: tuple[FirmwareIdentity, ...] = ()
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class FirmwareReference:
    """Reference image metadata for an application-region comparison."""

    role: str
    build_id: str
    ihex: str
    flash_size: int
    app_start: int
    app_end: int


@dataclass(frozen=True)
class FingerprintResult:
    """Outcome and matching identities from flash fingerprint comparison."""

    status: str
    identity: FirmwareIdentity | None = None
    matches: tuple[FirmwareIdentity, ...] = ()
    details: tuple[str, ...] = ()
    first_mismatch_address: int | None = None
    differing_bytes: int | None = None
    expected_sha256: str | None = None
    readback_sha256: str | None = None


@dataclass(frozen=True)
class FlashComparison:
    """Byte-for-byte comparison of one normalized HEX region and physical readback."""

    status: str
    first_mismatch_address: int | None = None
    differing_bytes: int | None = None
    expected_sha256: str | None = None
    readback_sha256: str | None = None
    details: tuple[str, ...] = ()


def crc8(data: bytes) -> int:
    """Return the CRC-8 checksum used by the V1 identity frame."""
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = ((value << 1) ^ (0x07 if value & 0x80 else 0)) & 0xFF
    return value


def _valid_build(role: str, build: str) -> bool:
    return (role == "SENDER" and build in {"sender", "sender_hello"}) or (
        role == "RECEIVER" and build == "receiver"
    )


def _valid_timestamp(date: bytes, time: bytes) -> bool:
    try:
        normalized_date = " ".join(date.decode("ascii").split())
        datetime.strptime(f"{normalized_date} {time.decode('ascii')}", "%b %d %Y %H:%M:%S")
    except UnicodeDecodeError, ValueError:
        return False
    else:
        return True


def parse_identity_stream(
    data: bytes | str,
) -> IdentityParseResult:
    """Parse complete CRLF records; an invalid candidate invalidates the stream."""
    if isinstance(data, str):
        try:
            raw = data.encode("ascii")
        except UnicodeEncodeError:
            return IdentityParseResult("MALFORMED", details=("non-ASCII identity stream",))
    else:
        raw = data

    found: list[FirmwareIdentity] = []
    malformed: list[str] = []
    for line in raw.splitlines(keepends=True):
        is_v1 = line.startswith((b"[SENDER] ID", b"[RECEIVER] ID"))
        is_legacy = line.startswith((b"[GATEWAY] BOOT", b"[RECEIVER] BOOT"))
        if not (is_v1 or is_legacy):
            continue
        if is_v1:
            match = _V1_MARKER.fullmatch(line)
            if match is None:
                malformed.append("malformed or incomplete V1 identity frame")
                continue
            role_b, build_b, date, time, crc_b = match.groups()
            role, build = role_b.decode(), build_b.decode()
            if not _valid_build(role, build) or not _valid_timestamp(date, time):
                malformed.append("V1 role/build/timestamp mismatch")
                continue
            canonical = b"|".join((role_b, b"V1", build_b, date, time))
            expected = crc8(canonical)
            if expected != int(crc_b, 16):
                malformed.append("V1 identity checksum mismatch")
                continue
            date_text = " ".join(date.decode().split())
            found.append(
                FirmwareIdentity(role, f"{build}@{date_text}T{time.decode()}", 1, expected, "crc8")
            )
        else:
            match = _LEGACY_MARKER.fullmatch(line)
            if match is None:
                malformed.append("malformed or incomplete legacy boot frame")
                continue
            source_role_b, build_b, date, time = match.groups()
            build = build_b.decode()
            role = "SENDER" if source_role_b == b"GATEWAY" else "RECEIVER"
            if not _valid_build(role, build) or not _valid_timestamp(date, time):
                malformed.append("legacy role/build/timestamp mismatch")
                continue
            date_text = " ".join(date.decode().split())
            found.append(
                FirmwareIdentity(
                    role, f"{build}@{date_text}T{time.decode()}", 0, None, "line-framed"
                )
            )

    if malformed:
        return IdentityParseResult("MALFORMED", details=tuple(malformed))
    unique: dict[tuple[str, str], FirmwareIdentity] = {}
    for identity in found:
        key = (identity.role, identity.build_id)
        prior = unique.get(key)
        if prior is None or identity.protocol > prior.protocol:
            unique[key] = identity
    identities = tuple(unique.values())
    if not identities:
        return IdentityParseResult("NONE")
    if len(identities) != 1:
        return IdentityParseResult(
            "AMBIGUOUS", identities=identities, details=("conflicting firmware identities",)
        )
    return IdentityParseResult("VALID", identity=identities[0], identities=identities)


def _parse_ihex(text: str) -> dict[int, int]:
    memory: dict[int, int] = {}
    upper = 0
    eof = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        if eof or not line.startswith(":"):
            msg = f"invalid Intel HEX record at line {line_number}"
            raise ValueError(msg)
        try:
            record = bytes.fromhex(line[1:])
        except ValueError as exc:
            msg = f"invalid Intel HEX bytes at line {line_number}"
            raise ValueError(msg) from exc
        if (
            len(record) < _MIN_RECORD_LENGTH
            or record[0] != len(record) - _MIN_RECORD_LENGTH
            or sum(record) & 0xFF
        ):
            msg = f"invalid Intel HEX length/checksum at line {line_number}"
            raise ValueError(msg)
        length, offset, record_type = record[0], int.from_bytes(record[1:3], "big"), record[3]
        data = record[4 : 4 + length]
        if record_type == _RECORD_DATA:
            start = upper + offset
            for index, byte in enumerate(data):
                address = start + index
                if address in memory and memory[address] != byte:
                    msg = f"conflicting Intel HEX data at address 0x{address:X}"
                    raise ValueError(msg)
                memory[address] = byte
        elif record_type == _RECORD_EOF:
            if length != 0 or offset != 0:
                msg = f"invalid Intel HEX EOF at line {line_number}"
                raise ValueError(msg)
            eof = True
        elif record_type == _RECORD_SEGMENT_ADDRESS:
            if length != _ADDRESS_RECORD_LENGTH:
                msg = f"invalid Intel HEX segment address at line {line_number}"
                raise ValueError(msg)
            upper = int.from_bytes(data, "big") << 4
        elif record_type == _RECORD_LINEAR_ADDRESS:
            if length != _ADDRESS_RECORD_LENGTH:
                msg = f"invalid Intel HEX linear address at line {line_number}"
                raise ValueError(msg)
            upper = int.from_bytes(data, "big") << 16
        elif record_type not in _RECORD_START_ADDRESS_TYPES:
            msg = f"unsupported Intel HEX record type {record_type}"
            raise ValueError(msg)
    if not eof:
        msg = "Intel HEX EOF record is missing"
        raise ValueError(msg)
    return memory


def parse_ihex_image(text: str) -> dict[int, int]:
    """Return validated Intel HEX bytes keyed by absolute Flash address."""
    return _parse_ihex(text)


def normalize_ihex_region(text: str, app_start: int, app_end: int) -> bytes:
    """Expand sparse Intel HEX data over the requested erased-byte-filled region."""
    if app_start < 0 or app_end <= app_start:
        msg = "invalid application flash region"
        raise ValueError(msg)
    memory = _parse_ihex(text)
    normalized = bytearray(b"\xff" * (app_end - app_start))
    for address, byte in memory.items():
        if app_start <= address < app_end:
            normalized[address - app_start] = byte
    return bytes(normalized)


def compare_flash_region(
    actual_flash: bytes | None,
    ihex: str,
    *,
    flash_size: int,
    region_start: int,
    region_end: int,
) -> FlashComparison:
    """Compare exact Flash bytes and report the first physical mismatch address."""
    if actual_flash is None or len(actual_flash) != flash_size:
        return FlashComparison("INCOMPLETE", details=("full Flash readback is unavailable",))
    if not (0 <= region_start < region_end <= flash_size):
        return FlashComparison("INVALID_RANGE", details=("Flash comparison range is invalid",))

    image = parse_ihex_image(ihex)
    outside = sorted(address for address in image if not region_start <= address < region_end)
    if outside:
        return FlashComparison(
            "IMAGE_RANGE_MISMATCH",
            first_mismatch_address=outside[0],
            details=(f"firmware HEX contains data outside [{region_start}, {region_end})",),
        )

    expected = normalize_ihex_region(ihex, region_start, region_end)
    readback = actual_flash[region_start:region_end]
    mismatch_offsets = [
        offset
        for offset, (expected_byte, actual_byte) in enumerate(zip(expected, readback, strict=True))
        if expected_byte != actual_byte
    ]
    return FlashComparison(
        "FLASH_BYTES_MATCH" if not mismatch_offsets else "FLASH_BYTES_MISMATCH",
        first_mismatch_address=(region_start + mismatch_offsets[0]) if mismatch_offsets else None,
        differing_bytes=len(mismatch_offsets),
        expected_sha256=hashlib.sha256(expected).hexdigest(),
        readback_sha256=hashlib.sha256(readback).hexdigest(),
        details=(
            ()
            if not mismatch_offsets
            else (f"{len(mismatch_offsets)} bytes differ in the verified span",)
        ),
    )


def match_flash_fingerprint(
    actual_flash: bytes | None,
    references: list[FirmwareReference] | tuple[FirmwareReference, ...],
    *,
    flash_size: int,
    app_start: int,
    app_end: int,
) -> FingerprintResult:
    """Require a complete flash read and compare only the verified app region."""
    if actual_flash is None:
        return FingerprintResult("UNAVAILABLE", details=("no readback/reference",))
    if len(actual_flash) != flash_size:
        return FingerprintResult("INCOMPLETE", details=("flash read length mismatch",))
    if not (0 <= app_start < app_end <= flash_size):
        return FingerprintResult("INCOMPLETE", details=("application region is invalid",))
    if not references:
        return FingerprintResult("UNAVAILABLE", details=("no fingerprint references",))

    matches: list[FirmwareIdentity] = []
    comparisons: list[FlashComparison] = []
    for reference in references:
        if (reference.flash_size, reference.app_start, reference.app_end) != (
            flash_size,
            app_start,
            app_end,
        ):
            continue
        try:
            region_comparison = compare_flash_region(
                actual_flash,
                reference.ihex,
                flash_size=flash_size,
                region_start=app_start,
                region_end=app_end,
            )
        except ValueError:
            continue
        comparisons.append(region_comparison)
        if region_comparison.status == "FLASH_BYTES_MATCH" and reference.role in ROLES:
            matches.append(
                FirmwareIdentity(reference.role, reference.build_id, 0, None, "flash-fingerprint")
            )
    if not matches:
        single_comparison = comparisons[0] if len(comparisons) == 1 else None
        return FingerprintResult(
            "NO_MATCH",
            details=("no exact application image match",)
            + (single_comparison.details if single_comparison else ()),
            first_mismatch_address=(
                single_comparison.first_mismatch_address if single_comparison else None
            ),
            differing_bytes=(single_comparison.differing_bytes if single_comparison else None),
            expected_sha256=(single_comparison.expected_sha256 if single_comparison else None),
            readback_sha256=(single_comparison.readback_sha256 if single_comparison else None),
        )
    unique = {(identity.role, identity.build_id): identity for identity in matches}
    if len(unique) != 1:
        identities = tuple(unique.values())
        return FingerprintResult(
            "AMBIGUOUS", matches=identities, details=("multiple references match the same image",)
        )
    identity = next(iter(unique.values()))
    return FingerprintResult("MATCH", identity=identity, matches=(identity,))
