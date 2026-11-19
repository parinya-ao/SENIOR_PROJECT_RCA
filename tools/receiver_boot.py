"""Prepare a one-page Receiver boot repair. No hardware writes in preparation."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from boot_analysis import analyze  # type: ignore[import-not-found]
    from device_detection.firmware_identity import (  # type: ignore[import-not-found]
        _parse_ihex,
        normalize_ihex_region,
    )
except ModuleNotFoundError:
    from tools.boot_analysis import analyze
    from tools.device_detection.firmware_identity import _parse_ihex, normalize_ihex_region

Json = Any

ROOT = Path(__file__).resolve().parents[1]
PAGE_SIZE = 512
FLASH_SIZE = 131072
APP_START = 0x5800
_RESET_VECTOR_SIZE = 4
_RJMP_MASK = 0xF000
_RJMP_OPCODE = 0xC000
_RJMP_OFFSET_MASK = 0x0FFF
_RJMP_SIGN_BIT = 0x0800
_JMP_MASK = 0xFE0E
_JMP_OPCODE = 0x940C
_CCP_REGISTER = 0x0034
_CCP_IOREG_KEY = 0xD8
_CPUINT_CTRLA = 0x0110
_PAGE_WRITE_BAUD_FALLBACK = 57_600
_FIRST_FLASH_BANK_SIZE = 65_536
_MAX_EEPROM_SIZE = 512
_FUSE_SIZE = 16
_USER_SIGNATURE_SIZE = 32
_REVIEWED_BOOTSIZE = 44
_CLI_OPCODE = 0x94F8
_EOR_MASK, _EOR_OPCODE = 0xFC00, 0x2400
_LDI_MASK, _LDI_OPCODE = 0xF000, 0xE000
_OUT_MASK, _OUT_OPCODE = 0xF800, 0xB800
_STS_MASK, _STS_OPCODE = 0xFE0F, 0x9200
_LDS_MASK, _LDS_OPCODE = 0xFE0E, 0x9004
_CPI_MASK, _CPI_OPCODE = 0xF000, 0x3000
_BRANCH_MASK, _BRANCH_OPCODE = 0xFC07, 0xF401
BACKUP = (
    ROOT / "artifacts/rf-proof/20261106T104722Z-target-backup/receiver-candidate-backup-flash.bin"
)
BACKUP_SHA = "a142fba14979cbc184d97c62cbfc8da75da01759b4cf6838f5b63aae36d4c943"
PORT = "/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0"
TOOLCHAIN = Path.home() / ".platformio/packages/toolchain-atmelavr/bin"
AVRDUDE = Path.home() / ".platformio/packages/tool-avrdude/avrdude"
AVRDUDE_CONF = AVRDUDE.with_name("avrdude.conf")


def sha(data: bytes) -> str:
    """Return the SHA-256 digest for one captured or generated image."""
    return hashlib.sha256(data).hexdigest()


def reset_target(entry: bytes, base: int) -> int:
    """Decode the first AVR RJMP/JMP instruction into its byte address."""
    if len(entry) != _RESET_VECTOR_SIZE:
        msg = "reset vector must contain four bytes"
        raise ValueError(msg)
    word = int.from_bytes(entry[:2], "little")
    if word & _RJMP_MASK == _RJMP_OPCODE:
        offset = word & _RJMP_OFFSET_MASK
        if offset & _RJMP_SIGN_BIT:
            offset -= _RJMP_OFFSET_MASK + 1
        return base + 2 + 2 * offset
    if word & _JMP_MASK == _JMP_OPCODE:
        return 2 * (
            ((word & 0x1F0) << 13) | ((word & 1) << 16) | int.from_bytes(entry[2:], "little")
        )
    msg = "reset is not an AVR RJMP/JMP instruction"
    raise ValueError(msg)


def patch_page0(original: bytes, stub: bytes) -> tuple[bytes, list[list[int]]]:
    """Replace only the approved page-0 prefix and report exact byte ranges."""
    if len(original) != FLASH_SIZE or not 0 < len(stub) <= PAGE_SIZE or len(stub) % 2:
        msg = "invalid full Flash backup or boot stub size"
        raise ValueError(msg)
    patched = stub + original[len(stub) : PAGE_SIZE]
    changes: list[list[int]] = []
    for address, (old, new) in enumerate(zip(original, patched, strict=False)):
        if old != new:
            if changes and changes[-1][1] == address:
                changes[-1][1] += 1
            else:
                changes.append([address, address + 1])
    return patched, changes


def trace_stub(  # noqa: C901, PLR0912, PLR0915 -- models each reviewed AVR instruction
    code: bytes, application_entry: bytes, steps: int = 80
) -> Json:
    """Bounded instruction model for this stack-free stub, not a hardware emulator."""
    registers = [0xA5] * 32
    stores: dict[int, int] = {}
    pc, zero, interrupts = 0, False, True
    for _ in range(steps):
        if pc == APP_START:
            return {
                "application_entered": True,
                "cpuint": stores.get(_CPUINT_CTRLA),
                "interrupts": interrupts,
            }
        if not 0 <= pc < len(code) - 1:
            msg = f"stub escaped approved code at {pc:#x}"
            raise ValueError(msg)
        word = int.from_bytes(code[pc : pc + 2], "little")
        following = pc + 2
        if word == _CLI_OPCODE:
            interrupts = False
        elif word & _EOR_MASK == _EOR_OPCODE:
            destination = (word >> 4) & 31
            source = (word & 15) | ((word >> 5) & 16)
            registers[destination] ^= registers[source]
            zero = registers[destination] == 0
        elif word & _LDI_MASK == _LDI_OPCODE:
            registers[16 + ((word >> 4) & 15)] = (word & 15) | ((word >> 4) & 0xF0)
        elif word & _OUT_MASK == _OUT_OPCODE:
            address = (word & 15) | ((word >> 5) & 0x30)
            stores[address] = registers[(word >> 4) & 31]
        elif word & _STS_MASK == _STS_OPCODE:
            address = int.from_bytes(code[pc + 2 : pc + 4], "little")
            if address != _CPUINT_CTRLA or stores.get(_CCP_REGISTER) != _CCP_IOREG_KEY:
                msg = "unexpected protected register write"
                raise ValueError(msg)
            stores[address] = registers[(word >> 4) & 31]
            following += 2
        elif word & _LDS_MASK == _LDS_OPCODE:
            address = registers[30] | registers[31] << 8
            offset = address - APP_START
            if not 0 <= offset < len(application_entry):
                msg = "unexpected Flash read"
                raise ValueError(msg)
            registers[(word >> 4) & 31] = application_entry[offset]
            if word & 1:
                address += 1
                registers[30], registers[31] = address & 255, address >> 8
        elif word & _CPI_MASK == _CPI_OPCODE:
            zero = registers[16 + ((word >> 4) & 15)] == ((word & 15) | ((word >> 4) & 0xF0))
        elif word & _BRANCH_MASK == _BRANCH_OPCODE:
            offset = (word >> 3) & 0x7F
            if offset & 0x40:
                offset -= 0x80
            if not zero:
                following += 2 * offset
        elif word & _RJMP_MASK == _RJMP_OPCODE:
            following = reset_target(code[pc : pc + 2] + b"\0\0", pc)
        elif word & _JMP_MASK == _JMP_OPCODE:
            following = reset_target(code[pc : pc + 4], pc)
        else:
            msg = f"unreviewed stub instruction {word:#x} at {pc:#x}"
            raise ValueError(msg)
        pc = following
    return {
        "application_entered": False,
        "parked_pc": pc,
        "cpuint": stores.get(_CPUINT_CTRLA),
        "interrupts": interrupts,
    }


def ihex(data: bytes, start: int = 0) -> str:
    """Encode a byte region as Intel HEX records and a terminating EOF record."""
    if not data or start < 0 or start + len(data) > _FIRST_FLASH_BANK_SIZE:
        msg = "this page image must fit the first 64 KiB"
        raise ValueError(msg)
    lines = []
    for offset in range(0, len(data), 16):
        chunk = data[offset : offset + 16]
        address = start + offset
        record = bytes([len(chunk), address >> 8, address & 255, 0]) + chunk
        lines.append(":" + (record + bytes([-sum(record) & 255])).hex().upper())
    return "\n".join(lines) + "\n:00000001FF\n"


def page_write_command(  # noqa: PLR0913, PLR0917 -- explicit programmer and page bounds stay separate
    executable: str | Path,
    configuration: str | Path,
    port: str | Path,
    image: str | Path,
    start: int = 0,
    size: int = PAGE_SIZE,
) -> list[str]:
    """Build an AVRDUDE command restricted to the approved first flash page."""
    if start != 0 or size != PAGE_SIZE:
        msg = "BOOT approval is restricted to exactly page 0"
        raise ValueError(msg)
    return [
        str(executable),
        "-N",
        "-C",
        str(configuration),
        "-p",
        "avr128da28",
        "-c",
        "serialupdi",
        "-P",
        str(port),
        "-b",
        "115200",
        "-D",
        "-T",
        f"erase flash {start:#x} {size:#x}",
        "-U",
        f"flash:w:{image}:i",
        "-U",
        f"flash:v:{image}:i",
    ]


def read_snapshot_command(proof: Json, name: str, command: list[str], timeout: int = 60) -> int:
    """Run a snapshot command with one bounded, lower-baud retry."""
    code, _, _ = proof.command(name, command, timeout)
    if code == 0:
        return int(code)
    retry = command.copy()
    baud_index = retry.index("-b") + 1
    if int(retry[baud_index]) <= _PAGE_WRITE_BAUD_FALLBACK:
        return int(code)
    retry[baud_index] = str(_PAGE_WRITE_BAUD_FALLBACK)
    return int(proof.command(f"{name}-baud57600", retry, timeout)[0])


def load_package(  # noqa: C901, PLR0912 -- validates the reviewed write scope before use
    path: str | Path, *, check_apps: bool = True
) -> Json:
    """Validate the reviewed page-0 package and its protected-range invariants."""
    path = Path(path)
    report = json.loads(path.read_text())
    if (
        report.get("origin") != "STATIC_BUILD_AND_AVRDUDE_DRYRUN"
        or report.get("boot_pages_written") != [0]
        or report.get("boot_write_range") != [0, 512]
        or report.get("backup_sha256") != BACKUP_SHA
    ):
        msg = "package is not the reviewed Receiver page-0 repair"
        raise ValueError(msg)
    if (
        report.get("application_start") != APP_START
        or report.get("page_size") != PAGE_SIZE
        or report.get("bootsize") != _REVIEWED_BOOTSIZE
        or report.get("codesize") != 0
        or set(report.get("application_images", {})) != {"receiver", "receiver_spi"}
        or type(report.get("stub_size")) is not int
        or not 0 < report["stub_size"] <= PAGE_SIZE
    ):
        msg = "invalid boot/application scope in approval package"
        raise ValueError(msg)
    if report.get("avrdude_sha256") != sha(AVRDUDE.read_bytes()) or report.get(
        "avrdude_conf_sha256"
    ) != sha(AVRDUDE_CONF.read_bytes()):
        msg = "programmer executable/configuration changed since scope review"
        raise ValueError(msg)
    for name, key in [
        ("receiver-boot-page0.hex", "page_hex_sha256"),
        ("receiver-boot-page0.original.hex", "restore_hex_sha256"),
    ]:
        data = (path.parent / name).read_bytes()
        memory = _parse_ihex(data.decode("ascii"))
        if sha(data) != report[key] or set(memory) != set(range(PAGE_SIZE)):
            msg = f"{name}: changed or out-of-scope page data"
            raise ValueError(msg)
    replacement = normalize_ihex_region(
        (path.parent / "receiver-boot-page0.hex").read_text(), 0, PAGE_SIZE
    )
    original = BACKUP.read_bytes()
    if (
        sha(original) != BACKUP_SHA
        or replacement[report["stub_size"] :] != original[report["stub_size"] : PAGE_SIZE]
    ):
        msg = "package would overwrite unapproved page-0 bytes"
        raise ValueError(msg)
    if sha(replacement) != report["replacement_page_sha256"]:
        msg = "replacement page hash mismatch"
        raise ValueError(msg)
    restoration = normalize_ihex_region(
        (path.parent / "receiver-boot-page0.original.hex").read_text(), 0, PAGE_SIZE
    )
    if restoration != original[:PAGE_SIZE]:
        msg = "restoration image differs from verified backup"
        raise ValueError(msg)
    entry = bytes.fromhex(report["application_images"]["receiver_spi"]["reset_bytes"])
    if not trace_stub(replacement[: report["stub_size"]], entry)["application_entered"]:
        msg = "replacement code does not reach APPCODE"
        raise ValueError(msg)
    for environment, expected in report["application_images"].items() if check_apps else []:
        for extension in ("hex", "elf"):
            image = ROOT / ".pio/build" / environment / ("firmware." + extension)
            if sha(image.read_bytes()) != expected[extension + "_sha256"]:
                msg = "application artifact changed since boot approval package was prepared"
                raise ValueError(
                    msg
                )
    if check_apps:
        padded = (path.parent / "receiver-spi-full-pages.hex").read_bytes()
        memory = _parse_ihex(padded.decode())
        if sha(padded) != report["spi_padded_hex_sha256"] or set(memory) != set(
            range(APP_START, report["application_write_range"][1])
        ):
            msg = "RF-disabled application page image differs from approved scope"
            raise ValueError(msg)
    return report


def read_snapshot(
    proof: Json,
    name: str,
    role: str = "receiver",
    *,
    current_target: bool = False,
    include_usersig: bool = False,
) -> Json:
    """Capture and validate protected memories before or after an authorized write."""
    import rf_proof  # type: ignore[import-not-found]  # noqa: PLC0415 -- avoids import cycle

    if role not in rf_proof.PORTS:
        msg = "unknown programming target"
        raise ValueError(msg)
    backup_name = "receiver" if role == "receiver" else "gateway"
    if current_target:
        identity = json.loads((ROOT / "config/current_hardware.json").read_text())[role]
        if identity["port_path"] != rf_proof.PORTS[role]:
            msg = "current target port differs from inventory"
            raise ValueError(msg)
    else:
        identity = json.loads(BACKUP.with_name("backup-summary.json").read_text())[
            backup_name + "-candidate"
        ]
    memories: tuple[str, ...] = ("signature", "sernum", "flash", "eeprom", "fuses", "lock")
    if include_usersig:
        memories += ("usersig",)
    command = [
        str(AVRDUDE),
        "-N",
        "-C",
        str(AVRDUDE_CONF),
        "-p",
        "avr128da28",
        "-c",
        "serialupdi",
        "-P",
        rf_proof.PORTS[role],
        "-b",
        "115200",
        "-D",
    ]
    for memory in memories:
        command += ["-U", f"{memory}:r:{proof.run_dir / (name + '-' + memory + '.bin')}:r"]
    code = read_snapshot_command(proof, name, command, 60)
    if code:
        msg = "Receiver snapshot failed; no further write permitted"
        raise ValueError(msg)
    result = {
        memory: (proof.run_dir / (name + "-" + memory + ".bin")).read_bytes() for memory in memories
    }
    if (
        result["signature"] != bytes.fromhex("1e970a")
        or result["sernum"] != bytes.fromhex(identity["device_serial_hex"])
        or len(result["flash"]) != FLASH_SIZE
        or len(result["fuses"]) != _FUSE_SIZE
        or len(result["eeprom"]) != _MAX_EEPROM_SIZE
        or result["lock"] != bytes.fromhex("5cc5c55c")
        or (include_usersig and len(result["usersig"]) != _USER_SIGNATURE_SIZE)
    ):
        msg = "Receiver identity/length/unlocked-state mismatch"
        raise ValueError(msg)
    expected_fuses = (
        bytes.fromhex(identity["fuses_hex"])
        if current_target
        else BACKUP.with_name(backup_name + "-candidate-backup-fuses.bin").read_bytes()
    )
    if result["fuses"] != expected_fuses:
        msg = "Receiver fuses differ from the reviewed target; no fuse changes allowed"
        raise ValueError(msg)
    return result


def require_preserved(before: Json, after: Json, first: int, end: int) -> None:
    """Reject any change outside the explicitly approved Flash page range."""
    names: tuple[str, ...] = ("signature", "sernum", "fuses", "eeprom", "lock")
    if "usersig" in before or "usersig" in after:
        names += ("usersig",)
    for name in names:
        if before[name] != after[name]:
            msg = f"unapproved {name} change; stop for recovery inspection"
            raise ValueError(msg)
    if (
        before["flash"][:first] != after["flash"][:first]
        or before["flash"][end:] != after["flash"][end:]
    ):
        msg = "Flash outside approved page range changed; stop for recovery inspection"
        raise ValueError(msg)


def install(  # noqa: C901, PLR0915 -- keeps the authorized write sequence explicit
    proof: Json, args: Json, *, restore: bool = False
) -> int:
    """Explicitly authorized write only; never called from an ordinary app upload."""
    token = getattr(
        args,
        "authorize_receiver_boot_restore" if restore else "authorize_receiver_boot_page0",
        None,
    )
    if not token or not getattr(args, "receiver_boot_package", None) or not args.authorize_upload:
        proof.note(
            "receiver-boot-install.log",
            "BLOCKED: specific boot-page authorization and package are required; "
            "no serial port opened.\n",
        )
        return 2
    report = load_package(args.receiver_boot_package, check_apps=not restore)
    expected_token = (
        report["restore_hex_sha256"]
        if restore
        else sha(Path(args.receiver_boot_package).read_bytes())
    )
    if token != expected_token:
        msg = "authorization hash does not match exact reviewed page image"
        raise ValueError(msg)
    import rf_proof  # noqa: PLC0415 -- avoids a module cycle

    errors = rf_proof.physical_readiness_errors(args)
    if errors or rf_proof.check_port_owners(proof, "boot-preflight"):
        proof.note(
            "receiver-boot-install.log",
            "BLOCKED: "
            + "; ".join(errors or ["UPDI port ownership"])
            + "; no serial port opened.\n",
        )
        return 2
    directory = Path(args.receiver_boot_package).parent
    before = read_snapshot(proof, "boot-before")
    original = BACKUP.read_bytes()
    if before["flash"][PAGE_SIZE:APP_START] != original[PAGE_SIZE:APP_START]:
        msg = "unreviewed installed BOOT content outside page 0"
        raise ValueError(msg)
    expected_page = normalize_ihex_region(
        (directory / "receiver-boot-page0.hex").read_text(), 0, PAGE_SIZE
    )
    if restore:
        # A failed write may leave page 0 partly erased; exact patched-byte matching
        # would make the recovery path unusable precisely when it is needed.
        proof.note(
            "receiver-boot-restore-before.json",
            json.dumps(
                {
                    "observed_page_sha256": sha(before["flash"][:PAGE_SIZE]),
                    "expected_original_page_sha256": report["original_page_sha256"],
                }
            )
            + "\n",
        )
        image = directory / "receiver-boot-page0.original.hex"
        expected_page = original[:PAGE_SIZE]
    else:
        if before["flash"][:APP_START] != original[:APP_START]:
            msg = "installed BOOT differs from the approved original"
            raise ValueError(msg)
        # Prove this programmer can write and read APPCODE before touching BOOT.
        app = report["application_images"]["receiver_spi"]
        app_image = directory / "receiver-spi-full-pages.hex"
        image_data = normalize_ihex_region(app_image.read_text(), APP_START, app["page_end"])
        command = [
            str(AVRDUDE),
            "-N",
            "-C",
            str(AVRDUDE_CONF),
            "-p",
            "avr128da28",
            "-c",
            "serialupdi",
            "-P",
            PORT,
            "-b",
            "115200",
            "-D",
            "-T",
            f"erase flash {APP_START:#x} {len(image_data):#x}",
            "-U",
            f"flash:w:{app_image}:i",
            "-U",
            f"flash:v:{app_image}:i",
        ]
        proof.note("receiver-app-program-command.json", json.dumps(command, indent=2) + "\n")
        code, _, _ = proof.command("receiver-spi-app-program", command, 120)
        if code:
            msg = "APPCODE programming failed; BOOT remains untouched"
            raise ValueError(msg)
        after_app = read_snapshot(proof, "boot-after-app")
        require_preserved(before, after_app, APP_START, app["page_end"])
        if after_app["flash"][APP_START : app["page_end"]] != image_data:
            msg = "APPCODE readback mismatch; BOOT remains untouched"
            raise ValueError(msg)
        before = after_app
        image = directory / "receiver-boot-page0.hex"
    command = page_write_command(AVRDUDE, AVRDUDE_CONF, PORT, image)
    proof.note("receiver-boot-program-command.json", json.dumps(command, indent=2) + "\n")
    code, _, _ = proof.command(
        "receiver-boot-page0-restore" if restore else "receiver-boot-page0-write", command, 60
    )
    if code:
        msg = (
            "BOOT page write/verify failed; use the separately authorized page-0 "
            "recovery procedure"
        )
        raise ValueError(
            msg
        )
    after = read_snapshot(proof, "boot-after")
    require_preserved(before, after, 0, PAGE_SIZE)
    if after["flash"][:PAGE_SIZE] != expected_page:
        msg = "BOOT page readback mismatch; stop for recovery inspection"
        raise ValueError(msg)
    receipt = {
        "origin": "PHYSICAL_UPDI",
        "operation": "restore" if restore else "install",
        "package": str(Path(args.receiver_boot_package).resolve()),
        "port": PORT,
        "page_hex_sha256": report["page_hex_sha256"],
        "boot_sha256": sha(after["flash"][:APP_START]),
        "serial": after["sernum"].hex(),
        "fuses": after["fuses"].hex(),
        "app_programming_verified": not restore,
        "physical_restore_test": "PASS" if restore else "NOT_RUN",
    }
    proof.note("receiver-boot-receipt.json", json.dumps(receipt, indent=2) + "\n")
    proof.note(
        "receiver-boot-install.log",
        "PASS: physical page readback and preservation checks; actual application boot "
        "still requires its device marker.\n",
    )
    return 0


def verify_live_receipt(proof: Json, path: str | Path) -> bool:
    """Compare a physical write receipt with current application and boot-page bytes."""
    receipt = json.loads(Path(path).read_text())
    if (
        receipt.get("origin") != "PHYSICAL_UPDI"
        or receipt.get("operation") != "install"
        or not receipt.get("app_programming_verified")
    ):
        return False
    report = load_package(receipt["package"], check_apps=False)
    if receipt.get("page_hex_sha256") != report["page_hex_sha256"] or receipt.get("port") != PORT:
        return False
    current = read_snapshot(proof, "boot-live-check")
    page = normalize_ihex_region(
        (Path(receipt["package"]).parent / "receiver-boot-page0.hex").read_text(), 0, PAGE_SIZE
    )
    original = BACKUP.read_bytes()
    return bool(
        current["flash"][:PAGE_SIZE] == page
        and current["flash"][PAGE_SIZE:APP_START] == original[PAGE_SIZE:APP_START]
        and sha(current["flash"][:APP_START]) == receipt.get("boot_sha256")
    )


def _build_handoff(
    directory: Path, reset: bytes, command: Any
) -> tuple[bytes, dict[str, Any]]:
    """Compile and trace the historical handoff with the supplied reset vector."""
    header = f"#define APP_START {APP_START}\n#define CCP_IOREG_VALUE 0xD8\n" + "".join(
        f"#define RESET_BYTE_{index} {value}\n" for index, value in enumerate(reset)
    )
    (directory / "handoff_config.h").write_text(header)
    code, _, _ = command(
        "boot-device-contract",
        [
            str(TOOLCHAIN / "avr-gcc"),
            "-mmcu=avr128da28",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-fsyntax-only",
            "-I",
            str(directory),
            str(ROOT / "src/receiver/bootloader/handoff/receiver_handoff_contract.c"),
        ],
    )
    if code:
        msg = "installed AVR device definitions disagree with handoff contract"
        raise ValueError(msg)
    elf = directory / "receiver-handoff.elf"
    code, _, _ = command(
        "boot-compile",
        [
            str(TOOLCHAIN / "avr-gcc"),
            "-mmcu=avr128da28",
            "-nostdlib",
            "-nostartfiles",
            "-x",
            "assembler-with-cpp",
            "-I",
            str(directory),
            f"-Wl,-Map={directory / 'receiver-handoff.map'}",
            "-Wl,--section-start=.text=0",
            "-Wl,-e,_start",
            str(ROOT / "src/receiver/bootloader/handoff/receiver_handoff.S"),
            "-o",
            str(elf),
        ],
    )
    if code:
        msg = "boot handoff compilation failed"
        raise ValueError(msg)
    for output_format, name in [
        ("binary", "receiver-handoff.bin"),
        ("ihex", "receiver-handoff.hex"),
    ]:
        subprocess.run(  # noqa: S603 -- fixed, absolute toolchain executable
            [str(TOOLCHAIN / "avr-objcopy"), "-O", output_format, str(elf), str(directory / name)],
            check=True,
        )
    disassembly = subprocess.check_output(  # noqa: S603 -- fixed, absolute toolchain executable
        [str(TOOLCHAIN / "avr-objdump"), "-d", str(elf)], text=True
    )
    (directory / "receiver-handoff.disassembly.txt").write_text(disassembly)
    audit = analyze(disassembly, APP_START)
    if audit["application_transfers"] != [APP_START] or audit["unresolved"]:
        msg = "compiled stub has no fully resolved APPCODE transfer"
        raise ValueError(msg)
    stub = (directory / "receiver-handoff.bin").read_bytes()
    traces = {
        "matching_reset": trace_stub(stub, reset),
        "blank_application": trace_stub(stub, b"\xff" * 4),
    }
    if (
        traces["matching_reset"] != {"application_entered": True, "cpuint": 0, "interrupts": False}
        or traces["blank_application"]["application_entered"]
    ):
        msg = "compiled boot behavior differs from required handoff"
        raise ValueError(msg)
    for index in range(_RESET_VECTOR_SIZE):
        wrong = bytearray(reset)
        wrong[index] ^= 1
        traces[f"wrong_reset_byte_{index}"] = trace_stub(stub, bytes(wrong))
        if traces[f"wrong_reset_byte_{index}"]["application_entered"]:
            msg = "boot guard accepted an incorrect reset vector"
            raise ValueError(msg)
    return stub, traces


def build_fixture(directory: Path) -> None:
    """Build the archived handoff without preparing a device programming package."""
    directory.mkdir(parents=True)

    def run_tool(_name: str, argv: list[str]) -> tuple[int, bytes, bytes]:
        result = subprocess.run(argv, check=False, capture_output=True)  # noqa: S603
        if result.returncode:
            print(result.stderr.decode(errors="replace"), end="")
        return result.returncode, result.stdout, result.stderr

    _, traces = _build_handoff(directory, bytes.fromhex("52c00000"), run_tool)
    (directory / "receiver-boot-instruction-traces.json").write_text(
        json.dumps(traces, indent=2) + "\n"
    )


def prepare(proof: Json) -> int:  # noqa: C901, PLR0912, PLR0915 -- builds and verifies one approved image set
    """Compile, inspect and simulate the exact proposed overwrite and restoration."""
    directory = proof.run_dir
    original = BACKUP.read_bytes()
    if len(original) != FLASH_SIZE or sha(original) != BACKUP_SHA:
        msg = "Receiver backup identity/integrity mismatch"
        raise ValueError(msg)
    ssot = json.loads((ROOT / "config/lora_system.json").read_text())
    board = ssot["receiver_board"]
    if (board["bootsize"], board["codesize"], board["image_start"]) != (
        _REVIEWED_BOOTSIZE,
        0,
        APP_START,
    ):
        msg = "Receiver fuse geometry differs from reviewed target"
        raise ValueError(msg)
    code, stdout, stderr = proof.command("boot-avrdude-version", [str(AVRDUDE), "--version"])
    if code or not re.search(rb"\bversion 8\.1\b", stdout + stderr):
        msg = "page-erase strategy is reviewed for installed AVRDUDE 8.1 only"
        raise ValueError(msg)
    code, stdout, _ = proof.command(
        "boot-avrdude-device-definition",
        [str(AVRDUDE), "-N", "-C", str(AVRDUDE_CONF), "-p", "avr128da28/S"],
    )
    definition = stdout.decode()
    flash = re.search(r'memory "flash"(.*?^\s*;\s*$)', definition, re.DOTALL | re.MULTILINE)
    if (
        code
        or not flash
        or not re.search(r"page_size\s*=\s*512", flash.group(1))
        or not re.search(r"size\s*=\s*0x20000", flash.group(1))
    ):
        msg = "installed programmer does not declare expected Flash/page geometry"
        raise ValueError(msg)
    app_info = {}
    reset = None
    for environment in ("receiver", "receiver_spi"):
        path = ROOT / ".pio/build" / environment / "firmware.hex"
        data = path.read_bytes()
        memory = _parse_ihex(data.decode("ascii"))
        start, end = min(memory), max(memory) + 1
        if start != APP_START or end > board["image_end_exclusive"]:
            msg = f"{environment}: image outside Receiver APPCODE"
            raise ValueError(msg)
        entry = normalize_ihex_region(data.decode("ascii"), start, start + 4)
        target = reset_target(entry, start)
        if not start <= target < end or (reset is not None and entry != reset):
            msg = "applications do not share a valid reset vector"
            raise ValueError(msg)
        reset = entry
        elf = path.with_suffix(".elf")
        symbols = subprocess.check_output(  # noqa: S603 -- fixed, absolute toolchain executable
            [str(TOOLCHAIN / "avr-nm"), str(elf)], text=True
        )
        if not re.search(r"^00005800\s+\w\s+__vectors$", symbols, re.MULTILINE):
            msg = "ELF __vectors differs from HEX start"
            raise ValueError(msg)
        (directory / (environment + "-symbols.txt")).write_text(symbols)
        sections = subprocess.check_output(  # noqa: S603 -- fixed, absolute toolchain executable
            [str(TOOLCHAIN / "avr-objdump"), "-h", str(elf)], text=True
        )
        (directory / (environment + "-sections.txt")).write_text(sections)
        startup = subprocess.check_output(  # noqa: S603 -- fixed, absolute toolchain executable
            [
                str(TOOLCHAIN / "avr-objdump"),
                "-d",
                f"--start-address={start:#x}",
                f"--stop-address={target + 0x90:#x}",
                str(elf),
            ],
            text=True,
        )
        if not re.search(r"sts\s+0x0110,", startup):
            msg = "Receiver startup does not contain the reviewed CPUINT initialization"
            raise ValueError(msg)
        (directory / (environment + "-startup.disassembly.txt")).write_text(startup)
        (directory / (environment + ".hex")).write_bytes(data)
        (directory / (environment + ".elf")).write_bytes(elf.read_bytes())
        app_info[environment] = {
            "hex_sha256": sha(data),
            "elf_sha256": sha(elf.read_bytes()),
            "start": start,
            "end": end,
            "page_end": (end + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE,
            "reset_bytes": entry.hex(),
            "reset_target": target,
        }
    if reset is None:
        msg = "application reset vector was not found"
        raise ValueError(msg)
    stub, traces = _build_handoff(directory, reset, proof.command)
    proof.note("receiver-boot-instruction-traces.json", json.dumps(traces, indent=2) + "\n")
    page, changes = patch_page0(original, stub)
    (directory / "receiver-boot-page0.hex").write_text(ihex(page))
    (directory / "receiver-boot-page0.original.hex").write_text(ihex(original[:PAGE_SIZE]))
    spi_data = normalize_ihex_region(
        (ROOT / ".pio/build/receiver_spi/firmware.hex").read_text(),
        APP_START,
        app_info["receiver_spi"]["page_end"],
    )
    (directory / "receiver-spi-full-pages.hex").write_text(ihex(spi_data, APP_START))
    patched = page + original[PAGE_SIZE:]
    (directory / "expected-patched-flash.bin").write_bytes(patched)
    # The exact installed AVRDUDE processes page-scoped commands on its simulator only.
    dryrun = [
        str(AVRDUDE),
        "-N",
        "-C",
        str(AVRDUDE_CONF),
        "-p",
        "avr128da28",
        "-c",
        "dryrun",
        "-D",
        "-U",
        f"flash:w:{BACKUP}:r",
        "-T",
        "erase flash 0x0 0x200",
        "-U",
        f"flash:w:{directory / 'receiver-boot-page0.hex'}:i",
        "-U",
        f"flash:v:{directory / 'expected-patched-flash.bin'}:r",
        "-T",
        "erase flash 0x0 0x200",
        "-U",
        f"flash:w:{directory / 'receiver-boot-page0.original.hex'}:i",
        "-U",
        f"flash:v:{BACKUP}:r",
    ]
    code, _, _ = proof.command("boot-page-write-restore-dryrun", dryrun, 30)
    if code:
        msg = "installed AVRDUDE page-write/restore simulation failed"
        raise ValueError(msg)
    expected_app = (
        original[:APP_START] + spi_data + original[app_info["receiver_spi"]["page_end"] :]
    )
    (directory / "expected-spi-app-flash.bin").write_bytes(expected_app)
    (directory / "expected-spi-app-and-boot.bin").write_bytes(page + expected_app[PAGE_SIZE:])
    staged = [
        str(AVRDUDE),
        "-N",
        "-C",
        str(AVRDUDE_CONF),
        "-p",
        "avr128da28",
        "-c",
        "dryrun",
        "-D",
        "-U",
        f"flash:w:{BACKUP}:r",
        "-T",
        f"erase flash {APP_START:#x} {len(spi_data):#x}",
        "-U",
        f"flash:w:{directory / 'receiver-spi-full-pages.hex'}:i",
        "-U",
        f"flash:v:{directory / 'expected-spi-app-flash.bin'}:r",
        "-T",
        "erase flash 0x0 0x200",
        "-U",
        f"flash:w:{directory / 'receiver-boot-page0.hex'}:i",
        "-U",
        f"flash:v:{directory / 'expected-spi-app-and-boot.bin'}:r",
        "-T",
        "erase flash 0x0 0x200",
        "-U",
        f"flash:w:{directory / 'receiver-boot-page0.original.hex'}:i",
        "-U",
        f"flash:v:{directory / 'expected-spi-app-flash.bin'}:r",
    ]
    code, _, _ = proof.command("boot-app-first-boot-last-recovery-dryrun", staged, 30)
    if code:
        msg = "APPCODE-first/BOOT-last/recovery simulation failed"
        raise ValueError(msg)
    report = {
        "schema_version": 1,
        "origin": "STATIC_BUILD_AND_AVRDUDE_DRYRUN",
        "avrdude_sha256": sha(AVRDUDE.read_bytes()),
        "avrdude_conf_sha256": sha(AVRDUDE_CONF.read_bytes()),
        "device": "AVR128DA28",
        "expected_serial": "42032240221041150120010500000000",
        "backup_sha256": BACKUP_SHA,
        "bootsize": _REVIEWED_BOOTSIZE,
        "codesize": 0,
        "application_start": APP_START,
        "application_images": app_info,
        "page_size": PAGE_SIZE,
        "boot_pages_written": [0],
        "application_pages_to_program": list(
            range(APP_START // PAGE_SIZE, app_info["receiver_spi"]["page_end"] // PAGE_SIZE)
        ),
        "application_write_range": [APP_START, app_info["receiver_spi"]["page_end"]],
        "boot_write_range": [0, PAGE_SIZE],
        "changed_byte_ranges": changes,
        "stub_size": len(stub),
        "original_page_sha256": sha(original[:PAGE_SIZE]),
        "replacement_page_sha256": sha(page),
        "page_hex_sha256": sha((directory / "receiver-boot-page0.hex").read_bytes()),
        "restore_hex_sha256": sha((directory / "receiver-boot-page0.original.hex").read_bytes()),
        "spi_padded_hex_sha256": sha((directory / "receiver-spi-full-pages.hex").read_bytes()),
        "handoff_audit": audit,
        "physical_programming": "NOT_RUN",
        "physical_restore_test": "NOT_RUN",
        "write_command": page_write_command(
            AVRDUDE, AVRDUDE_CONF, PORT, directory / "receiver-boot-page0.hex"
        ),
        "restore_command": page_write_command(
            AVRDUDE, AVRDUDE_CONF, PORT, directory / "receiver-boot-page0.original.hex"
        ),
    }
    report["application_write_command"] = [
        str(AVRDUDE),
        "-N",
        "-C",
        str(AVRDUDE_CONF),
        "-p",
        "avr128da28",
        "-c",
        "serialupdi",
        "-P",
        PORT,
        "-b",
        "115200",
        "-D",
        "-T",
        f"erase flash {APP_START:#x} {len(spi_data):#x}",
        "-U",
        f"flash:w:{directory / 'receiver-spi-full-pages.hex'}:i",
        "-U",
        f"flash:v:{directory / 'receiver-spi-full-pages.hex'}:i",
    ]
    proof.note("receiver-boot-overwrite-map.json", json.dumps(report, indent=2) + "\n")
    proof.note(
        "receiver-boot-prepare.log",
        "PASS: static one-page boot package and simulated restoration; hardware writes NOT RUN.\n",
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the historical Receiver handoff fixture.")
    parser.add_argument("output_dir", type=Path, help="new directory for offline fixture artifacts")
    build_fixture(parser.parse_args().output_dir)
