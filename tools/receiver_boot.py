"""Prepare a one-page Receiver boot repair. No hardware writes in preparation."""

import hashlib
import json
import re
import subprocess
from pathlib import Path

try:
    from boot_analysis import analyze
    from device_detection.firmware_identity import _parse_ihex, normalize_ihex_region
except ModuleNotFoundError:
    from tools.boot_analysis import analyze
    from tools.device_detection.firmware_identity import _parse_ihex, normalize_ihex_region

ROOT = Path(__file__).resolve().parents[1]
PAGE_SIZE = 512
FLASH_SIZE = 131072
APP_START = 0x5800
BACKUP = (
    ROOT / "artifacts/rf-proof/20261106T104722Z-target-backup/receiver-candidate-backup-flash.bin"
)
BACKUP_SHA = "a142fba14979cbc184d97c62cbfc8da75da01759b4cf6838f5b63aae36d4c943"
PORT = "/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0"
TOOLCHAIN = Path.home() / ".platformio/packages/toolchain-atmelavr/bin"
AVRDUDE = Path.home() / ".platformio/packages/tool-avrdude/avrdude"
AVRDUDE_CONF = AVRDUDE.with_name("avrdude.conf")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reset_target(entry, base):
    if len(entry) != 4:
        raise ValueError("reset vector must contain four bytes")
    word = int.from_bytes(entry[:2], "little")
    if word & 0xF000 == 0xC000:
        offset = word & 0xFFF
        if offset & 0x800:
            offset -= 0x1000
        return base + 2 + 2 * offset
    if word & 0xFE0E == 0x940C:
        return 2 * (
            ((word & 0x1F0) << 13) | ((word & 1) << 16) | int.from_bytes(entry[2:], "little")
        )
    raise ValueError("reset is not an AVR RJMP/JMP instruction")


def patch_page0(original, stub):
    if len(original) != FLASH_SIZE or not 0 < len(stub) <= PAGE_SIZE or len(stub) % 2:
        raise ValueError("invalid full Flash backup or boot stub size")
    patched = stub + original[len(stub) : PAGE_SIZE]
    changes = []
    for address, (old, new) in enumerate(zip(original, patched)):
        if old != new:
            if changes and changes[-1][1] == address:
                changes[-1][1] += 1
            else:
                changes.append([address, address + 1])
    return patched, changes


def trace_stub(code, application_entry, steps=80):
    """Bounded instruction model for this stack-free stub, not a hardware emulator."""
    registers = [0xA5] * 32
    stores = {}
    pc, zero, interrupts = 0, False, True
    for _ in range(steps):
        if pc == APP_START:
            return dict(application_entered=True, cpuint=stores.get(0x110), interrupts=interrupts)
        if not 0 <= pc < len(code) - 1:
            raise ValueError(f"stub escaped approved code at {pc:#x}")
        word = int.from_bytes(code[pc : pc + 2], "little")
        following = pc + 2
        if word == 0x94F8:
            interrupts = False
        elif word & 0xFC00 == 0x2400:
            destination = (word >> 4) & 31
            source = (word & 15) | ((word >> 5) & 16)
            registers[destination] ^= registers[source]
            zero = registers[destination] == 0
        elif word & 0xF000 == 0xE000:
            registers[16 + ((word >> 4) & 15)] = (word & 15) | ((word >> 4) & 0xF0)
        elif word & 0xF800 == 0xB800:
            address = (word & 15) | ((word >> 5) & 0x30)
            stores[address] = registers[(word >> 4) & 31]
        elif word & 0xFE0F == 0x9200:
            address = int.from_bytes(code[pc + 2 : pc + 4], "little")
            if address != 0x110 or stores.get(0x34) != 0xD8:
                raise ValueError("unexpected protected register write")
            stores[address] = registers[(word >> 4) & 31]
            following += 2
        elif word & 0xFE0E == 0x9004:
            address = registers[30] | registers[31] << 8
            offset = address - APP_START
            if not 0 <= offset < len(application_entry):
                raise ValueError("unexpected Flash read")
            registers[(word >> 4) & 31] = application_entry[offset]
            if word & 1:
                address += 1
                registers[30], registers[31] = address & 255, address >> 8
        elif word & 0xF000 == 0x3000:
            zero = registers[16 + ((word >> 4) & 15)] == ((word & 15) | ((word >> 4) & 0xF0))
        elif word & 0xFC07 == 0xF401:
            offset = (word >> 3) & 0x7F
            if offset & 0x40:
                offset -= 0x80
            if not zero:
                following += 2 * offset
        elif word & 0xF000 == 0xC000:
            following = reset_target(code[pc : pc + 2] + b"\0\0", pc)
        elif word & 0xFE0E == 0x940C:
            following = reset_target(code[pc : pc + 4], pc)
        else:
            raise ValueError(f"unreviewed stub instruction {word:#x} at {pc:#x}")
        pc = following
    return dict(
        application_entered=False, parked_pc=pc, cpuint=stores.get(0x110), interrupts=interrupts
    )


