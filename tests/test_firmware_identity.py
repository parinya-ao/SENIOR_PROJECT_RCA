import importlib
import unittest


identity = importlib.import_module("tools.device_detection.firmware_identity")


def require(test, name):
    value = getattr(identity, name, None)
    test.assertIsNotNone(value, f"firmware_identity.{name} must exist")
    return value


def crc8(data):
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = ((value << 1) ^ (0x07 if value & 0x80 else 0)) & 0xFF
    return value


def marker(role="SENDER", build="sender", date="Nov  6 2026", time="05:00:00"):
    source = f"{role}|V1|{build}|{date}|{time}".encode("ascii")
    checksum = crc8(source)
    return f"[{role}] ID V1 {build} {date} {time} CRC={checksum:02X}\r\n".encode()


def ihex_record(address, record_type, data=b""):
    body = bytes([len(data), address >> 8, address & 0xFF, record_type]) + data
    check = (-sum(body)) & 0xFF
    return ":" + (body + bytes([check])).hex().upper()


class FirmwareIdentityTests(unittest.TestCase):
    def test_missing_marker_is_not_a_role(self):
        parse = require(self, "parse_identity_stream")
        if parse is None:
            return
        self.assertEqual(parse(b"ordinary debug text\r\n").status, "NONE")

    def test_valid_sender_and_receiver_markers_verify_crc_and_role(self):
        parse = require(self, "parse_identity_stream")
        if parse is None:
            return
        sender = parse(marker("SENDER", "sender_hello"))
        receiver = parse(marker("RECEIVER", "receiver"))
        self.assertEqual(sender.status, "VALID")
        self.assertEqual(sender.identity.role, "SENDER")
        self.assertEqual(receiver.identity.role, "RECEIVER")

    def test_existing_updi_boot_markers_map_gateway_to_sender(self):
        parse = require(self, "parse_identity_stream")
        if parse is None:
            return
        stream = (
            b"[GATEWAY] BOOT sender_hello Nov  6 2026 05:00:00\r\n"
            b"[RECEIVER] BOOT receiver Nov  6 2026 05:01:00\r\n"
        )
        result = parse(stream)
        self.assertEqual(result.status, "AMBIGUOUS")
        self.assertEqual({item.role for item in result.identities}, {"SENDER", "RECEIVER"})

    def test_malformed_partial_and_bad_crc_markers_are_rejected(self):
        parse = require(self, "parse_identity_stream")
        if parse is None:
            return
        good = marker()
        bad_crc = good.replace(good[-4:-2], b"00")
        self.assertEqual(parse(b"[SENDER] ID V1 sender" ).status, "MALFORMED")
        self.assertEqual(parse(bad_crc).status, "MALFORMED")
        self.assertEqual(parse(good[:-2]).status, "MALFORMED")

    def test_conflicting_markers_in_one_stream_are_ambiguous(self):
        parse = require(self, "parse_identity_stream")
        if parse is None:
            return
        self.assertEqual(parse(marker("SENDER", "sender") + marker("RECEIVER", "receiver")).status,
                         "AMBIGUOUS")

    def test_flash_readback_unavailable_returns_unknown(self):
        match = require(self, "match_flash_fingerprint")
        if match is None:
            return
        result = match(None, [], flash_size=32, app_start=4, app_end=24)
        self.assertEqual(result.status, "UNAVAILABLE")

    def test_sparse_hex_and_erased_tail_match_only_application_region(self):
        match = require(self, "match_flash_fingerprint")
        reference_cls = require(self, "FirmwareReference")
        if match is None or reference_cls is None:
            return
        hex_text = "\n".join([
            ihex_record(0, 4, b"\x00\x00"),
            ihex_record(8, 0, b"ABC"),
            ihex_record(0, 1),
        ]) + "\n"
        actual = bytearray([0x00] * 32)
        actual[4:24] = b"\xff" * 20
        actual[8:11] = b"ABC"
        actual[24:28] = b"BOOT"
        reference = reference_cls(role="SENDER", build_id="sender-x", ihex=hex_text,
                                 flash_size=32, app_start=4, app_end=24)
        result = match(bytes(actual), [reference], flash_size=32,
                       app_start=4, app_end=24)
        self.assertEqual(result.status, "MATCH")
        self.assertEqual(result.identity.role, "SENDER")

    def test_identical_fingerprints_with_different_roles_are_ambiguous(self):
        match = require(self, "match_flash_fingerprint")
        reference_cls = require(self, "FirmwareReference")
        if match is None or reference_cls is None:
            return
        ihex = "\n".join([ihex_record(4, 0, b"same"), ihex_record(0, 1)]) + "\n"
        refs = [reference_cls("SENDER", "same-a", ihex, 16, 4, 12),
                reference_cls("RECEIVER", "same-b", ihex, 16, 4, 12)]
        actual = b"\xff" * 4 + b"same" + b"\xff" * 4 + b"\x00" * 4
        result = match(actual, refs, flash_size=16, app_start=4, app_end=12)
        self.assertEqual(result.status, "AMBIGUOUS")

    def test_partial_readback_is_rejected(self):
        match = require(self, "match_flash_fingerprint")
        if match is None:
            return
        result = match(b"\xff" * 12, [], flash_size=32, app_start=4, app_end=24)
        self.assertEqual(result.status, "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
