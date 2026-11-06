"""Explicit, bounded UPDI probes through the repository's upditerm tool."""

from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
from typing import Any, Callable

from .evidence import ProbeEvidence
from .firmware_identity import match_flash_fingerprint, parse_identity_stream


ROOT = Path(__file__).resolve().parents[2]
UPDITERM = ROOT / "third_party" / "upditerm" / "upditerm.py"


def _require_safe(hardware_safe: bool) -> None:
    if not hardware_safe:
        raise PermissionError("UPDI access requires --hardware-safe after physical wiring checks")


def _port_busy(port: str, runner: Callable[..., Any]) -> bool:
    try:
        result = runner(["fuser", "-v", port], capture_output=True, text=True,
                        timeout=1.0, check=False)
    except (OSError, subprocess.SubprocessError, TypeError):
        return False
    return result.returncode == 0 and bool((result.stdout or "") + (result.stderr or ""))


def _is_access_error(text: str) -> bool:
    return bool(re.search(r"cannot open serial port|permission denied|resource busy|device or resource busy|access is denied", text, re.I))


def _run_bounded(
    argv: list[str], *, timeout: float, popen: Callable[..., Any] = subprocess.Popen
) -> tuple[int | None, str, str, bool]:
    timeout = max(0.1, min(float(timeout), 10.0))
    try:
        process = popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, bufsize=1)
    except OSError as exc:
        return None, "", str(exc), False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout or "", stderr or "", False
    except subprocess.TimeoutExpired:
        try:
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=1.0)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
            stdout, stderr = process.communicate()
        return process.returncode, stdout or "", stderr or "", True


def identify_mcu(sib: str) -> str | None:
    """Return an exact part only when the SIB text actually contains it."""
    compact = re.sub(r"[^A-Z0-9]", "", sib.upper())
    return "AVR128DA28" if "AVR128DA28" in compact else None


def probe_target_sib(
    port: str,
    *,
    hardware_safe: bool = False,
    baudrate: int = 38400,
    timeout: float = 3.0,
    command_runner: Callable[..., Any] = subprocess.run,
    popen: Callable[..., Any] = subprocess.Popen,
    upditerm_script: str | Path = UPDITERM,
) -> ProbeEvidence:
    """Use upditerm -i without its reset option; only run after explicit safety check."""
    _require_safe(hardware_safe)
    if _port_busy(port, command_runner):
        return ProbeEvidence(access_status="INACCESSIBLE", mcu_status="INACCESSIBLE",
                             error=f"serial port is already held: {port}")
    argv = [sys.executable, str(upditerm_script), "-i", port, str(baudrate)]
    code, stdout, stderr, timed_out = _run_bounded(argv, timeout=timeout, popen=popen)
    combined = f"{stdout}\n{stderr}".strip()
    if timed_out or code != 0:
        status = "INACCESSIBLE" if _is_access_error(combined) else "PROBE_FAILED"
        return ProbeEvidence(access_status=status, mcu_status=status,
                             error=combined or "upditerm SIB query failed or timed out")
    sib = stdout.strip()
    if not sib:
        return ProbeEvidence(mcu_status="UNKNOWN", error="upditerm returned an empty SIB")
    return ProbeEvidence(mcu_identity=identify_mcu(sib), mcu_status="OK", sib=sib)


def probe_firmware_identity(
    port: str,
    *,
    hardware_safe: bool = False,
    baudrate: int = 38400,
    timeout: float = 2.0,
    command_runner: Callable[..., Any] = subprocess.run,
    popen: Callable[..., Any] = subprocess.Popen,
    upditerm_script: str | Path = UPDITERM,
) -> ProbeEvidence:
    """Capture UPDI virtual-UART output without requesting a target reset."""
    _require_safe(hardware_safe)
    if _port_busy(port, command_runner):
        return ProbeEvidence(access_status="INACCESSIBLE", firmware_status="INACCESSIBLE",
                             error=f"serial port is already held: {port}")
    with tempfile.TemporaryDirectory(prefix="lora-role-") as temp:
        logfile = Path(temp) / "upditerm.log"
        argv = [sys.executable, str(upditerm_script), "-q", "-l", str(logfile),
                port, str(baudrate)]
        code, stdout, stderr, timed_out = _run_bounded(argv, timeout=timeout, popen=popen)
        try:
            captured = logfile.read_bytes()
        except OSError:
            captured = b""
    parsed = parse_identity_stream(captured)
    combined = f"{stdout}\n{stderr}".strip()
    if timed_out or code != 0:
        status = "INACCESSIBLE" if _is_access_error(combined) else "PROBE_FAILED"
        return ProbeEvidence(access_status=status, firmware_status=status,
                             parse_status=parsed.status,
                             error=combined or "upditerm identity capture failed or timed out")
    return ProbeEvidence(
        firmware_identity=parsed.identity,
        firmware_status="OK",
        parse_status=parsed.status,
        error="; ".join(parsed.details) if parsed.details else None,
    )


def read_firmware_flash(
    port: str,
    *,
    hardware_safe: bool = False,
    authorize_flash_read: bool = False,
    boot_layout_verified: bool = False,
    mcu_identity: str | None = None,
    flash_size: int,
    command_runner: Callable[..., Any] = subprocess.run,
    timeout: float = 10.0,
    avrdude: str = "avrdude",
) -> bytes | None:
    """Read flash only under explicit authorization and known target geometry."""
    if not (hardware_safe and authorize_flash_read and boot_layout_verified):
        raise PermissionError(
            "flash read requires --hardware-safe, --authorize-flash-read, and verified BOOT layout"
        )
    if mcu_identity != "AVR128DA28":
        raise PermissionError("flash read requires an identified AVR128DA28 target")
    if flash_size <= 0:
        raise ValueError("flash_size must be positive")
    if _port_busy(port, command_runner):
        raise PermissionError(f"serial port is already held: {port}")
    with tempfile.TemporaryDirectory(prefix="lora-flash-read-") as temp:
        raw_path = Path(temp) / "flash.bin"
        argv = [avrdude, "-p", "avr128da28", "-c", "serialupdi", "-P", port,
                "-U", f"flash:r:{raw_path}:r"]
        try:
            completed = command_runner(argv, capture_output=True, text=True,
                                       timeout=timeout, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            return None
        if completed.returncode != 0 or not raw_path.is_file():
            return None
        image = raw_path.read_bytes()
    return image if len(image) == flash_size else None


def firmware_fingerprint_evidence(
    actual_flash: bytes | None,
    references: list[Any] | tuple[Any, ...],
    *,
    flash_size: int,
    app_start: int,
    app_end: int,
) -> ProbeEvidence:
    result = match_flash_fingerprint(actual_flash, references, flash_size=flash_size,
                                     app_start=app_start, app_end=app_end)
    return ProbeEvidence(
        fingerprint_identity=result.identity,
        fingerprint_status={"MATCH": "OK", "UNAVAILABLE": "NOT_ATTEMPTED",
                            "AMBIGUOUS": "AMBIGUOUS", "INCOMPLETE": "PROBE_FAILED",
                            "NO_MATCH": "OK"}.get(result.status, "PROBE_FAILED"),
        parse_status=result.status,
        error="; ".join(result.details) if result.details else None,
    )