def ihex(data, start=0):
    if not data or start < 0 or start + len(data) > 65536:
        raise ValueError("this page image must fit the first 64 KiB")
    lines = []
    for offset in range(0, len(data), 16):
        chunk = data[offset : offset + 16]
        address = start + offset
        record = bytes([len(chunk), address >> 8, address & 255, 0]) + chunk
        lines.append(":" + (record + bytes([-sum(record) & 255])).hex().upper())
    return "\n".join(lines) + "\n:00000001FF\n"


def page_write_command(executable, configuration, port, image, start=0, size=PAGE_SIZE):
    if start != 0 or size != PAGE_SIZE:
        raise ValueError("BOOT approval is restricted to exactly page 0")
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


def load_package(path, check_apps=True):
    path = Path(path)
    report = json.loads(path.read_text())
    if (
        report.get("origin") != "STATIC_BUILD_AND_AVRDUDE_DRYRUN"
        or report.get("boot_pages_written") != [0]
        or report.get("boot_write_range") != [0, 512]
        or report.get("backup_sha256") != BACKUP_SHA
    ):
        raise ValueError("package is not the reviewed Receiver page-0 repair")
    if (
        report.get("application_start") != APP_START
        or report.get("page_size") != PAGE_SIZE
        or report.get("bootsize") != 44
        or report.get("codesize") != 0
        or set(report.get("application_images", {})) != {"receiver", "receiver_spi"}
        or type(report.get("stub_size")) is not int
        or not 0 < report["stub_size"] <= PAGE_SIZE
    ):
        raise ValueError("invalid boot/application scope in approval package")
    if report.get("avrdude_sha256") != sha(AVRDUDE.read_bytes()) or report.get(
        "avrdude_conf_sha256"
    ) != sha(AVRDUDE_CONF.read_bytes()):
        raise ValueError("programmer executable/configuration changed since scope review")
    for name, key in [
        ("receiver-boot-page0.hex", "page_hex_sha256"),
        ("receiver-boot-page0.original.hex", "restore_hex_sha256"),
    ]:
        data = (path.parent / name).read_bytes()
        memory = _parse_ihex(data.decode("ascii"))
        if sha(data) != report[key] or set(memory) != set(range(PAGE_SIZE)):
            raise ValueError(f"{name}: changed or out-of-scope page data")
    replacement = normalize_ihex_region(
        (path.parent / "receiver-boot-page0.hex").read_text(), 0, PAGE_SIZE
    )
    original = BACKUP.read_bytes()
    if (
        sha(original) != BACKUP_SHA
        or replacement[report["stub_size"] :] != original[report["stub_size"] : PAGE_SIZE]
    ):
        raise ValueError("package would overwrite unapproved page-0 bytes")
    if sha(replacement) != report["replacement_page_sha256"]:
        raise ValueError("replacement page hash mismatch")
    restoration = normalize_ihex_region(
        (path.parent / "receiver-boot-page0.original.hex").read_text(), 0, PAGE_SIZE
    )
    if restoration != original[:PAGE_SIZE]:
        raise ValueError("restoration image differs from verified backup")
    entry = bytes.fromhex(report["application_images"]["receiver_spi"]["reset_bytes"])
    if not trace_stub(replacement[: report["stub_size"]], entry)["application_entered"]:
        raise ValueError("replacement code does not reach APPCODE")
    for environment, expected in report["application_images"].items() if check_apps else []:
        for extension in ("hex", "elf"):
            image = ROOT / ".pio/build" / environment / ("firmware." + extension)
            if sha(image.read_bytes()) != expected[extension + "_sha256"]:
                raise ValueError(
                    "application artifact changed since boot approval package was prepared"
                )
    if check_apps:
        padded = (path.parent / "receiver-spi-full-pages.hex").read_bytes()
        memory = _parse_ihex(padded.decode())
        if sha(padded) != report["spi_padded_hex_sha256"] or set(memory) != set(
            range(APP_START, report["application_write_range"][1])
        ):
            raise ValueError("RF-disabled application page image differs from approved scope")
    return report


