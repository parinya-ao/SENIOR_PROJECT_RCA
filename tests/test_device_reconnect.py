from __future__ import annotations

import importlib
import unittest
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

if TYPE_CHECKING:
    from types import ModuleType

evidence = importlib.import_module("tools.device_detection.evidence")
identity = importlib.import_module("tools.device_detection.firmware_identity")
detector = importlib.import_module("tools.device_detection.role_detector")
Json = Any


def require(test: unittest.TestCase, module: ModuleType, name: str) -> Json:
    value = getattr(module, name, None)
    test.assertIsNotNone(value, f"{module.__name__}.{name} must exist")
    return value


def make_device(port: str, path: str) -> Json:
    cls = getattr(evidence, "USBDevice", None)
    if cls is None:
        return None
    return cls(
        device_node=port,
        real_device_path=port,
        usb_path=path,
        usb_by_path=(f"/dev/serial/by-path/{path}-port0",),
        present=True,
    )


def make_probe(role: str) -> Json:
    marker_cls = getattr(identity, "FirmwareIdentity", None)
    probe_cls = getattr(evidence, "ProbeEvidence", None)
    if not marker_cls or not probe_cls:
        return None
    return probe_cls(firmware_identity=marker_cls(role, "build-1", 1, 0))


class DeviceReconnectTests(unittest.TestCase):
    def test_sender_reconnects_with_new_tty_and_fresh_marker(self) -> None:
        classify = require(self, detector, "classify_devices")
        diff = require(self, detector, "diff_device_presence")
        if classify is None or diff is None or make_device("/dev/ttyUSB1", "usb-4") is None:
            return
        old = classify(
            [make_device("/dev/ttyUSB1", "usb-4")], {"/dev/ttyUSB1": make_probe("SENDER")}
        )
        disconnected = classify([])
        events = diff(old.devices, disconnected.devices)
        self.assertEqual(events[0]["event"], "disconnected")
        self.assertEqual(events[0]["identity_status"], "MISSING")
        reconnected = classify(
            [make_device("/dev/ttyUSB2", "usb-4")], {"/dev/ttyUSB2": make_probe("SENDER")}
        )
        events = diff(disconnected.devices, reconnected.devices)
        self.assertIn(events[0]["event"], {"connected", "updated"})
        self.assertEqual(reconnected.devices[0].identity_status, "VERIFIED_SENDER")
        self.assertEqual(reconnected.devices[0].port, "/dev/ttyUSB2")

    def test_receiver_disconnect_and_all_devices_disconnect_are_missing(self) -> None:
        classify = require(self, detector, "classify_devices")
        if classify is None or make_device("/dev/ttyUSB0", "usb-1") is None:
            return
        both = classify(
            [make_device("/dev/ttyUSB0", "usb-1"), make_device("/dev/ttyUSB1", "usb-4")],
            {"/dev/ttyUSB0": make_probe("RECEIVER"), "/dev/ttyUSB1": make_probe("SENDER")},
        )
        one = classify(
            [make_device("/dev/ttyUSB1", "usb-4")], {"/dev/ttyUSB1": make_probe("SENDER")}
        )
        none = classify([])
        removed_receiver = diff = require(self, detector, "diff_device_presence")
        if removed_receiver is None:
            return
        events = diff(both.devices, one.devices)
        self.assertTrue(
            any(e["event"] == "disconnected" and e["identity_status"] == "MISSING" for e in events)
        )
        self.assertEqual(len(diff(both.devices, none.devices)), 2)
        self.assertEqual(one.status, "PARTIAL")
        self.assertEqual(one.missing_roles, ("RECEIVER",))
        self.assertEqual(none.status, "MISSING")
        self.assertEqual(none.devices, ())

    def test_path_change_does_not_carry_cached_role_without_new_identity(self) -> None:
        classify = require(self, detector, "classify_devices")
        if classify is None or make_device("/dev/ttyUSB2", "usb-new") is None:
            return
        result = classify([make_device("/dev/ttyUSB2", "usb-new")], registry={"usb-old": "SENDER"})
        self.assertEqual(result.devices[0].role, "UNKNOWN")
        self.assertEqual(result.devices[0].identity_status, "UNKNOWN")

    def test_reenumerated_usb_instance_with_same_tty_gets_fresh_identity(self) -> None:
        cli = importlib.import_module("tools.detect_devices")
        inventory_cls = require(
            self, importlib.import_module("tools.device_detection.usb_inventory"), "InventoryResult"
        )
        probe_cls = require(self, evidence, "ProbeEvidence")
        if (
            inventory_cls is None
            or probe_cls is None
            or make_device("/dev/ttyUSB0", "usb-4") is None
        ):
            return
        first = make_device("/dev/ttyUSB0", "usb-4")
        second = importlib.import_module("dataclasses").replace(first, usb_instance="3:19")
        first = importlib.import_module("dataclasses").replace(first, usb_instance="3:18")
        inventories = iter([inventory_cls((first,), (), {}), inventory_cls((second,), (), {})])
        args = cli.build_parser().parse_args(["--scan", "--probe-firmware", "--hardware-safe"])
        cache: dict[str, Json] = {}
        with patch.object(
            cli, "_probe_device", side_effect=[make_probe("SENDER"), make_probe("RECEIVER")]
        ) as call:
            old, _ = cli._scan(args, inventory_fn=lambda: next(inventories), probe_cache=cache)
            new, _ = cli._scan(args, inventory_fn=lambda: next(inventories), probe_cache=cache)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(old.devices[0].role, "SENDER")
        self.assertEqual(new.devices[0].role, "RECEIVER")
        self.assertEqual(new.devices[0].identity_status, "VERIFIED_RECEIVER")


if __name__ == "__main__":
    unittest.main()
