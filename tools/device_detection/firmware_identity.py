"""Strict firmware identity framing and readback fingerprint comparison."""

import re
from dataclasses import dataclass
from datetime import datetime

from .evidence import ROLES, FirmwareIdentity

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


@dataclass(frozen=True)
class IdentityParseResult:
    status: str
    identity: FirmwareIdentity | None = None
    identities: tuple[FirmwareIdentity, ...] = ()
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class FirmwareReference:
    role: str
    build_id: str
    ihex: str
    flash_size: int
    app_start: int
    app_end: int


@dataclass(frozen=True)
class FingerprintResult:
    status: str
    identity: FirmwareIdentity | None = None
    matches: tuple[FirmwareIdentity, ...] = ()
    details: tuple[str, ...] = ()


def crc8(data: bytes) -> int:
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
        return True
    except (UnicodeDecodeError, ValueError):
        return False


def parse_identity_stream(data: bytes | str) -> IdentityParseResult:
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
            raise ValueError(f"invalid Intel HEX record at line {line_number}")
        try:
            record = bytes.fromhex(line[1:])
        except ValueError as exc:
            raise ValueError(f"invalid Intel HEX bytes at line {line_number}") from exc
        if len(record) < 5 or record[0] != len(record) - 5 or sum(record) & 0xFF:
            raise ValueError(f"invalid Intel HEX length/checksum at line {line_number}")
        length, offset, record_type = record[0], int.from_bytes(record[1:3], "big"), record[3]
        data = record[4 : 4 + length]
        if record_type == 0:
            start = upper + offset
            for index, byte in enumerate(data):
                address = start + index
                if address in memory and memory[address] != byte:
                    raise ValueError(f"conflicting Intel HEX data at address 0x{address:X}")
                memory[address] = byte
        elif record_type == 1:
            if length != 0 or offset != 0:
                raise ValueError(f"invalid Intel HEX EOF at line {line_number}")
            eof = True
        elif record_type == 2:
            if length != 2:
                raise ValueError(f"invalid Intel HEX segment address at line {line_number}")
            upper = int.from_bytes(data, "big") << 4
        elif record_type == 4:
            if length != 2:
                raise ValueError(f"invalid Intel HEX linear address at line {line_number}")
            upper = int.from_bytes(data, "big") << 16
        elif record_type not in (3, 5):
            raise ValueError(f"unsupported Intel HEX record type {record_type}")
    if not eof:
        raise ValueError("Intel HEX EOF record is missing")
    return memory


def normalize_ihex_region(text: str, app_start: int, app_end: int) -> bytes:
    if app_start < 0 or app_end <= app_start:
        raise ValueError("invalid application flash region")
    memory = _parse_ihex(text)
    normalized = bytearray(b"\xff" * (app_end - app_start))
    for address, byte in memory.items():
        if app_start <= address < app_end:
            normalized[address - app_start] = byte
    return bytes(normalized)


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

    actual = actual_flash[app_start:app_end]
    matches: list[FirmwareIdentity] = []
    for reference in references:
        if (reference.flash_size, reference.app_start, reference.app_end) != (
            flash_size,
            app_start,
            app_end,
        ):
            continue
        try:
            expected = normalize_ihex_region(reference.ihex, app_start, app_end)
        except ValueError:
            continue
        if actual == expected and reference.role in ROLES:
            matches.append(
                FirmwareIdentity(reference.role, reference.build_id, 0, None, "flash-fingerprint")
            )
    if not matches:
        return FingerprintResult("NO_MATCH", details=("no exact application image match",))
    unique = {(identity.role, identity.build_id): identity for identity in matches}
    if len(unique) != 1:
        identities = tuple(unique.values())
        return FingerprintResult(
            "AMBIGUOUS", matches=identities, details=("multiple references match the same image",)
        )
    identity = next(iter(unique.values()))
    return FingerprintResult("MATCH", identity=identity, matches=(identity,))
