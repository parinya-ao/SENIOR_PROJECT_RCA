"""One-shot acquisition using existing UPDI byte-read and serial trace machinery."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
import serial
from third_party.upditerm import upditerm
from tools.rca.gate1_live import Gate1Audit, instrument, read_data_space_byte

role = sys.argv[1]
out = Path(sys.argv[2]) / role
out.mkdir()
expected = json.loads((ROOT / "config/current_hardware.json").read_text())[role]
port = expected["port_path"]
assert Path(port).resolve(strict=True).is_char_device()
owners = subprocess.run(["fuser", port], capture_output=True, text=True, check=False)
assert owners.returncode == 1, f"Port ownership check refused: {owners}"
audit = Gate1Audit(out)
audit.device_path = port
instrument(upditerm, audit, serial)
record = dict(role=role, path=port, utc_start=datetime.now(timezone.utc).isoformat(),
              electrical_measurements="NOT_MEASURED", cpu_reset_requested=False,
              nvm_write_requested=False, rf_tx_requested=False)
link = None
try:
    link = upditerm.UPDI(port, 38400)
    record["sib"] = link.sib()
    def read(address, count):
        return bytes(read_data_space_byte(link, address + i) for i in range(count))
    record["signature"] = read(0x1100, 3).hex()
    record["mcu_serial"] = read(0x1110, 16).hex()
    record["identity_match"] = (record["signature"] == "1e970a" and
                                record["mcu_serial"] == expected["device_serial_hex"])
    assert record["identity_match"], "Wrong MCU: stopping before further reads"
    fuses = read(0x1050, 16)
    record["fuses_hex"] = fuses.hex()
    record["fuses"] = dict(BODCFG=fuses[1], CODESIZE=fuses[7], BOOTSIZE=fuses[8])
    record["fuses_match"] = fuses.hex() == expected["fuses_hex"]
    record["reset_flags"] = dict(RSTFR=read(0x40, 1)[0], GPIOR0=read(0x1c, 1)[0])
    record["result"] = "PASS" if record["fuses_match"] else "FAIL"
    assert record["fuses_match"], "Fuse mismatch"
except BaseException as error:
    record.update(result="FAIL", error=repr(error))
    raise
finally:
    if link is not None:
        link.__del__()
        link.ser.dev.close()
        link.ser = None
    record["cpu_resets_requested_by_audit"] = audit.reset_count
    record["utc_end"] = datetime.now(timezone.utc).isoformat()
    (out / "readback.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
