import importlib
import unittest

evidence = importlib.import_module("tools.device_detection.evidence")
identity = importlib.import_module("tools.device_detection.firmware_identity")
detector = importlib.import_module("tools.device_detection.role_detector")


def require(test, module, name):
    value = getattr(module, name, None)
    test.assertIsNotNone(value, f"{module.__name__}.{name} must exist")
    return value


def device(node, usb_path):
    cls = getattr(evidence, "USBDevice", None)
    if cls is None:
        return None
    return cls(
        device_node=node,
        real_device_path=node,
        usb_path=usb_path,
        usb_by_path=(f"/dev/serial/by-path/{usb_path}-port0",),
        vid="10c4",
        pid="ea60",
        serial_number="0001",
        present=True,
    )


def probe(role, build):
    identity_cls = getattr(identity, "FirmwareIdentity", None)
    probe_cls = getattr(evidence, "ProbeEvidence", None)
    if identity_cls is None or probe_cls is None:
        return None
    marker = identity_cls(role=role, build_id=build, protocol=1, crc8=0)
    return probe_cls(firmware_identity=marker, mcu_identity="AVR128DA28")


class RoleDetectorTests(unittest.TestCase):
    def test_sender_ttyusb0_receiver_ttyusb1_is_pass(self):
        classify = require(self, detector, "classify_devices")
        if classify is None or device("/dev/ttyUSB0", "usb-0:4:1.0") is None:
            return
        result = classify(
            [device("/dev/ttyUSB0", "usb-0:4:1.0"), device("/dev/ttyUSB1", "usb-0:1:1.0")],
            {
                "/dev/ttyUSB0": probe("SENDER", "build-a"),
                "/dev/ttyUSB1": probe("RECEIVER", "build-b"),
            },
        )
        self.assertEqual(result.status, "PASS")
        self.assertEqual({d.role for d in result.devices}, {"SENDER", "RECEIVER"})

    def test_sender_ttyusb1_receiver_ttyusb0_is_pass(self):
        classify = require(self, detector, "classify_devices")
        if classify is None or device("/dev/ttyUSB0", "usb-0:4:1.0") is None:
            return
        result = classify(
            [device("/dev/ttyUSB0", "usb-0:1:1.0"), device("/dev/ttyUSB1", "usb-0:4:1.0")],
            {
                "/dev/ttyUSB0": probe("RECEIVER", "build-r"),
                "/dev/ttyUSB1": probe("SENDER", "build-s"),
            },
        )
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.sender.port, "/dev/ttyUSB1")
        self.assertEqual(result.receiver.port, "/dev/ttyUSB0")

    def test_one_unidentified_adapter_stays_unknown(self):
        classify = require(self, detector, "classify_devices")
        if classify is None or device("/dev/ttyUSB0", "usb-0:1:1.0") is None:
            return
        result = classify([device("/dev/ttyUSB0", "usb-0:1:1.0")])
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.devices[0].identity_status, "UNKNOWN")

    def test_identical_serial_numbers_do_not_merge_or_assign_roles(self):
        classify = require(self, detector, "classify_devices")
        if classify is None or device("/dev/ttyUSB0", "usb-0:1:1.0") is None:
            return
        result = classify(
            [device("/dev/ttyUSB0", "usb-0:1:1.0"), device("/dev/ttyUSB1", "usb-0:4:1.0")]
        )
        self.assertEqual(len(result.devices), 2)
        self.assertTrue(all(d.identity_status == "UNKNOWN" for d in result.devices))

    def test_two_sender_claims_are_conflict(self):
        classify = require(self, detector, "classify_devices")
        if classify is None or device("/dev/ttyUSB0", "usb-0:1:1.0") is None:
            return
        result = classify(
            [device("/dev/ttyUSB0", "usb-0:1:1.0"), device("/dev/ttyUSB1", "usb-0:4:1.0")],
            {"/dev/ttyUSB0": probe("SENDER", "one"), "/dev/ttyUSB1": probe("SENDER", "two")},
        )
        self.assertEqual(result.status, "CONFLICT")

    def test_conflicting_independent_role_probes_are_ambiguous(self):
        classify = require(self, detector, "classify_devices")
        probe_cls = require(self, evidence, "ProbeEvidence")
        identity_cls = require(self, identity, "FirmwareIdentity")
        if (
            any(x is None for x in (classify, probe_cls, identity_cls))
            or device("/dev/ttyUSB0", "usb-0:1:1.0") is None
        ):
            return
        result = classify(
            [device("/dev/ttyUSB0", "usb-0:1:1.0")],
            {
                "/dev/ttyUSB0": probe_cls(
                    firmware_identity=identity_cls("SENDER", "sender", 1, 0x11),
                    fingerprint_identity=identity_cls(
                        "RECEIVER", "receiver", 0, None, "flash-fingerprint"
                    ),
                )
            },
        )
        self.assertEqual(result.status, "AMBIGUOUS")
        self.assertEqual(result.devices[0].identity_status, "AMBIGUOUS")

    def test_mcu_identity_does_not_determine_firmware_role(self):
        classify = require(self, detector, "classify_devices")
        probe_cls = require(self, evidence, "ProbeEvidence")
        if classify is None or probe_cls is None or device("/dev/ttyUSB0", "usb-0:1:1.0") is None:
            return
        result = classify(
            [device("/dev/ttyUSB0", "usb-0:1:1.0")],
            {"/dev/ttyUSB0": probe_cls(mcu_identity="AVR128DA28")},
        )
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.devices[0].mcu, "AVR128DA28")

    def test_busy_port_is_inaccessible_and_updi_failure_is_not_receiver(self):
        classify = require(self, detector, "classify_devices")
        probe_cls = require(self, evidence, "ProbeEvidence")
        if classify is None or probe_cls is None or device("/dev/ttyUSB0", "usb-0:1:1.0") is None:
            return
        busy = classify(
            [device("/dev/ttyUSB0", "usb-0:1:1.0")],
            {"/dev/ttyUSB0": probe_cls(access_status="INACCESSIBLE")},
        )
        failed = classify(
            [device("/dev/ttyUSB0", "usb-0:1:1.0")],
            {"/dev/ttyUSB0": probe_cls(access_status="PROBE_FAILED")},
        )
        self.assertEqual(busy.devices[0].identity_status, "INACCESSIBLE")
        self.assertEqual(failed.devices[0].identity_status, "PROBE_FAILED")
        self.assertNotEqual(failed.devices[0].role, "RECEIVER")

    def test_live_firmware_role_overrides_stale_path_hint(self):
        classify = require(self, detector, "classify_devices")
        if classify is None or device("/dev/ttyUSB0", "usb-0:1:1.0") is None:
            return
        result = classify(
            [device("/dev/ttyUSB0", "usb-0:1:1.0")],
            {"/dev/ttyUSB0": probe("RECEIVER", "current")},
            registry={"usb-0:1:1.0": "SENDER"},
        )
        self.assertEqual(result.devices[0].role, "RECEIVER")
        self.assertEqual(result.devices[0].identity_status, "VERIFIED_RECEIVER")
        self.assertTrue(any("historical" in x.lower() for x in result.devices[0].warnings))

    def test_enrollment_requires_matching_current_physical_identity(self):
        classify = require(self, detector, "classify_devices")
        probe_cls = require(self, evidence, "ProbeEvidence")
        if classify is None or probe_cls is None or device("/dev/ttyUSB0", "usb-0:1:1.0") is None:
            return
        enrolled = {"usb-0:1:1.0": {"role": "SENDER", "physical_id": "chip-abc"}}
        unverified = classify([device("/dev/ttyUSB0", "usb-0:1:1.0")], registry=enrolled)
        verified = classify(
            [device("/dev/ttyUSB0", "usb-0:1:1.0")],
            {"/dev/ttyUSB0": probe_cls(physical_id="chip-abc")},
            registry=enrolled,
        )
        self.assertEqual(unverified.devices[0].identity_status, "UNKNOWN")
        self.assertEqual(verified.devices[0].role, "SENDER")
        self.assertEqual(verified.devices[0].identity_status, "VERIFIED_SENDER")
        self.assertEqual(verified.devices[0].evidence_type, "verified_enrollment")

    def test_absent_inventory_is_missing_not_a_sender_guess(self):
        classify = require(self, detector, "classify_devices")
        if classify is None:
            return
        result = classify([])
        self.assertEqual(result.status, "MISSING")
        self.assertIsNone(result.sender)
        self.assertIsNone(result.receiver)


if __name__ == "__main__":
    unittest.main()