def read_snapshot(proof, name, role="receiver", *, current_target=False):
    import rf_proof

    if role not in rf_proof.PORTS:
        raise ValueError("unknown programming target")
    backup_name = "receiver" if role == "receiver" else "gateway"
    if current_target:
        identity = json.loads((ROOT / "config/current_hardware.json").read_text())[role]
        if identity["port_path"] != rf_proof.PORTS[role]:
            raise ValueError("current target port differs from inventory")
    else:
        identity = json.loads(BACKUP.with_name("backup-summary.json").read_text())[
            backup_name + "-candidate"
        ]
    memories = ("signature", "sernum", "flash", "eeprom", "fuses", "lock")
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
    code, _, _ = proof.command(name, command, 60)
    if code:
        raise ValueError("Receiver snapshot failed; no further write permitted")
    result = {
        memory: (proof.run_dir / (name + "-" + memory + ".bin")).read_bytes() for memory in memories
    }
    if (
        result["signature"] != bytes.fromhex("1e970a")
        or result["sernum"] != bytes.fromhex(identity["device_serial_hex"])
        or len(result["flash"]) != FLASH_SIZE
        or len(result["fuses"]) != 16
        or len(result["eeprom"]) != 512
        or result["lock"] != bytes.fromhex("5cc5c55c")
    ):
        raise ValueError("Receiver identity/length/unlocked-state mismatch")
    expected_fuses = (
        bytes.fromhex(identity["fuses_hex"])
        if current_target
        else BACKUP.with_name(backup_name + "-candidate-backup-fuses.bin").read_bytes()
    )
    if result["fuses"] != expected_fuses:
        raise ValueError("Receiver fuses differ from the reviewed target; no fuse changes allowed")
    return result


def require_preserved(before, after, first, end):
    for name in ("signature", "sernum", "fuses", "eeprom", "lock"):
        if before[name] != after[name]:
            raise ValueError(f"unapproved {name} change; stop for recovery inspection")
    if (
        before["flash"][:first] != after["flash"][:first]
        or before["flash"][end:] != after["flash"][end:]
    ):
        raise ValueError("Flash outside approved page range changed; stop for recovery inspection")


def install(proof, args, restore=False):
    """Explicitly authorized write only; never called from an ordinary app upload."""
    token = getattr(
        args,
        "authorize_receiver_boot_restore" if restore else "authorize_receiver_boot_page0",
        None,
    )
    if not token or not getattr(args, "receiver_boot_package", None) or not args.authorize_upload:
        proof.note(
            "receiver-boot-install.log",
            "BLOCKED: specific boot-page authorization and package are required; no serial port opened.\n",
        )
        return 2
    report = load_package(args.receiver_boot_package, check_apps=not restore)
    expected_token = (
        report["restore_hex_sha256"]
        if restore
        else sha(Path(args.receiver_boot_package).read_bytes())
    )
    if token != expected_token:
        raise ValueError("authorization hash does not match exact reviewed page image")
    import rf_proof

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
        raise ValueError("unreviewed installed BOOT content outside page 0")
    expected_page = normalize_ihex_region(
        (directory / "receiver-boot-page0.hex").read_text(), 0, PAGE_SIZE
    )
    if restore:
        # A failed write may leave page 0 partly erased; exact patched-byte matching
        # would make the recovery path unusable precisely when it is needed.
        proof.note(
            "receiver-boot-restore-before.json",
            json.dumps(
                dict(
                    observed_page_sha256=sha(before["flash"][:PAGE_SIZE]),
                    expected_original_page_sha256=report["original_page_sha256"],
                )
            )
            + "\n",
        )
        image = directory / "receiver-boot-page0.original.hex"
        expected_page = original[:PAGE_SIZE]
    else:
        if before["flash"][:APP_START] != original[:APP_START]:
            raise ValueError("installed BOOT differs from the approved original")
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
            raise ValueError("APPCODE programming failed; BOOT remains untouched")
        after_app = read_snapshot(proof, "boot-after-app")
        require_preserved(before, after_app, APP_START, app["page_end"])
        if after_app["flash"][APP_START : app["page_end"]] != image_data:
            raise ValueError("APPCODE readback mismatch; BOOT remains untouched")
        before = after_app
        image = directory / "receiver-boot-page0.hex"
    command = page_write_command(AVRDUDE, AVRDUDE_CONF, PORT, image)
    proof.note("receiver-boot-program-command.json", json.dumps(command, indent=2) + "\n")
    code, _, _ = proof.command(
        "receiver-boot-page0-restore" if restore else "receiver-boot-page0-write", command, 60
    )
    if code:
        raise ValueError(
            "BOOT page write/verify failed; use the separately authorized page-0 recovery procedure"
        )
    after = read_snapshot(proof, "boot-after")
    require_preserved(before, after, 0, PAGE_SIZE)
    if after["flash"][:PAGE_SIZE] != expected_page:
        raise ValueError("BOOT page readback mismatch; stop for recovery inspection")
    receipt = dict(
        origin="PHYSICAL_UPDI",
        operation="restore" if restore else "install",
        package=str(Path(args.receiver_boot_package).resolve()),
        port=PORT,
        page_hex_sha256=report["page_hex_sha256"],
        boot_sha256=sha(after["flash"][:APP_START]),
        serial=after["sernum"].hex(),
        fuses=after["fuses"].hex(),
        app_programming_verified=not restore,
        physical_restore_test="PASS" if restore else "NOT_RUN",
    )
    proof.note("receiver-boot-receipt.json", json.dumps(receipt, indent=2) + "\n")
    proof.note(
        "receiver-boot-install.log",
        "PASS: physical page readback and preservation checks; actual application boot still requires its device marker.\n",
    )
    return 0


