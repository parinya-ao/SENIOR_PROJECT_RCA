import importlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

inventory = importlib.import_module("tools.device_detection.usb_inventory")


def require(test, name):
    value = getattr(inventory, name, None)
    test.assertTrue(callable(value), f"usb_inventory.{name} must exist")
    return value


class Port:
    def __init__(self, device, location) -> None:
        self.device = device
        self.vid = 0x10C4
        self.pid = 0xEA60
        self.serial_number = "0001"
        self.manufacturer = "Silicon Labs"
        self.product = "CP2102 USB to UART Bridge Controller"
        self.location = location


class USBInventoryTests(unittest.TestCase):
    def test_udev_monitor_is_used_with_polling_fallback_when_unavailable(self) -> None:
        start = require(self, "start_udev_monitor")
        if start is None:
            return
        calls = []
        sentinel = object()

        def available(argv, **kwargs):
            calls.append((argv, kwargs))
            return sentinel

        self.assertIs(start(available), sentinel)
        self.assertEqual(calls[0][0][:3], ["udevadm", "monitor", "--udev"])
        self.assertIsNone(start(lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError())))

    def test_duplicate_cp2102_serials_keep_distinct_usb_paths(self) -> None:
        discover = require(self, "discover_usb_devices")
        if discover is None:
            return
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dev = root / "dev"
            by_path = dev / "serial" / "by-path"
            by_path.mkdir(parents=True)
            nodes = [dev / "ttyUSB0", dev / "ttyUSB1"]
            for node in nodes:
                node.parent.mkdir(parents=True, exist_ok=True)
                node.touch()
            links = [
                by_path / "pci-0000-usb-0:1:1.0-port0",
                by_path / "pci-0000-usb-0:4:1.0-port0",
            ]
            for link, node in zip(links, nodes):
                link.symlink_to(node)
            properties = {
                str(
                    nodes[0]
                ): "ID_VENDOR_ID=10c4\nID_MODEL_ID=ea60\nID_SERIAL_SHORT=0001\nID_PATH=pci-0000-usb-0:1:1.0\nID_USB_DRIVER=cp210x\n",
                str(
                    nodes[1]
                ): "ID_VENDOR_ID=10c4\nID_MODEL_ID=ea60\nID_SERIAL_SHORT=0001\nID_PATH=pci-0000-usb-0:4:1.0\nID_USB_DRIVER=cp210x\n",
            }

            def run(argv, **kwargs):
                if argv[:3] == ["udevadm", "info", "--query=property"]:
                    node = argv[-1].split("=", 1)[-1]
                    return subprocess.CompletedProcess(argv, 0, properties[node], "")
                if argv[:3] == ["pio", "device", "list"]:
                    return subprocess.CompletedProcess(argv, 0, "[]", "")
                return subprocess.CompletedProcess(argv, 0, "", "")

            result = discover(
                list_ports_fn=lambda **kwargs: [
                    Port(str(nodes[0]), "3-1:1.0"),
                    Port(str(nodes[1]), "3-4:1.0"),
                ],
                command_runner=run,
                by_path_dir=by_path,
            )
        self.assertEqual(len(result.devices), 2)
        self.assertEqual({d.serial_number for d in result.devices}, {"0001"})
        self.assertEqual(
            {d.usb_path for d in result.devices}, {"pci-0000-usb-0:1:1.0", "pci-0000-usb-0:4:1.0"}
        )

    def test_duplicate_symbolic_links_are_deduplicated(self) -> None:
        discover = require(self, "discover_usb_devices")
        if discover is None:
            return
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            by_path = root / "serial" / "by-path"
            by_path.mkdir(parents=True)
            node = root / "ttyUSB2"
            node.touch()
            (by_path / "usb-link-a").symlink_to(node)
            (by_path / "usb-link-b").symlink_to(node)
            props = "ID_VENDOR_ID=10c4\nID_MODEL_ID=ea60\nID_PATH=usb-1:2\n"

            def run(argv, **kwargs):
                if argv[0] == "udevadm":
                    return subprocess.CompletedProcess(argv, 0, props, "")
                return subprocess.CompletedProcess(argv, 0, "", "")

            result = discover(
                list_ports_fn=lambda **kwargs: [
                    Port(str(node), "1-2:1.0"),
                    Port(str(by_path / "usb-link-a"), "1-2:1.0"),
                ],
                command_runner=run,
                by_path_dir=by_path,
            )
        self.assertEqual(len(result.devices), 1)
        self.assertEqual(len(result.devices[0].usb_by_path), 2)

    def test_current_device_metadata_includes_driver_and_real_node(self) -> None:
        discover = require(self, "discover_usb_devices")
        if discover is None:
            return
        with tempfile.TemporaryDirectory() as temp:
            node = Path(temp) / "ttyUSB3"
            node.touch()

            def run(argv, **kwargs):
                if argv[0] == "udevadm":
                    return subprocess.CompletedProcess(
                        argv,
                        0,
                        "ID_VENDOR_ID=10c4\nID_MODEL_ID=ea60\nID_PATH=usb-2:1\nID_USB_DRIVER=cp210x\n",
                        "",
                    )
                return subprocess.CompletedProcess(argv, 0, "", "")

            result = discover(
                list_ports_fn=lambda **kwargs: [Port(str(node), "2-1:1.0")],
                command_runner=run,
                by_path_dir=Path(temp) / "none",
            )
        self.assertEqual(result.devices[0].real_device_path, os.path.realpath(node))
        self.assertEqual(result.devices[0].driver, "cp210x")
        self.assertTrue(result.devices[0].present)

    def test_usb_instance_uses_live_sysfs_device_number(self) -> None:
        discover = require(self, "discover_usb_devices")
        if discover is None:
            return
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            node = root / "ttyUSB4"
            node.touch()
            sysfs = root / "sysfs" / "3-4"
            sysfs.mkdir(parents=True)
            (sysfs / "busnum").write_text("3\n")
            (sysfs / "devnum").write_text("27\n")

            def run(argv, **kwargs):
                if argv[0] == "udevadm":
                    return subprocess.CompletedProcess(
                        argv,
                        0,
                        "ID_VENDOR_ID=10c4\nID_MODEL_ID=ea60\nID_PATH=usb-0:4:1.0\n"
                        "DEVPATH=/devices/pci/usb3/3-4/3-4:1.0/ttyUSB4\n",
                        "",
                    )
                return subprocess.CompletedProcess(argv, 0, "", "")

            result = discover(
                list_ports_fn=lambda **kwargs: [Port(str(node), "3-4:1.0")],
                command_runner=run,
                by_path_dir=root / "none",
                sysfs_usb_dir=root / "sysfs",
            )
        self.assertTrue(result.devices[0].usb_instance.startswith("3:27:"))


if __name__ == "__main__":
    unittest.main()
