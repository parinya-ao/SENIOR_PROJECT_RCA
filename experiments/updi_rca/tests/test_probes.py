import json
from types import SimpleNamespace

import pytest

from updi_rca import probes
from updi_rca.identity import AdapterIdentity, BoardIdentity, ConnectionIdentity
from updi_rca.probes import run_control_read, run_data_read, run_sib_probe


def connection(by_path="adapter-path", tty="/dev/ttyUSB9"):
    return ConnectionIdentity(
        AdapterIdentity("10c4", "ea60", "0001", "usb-path-a", "/sys/usb/a",
                        current_tty=tty, by_path=by_path),
        BoardIdentity(),
    )


class FakeSerial:
    def __init__(self, port=None, baudrate=38400, *, responses=None, corrupt_echo=False, **kwargs):
        self.kwargs = {"port": port, "baudrate": baudrate, **kwargs}
        self.responses = responses or {}
        self.corrupt_echo = corrupt_echo
        self.writes = []
        self.pending = bytearray()
        self.baudrate = baudrate
        self.closed = False

    def write(self, data):
        data = bytes(data)
        self.writes.append((self.baudrate, data))
        echo = bytes([data[0] ^ 0x01]) + data[1:] if self.corrupt_echo else data
        self.pending.extend(echo)
        self.pending.extend(self.responses.get(data, b""))
        return len(data)

    def read(self, size):
        out = bytes(self.pending[:size])
        del self.pending[:size]
        return out

    def close(self):
        self.closed = True


def install_serial(monkeypatch, fake, adapter=None):
    adapter = adapter or connection().adapter
    monkeypatch.setattr(probes, "discover_serial_ports", lambda: [adapter])
    def open_fake(*args, **kwargs):
        fake.kwargs = kwargs
        return fake
    monkeypatch.setattr(probes, "serial", SimpleNamespace(
        Serial=open_fake, PARITY_EVEN="E", STOPBITS_TWO=2,
        SerialException=OSError,
    ), raising=False)


def test_sib_probe_uses_only_break_and_read_command(tmp_path, monkeypatch):
    sib = b"AVR128DA28 test SIB".ljust(32, b"\0")
    fake = FakeSerial(responses={b"\x55\xe6": sib})
    install_serial(monkeypatch, fake)

    result = run_sib_probe(connection(), 38400, tmp_path / "sib.json")

    assert result.success
    assert fake.writes == [(300, b"\0"), (300, b"\0"), (38400, b"\x55\xe6")]
    assert fake.closed
    saved = json.loads((tmp_path / "sib.json").read_text())
    assert saved["write_policy"] == "no STCS, STS, programming key, reset, or NVM write"
    assert saved["values"]["SIB"] == sib.hex()


def test_control_probe_uses_only_ldcs_reads(tmp_path, monkeypatch):
    responses = {bytes((0x55, 0x80 | address)): b"\x00" for address in (0, 1, 2, 3, 7, 8, 9, 10, 11, 12, 4, 5)}
    fake = FakeSerial(responses=responses)
    install_serial(monkeypatch, fake)

    result = run_control_read(connection(), 38400, tmp_path / "control.json")

    assert result.success
    assert all(frame == b"\x00" or (frame[0] == 0x55 and frame[1] & 0xF0 == 0x80)
               for _, frame in fake.writes)
    assert fake.closed


def test_data_probe_uses_stable_by_path_and_keeps_target_failure_stage(tmp_path, monkeypatch):
    fake = FakeSerial()
    install_serial(monkeypatch, fake)

    result = run_data_read(connection(), 0x1E, 38400, tmp_path / "raw.json")

    assert result.stage == "ACC_DATA_RESPONSE"
    assert result.echo == bytes.fromhex("000055001e")
    assert fake.kwargs["port"].endswith("/adapter-path")
    assert "/dev/ttyUSB9" not in fake.kwargs["port"]
    assert fake.closed


def test_echo_failure_and_missing_target_response_are_separate(tmp_path, monkeypatch):
    broken_echo = FakeSerial(corrupt_echo=True)
    install_serial(monkeypatch, broken_echo)
    echo_result = run_control_read(connection(), 38400, tmp_path / "echo.json")
    assert echo_result.stage == "LOCAL_ECHO"

    no_response = FakeSerial()
    install_serial(monkeypatch, no_response)
    response_result = run_control_read(connection(), 38400, tmp_path / "response.json")
    assert response_result.stage == "UPDI_CONTROL_RESPONSE"
    assert response_result.echo


def test_probe_refuses_to_open_when_stable_by_path_is_missing(tmp_path, monkeypatch):
    fake = FakeSerial()
    adapter = connection(by_path=None).adapter
    install_serial(monkeypatch, fake, adapter)

    with pytest.raises(ValueError, match="by-path"):
        run_sib_probe(connection(by_path=None), 38400, tmp_path / "raw.json")

    assert not fake.writes
    assert not fake.closed


def test_probe_raw_evidence_survives_missing_response(tmp_path, monkeypatch):
    fake = FakeSerial()
    install_serial(monkeypatch, fake)
    path = tmp_path / "timeout.json"

    result = run_data_read(connection(), 0x1E, 38400, path)

    assert result.stage == "ACC_DATA_RESPONSE"
    assert path.exists()
    assert result.raw_sha256
    assert "ACC_DATA_RESPONSE" in path.read_text()