def verify_live_receipt(proof, path):
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
    return (
        current["flash"][:PAGE_SIZE] == page
        and current["flash"][PAGE_SIZE:APP_START] == original[PAGE_SIZE:APP_START]
        and sha(current["flash"][:APP_START]) == receipt.get("boot_sha256")
    )


def prepare(proof):
    """Compile, inspect and simulate the exact proposed overwrite and restoration."""
    directory = proof.run_dir
    original = BACKUP.read_bytes()
    if len(original) != FLASH_SIZE or sha(original) != BACKUP_SHA:
        raise ValueError("Receiver backup identity/integrity mismatch")
    ssot = json.loads((ROOT / "config/lora_system.json").read_text())
    board = ssot["receiver_board"]
    if (board["bootsize"], board["codesize"], board["image_start"]) != (44, 0, APP_START):
        raise ValueError("Receiver fuse geometry differs from reviewed target")
    code, stdout, stderr = proof.command("boot-avrdude-version", [str(AVRDUDE), "--version"])
    if code or not re.search(rb"\bversion 8\.1\b", stdout + stderr):
        raise ValueError("page-erase strategy is reviewed for installed AVRDUDE 8.1 only")
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
        raise ValueError("installed programmer does not declare expected Flash/page geometry")
    app_info = {}
    reset = None
    for environment in ("receiver", "receiver_spi"):
        path = ROOT / ".pio/build" / environment / "firmware.hex"
        data = path.read_bytes()
        memory = _parse_ihex(data.decode("ascii"))
        start, end = min(memory), max(memory) + 1
        if start != APP_START or end > board["image_end_exclusive"]:
            raise ValueError(f"{environment}: image outside Receiver APPCODE")
        entry = normalize_ihex_region(data.decode("ascii"), start, start + 4)
        target = reset_target(entry, start)
        if not start <= target < end or (reset is not None and entry != reset):
            raise ValueError("applications do not share a valid reset vector")
        reset = entry
        elf = path.with_suffix(".elf")
        symbols = subprocess.check_output([str(TOOLCHAIN / "avr-nm"), str(elf)], text=True)
        if not re.search(r"^00005800\s+\w\s+__vectors$", symbols, re.MULTILINE):
            raise ValueError("ELF __vectors differs from HEX start")
        (directory / (environment + "-symbols.txt")).write_text(symbols)
        sections = subprocess.check_output(
            [str(TOOLCHAIN / "avr-objdump"), "-h", str(elf)], text=True
        )
        (directory / (environment + "-sections.txt")).write_text(sections)
        startup = subprocess.check_output(
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
            raise ValueError("Receiver startup does not contain the reviewed CPUINT initialization")
        (directory / (environment + "-startup.disassembly.txt")).write_text(startup)
        (directory / (environment + ".hex")).write_bytes(data)
        (directory / (environment + ".elf")).write_bytes(elf.read_bytes())
        app_info[environment] = dict(
            hex_sha256=sha(data),
            elf_sha256=sha(elf.read_bytes()),
            start=start,
            end=end,
            page_end=(end + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE,
            reset_bytes=entry.hex(),
            reset_target=target,
        )
    header = f"#define APP_START {APP_START}\n#define CCP_IOREG_VALUE 0xD8\n" + "".join(
        f"#define RESET_BYTE_{index} {value}\n" for index, value in enumerate(reset)
    )
    (directory / "handoff_config.h").write_text(header)
    code, _, _ = proof.command(
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
            str(ROOT / "boot/receiver_handoff_contract.c"),
        ],
    )
    if code:
        raise ValueError("installed AVR device definitions disagree with handoff contract")
    elf = directory / "receiver-handoff.elf"
    code, _, _ = proof.command(
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
            str(ROOT / "boot/receiver_handoff.S"),
            "-o",
            str(elf),
        ],
    )
    if code:
        raise ValueError("boot handoff compilation failed")
    for output_format, name in [
        ("binary", "receiver-handoff.bin"),
        ("ihex", "receiver-handoff.hex"),
    ]:
        subprocess.run(
            [str(TOOLCHAIN / "avr-objcopy"), "-O", output_format, str(elf), str(directory / name)],
            check=True,
        )
    disassembly = subprocess.check_output(
        [str(TOOLCHAIN / "avr-objdump"), "-d", str(elf)], text=True
    )
    (directory / "receiver-handoff.disassembly.txt").write_text(disassembly)
    audit = analyze(disassembly, APP_START)
    if audit["application_transfers"] != [APP_START] or audit["unresolved"]:
        raise ValueError("compiled stub has no fully resolved APPCODE transfer")
    stub = (directory / "receiver-handoff.bin").read_bytes()
    traces = {
        "matching_reset": trace_stub(stub, reset),
        "blank_application": trace_stub(stub, b"\xff" * 4),
    }
    if (
        traces["matching_reset"] != dict(application_entered=True, cpuint=0, interrupts=False)
        or traces["blank_application"]["application_entered"]
    ):
        raise ValueError("compiled boot behavior differs from required handoff")
    for index in range(4):
        wrong = bytearray(reset)
        wrong[index] ^= 1
        traces[f"wrong_reset_byte_{index}"] = trace_stub(stub, wrong)
        if traces[f"wrong_reset_byte_{index}"]["application_entered"]:
            raise ValueError("boot guard accepted an incorrect reset vector")
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
        raise ValueError("installed AVRDUDE page-write/restore simulation failed")
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
        raise ValueError("APPCODE-first/BOOT-last/recovery simulation failed")
    report = dict(
        schema_version=1,
        origin="STATIC_BUILD_AND_AVRDUDE_DRYRUN",
        avrdude_sha256=sha(AVRDUDE.read_bytes()),
        avrdude_conf_sha256=sha(AVRDUDE_CONF.read_bytes()),
        device="AVR128DA28",
        expected_serial="42032240221041150120010500000000",
        backup_sha256=BACKUP_SHA,
        bootsize=44,
        codesize=0,
        application_start=APP_START,
        application_images=app_info,
        page_size=PAGE_SIZE,
        boot_pages_written=[0],
        application_pages_to_program=list(
            range(APP_START // PAGE_SIZE, app_info["receiver_spi"]["page_end"] // PAGE_SIZE)
        ),
        application_write_range=[APP_START, app_info["receiver_spi"]["page_end"]],
        boot_write_range=[0, PAGE_SIZE],
        changed_byte_ranges=changes,
        stub_size=len(stub),
        original_page_sha256=sha(original[:PAGE_SIZE]),
        replacement_page_sha256=sha(page),
        page_hex_sha256=sha((directory / "receiver-boot-page0.hex").read_bytes()),
        restore_hex_sha256=sha((directory / "receiver-boot-page0.original.hex").read_bytes()),
        spi_padded_hex_sha256=sha((directory / "receiver-spi-full-pages.hex").read_bytes()),
        handoff_audit=audit,
        physical_programming="NOT_RUN",
        physical_restore_test="NOT_RUN",
        write_command=page_write_command(
            AVRDUDE, AVRDUDE_CONF, PORT, directory / "receiver-boot-page0.hex"
        ),
        restore_command=page_write_command(
            AVRDUDE, AVRDUDE_CONF, PORT, directory / "receiver-boot-page0.original.hex"
        ),
    )
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
