"""HOST SIMULATION: actual firmware roles; only MCU/radio I/O is replaced."""

import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_LIB = ROOT / "stable_lib"


class Board:
    def __init__(self, binary: str | Path) -> None:
        self.process = subprocess.Popen(
            [str(binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if (
            self.process.stdin is None
            or self.process.stdout is None
            or self.process.stderr is None
        ):
            msg = "board process streams were not opened"
            raise RuntimeError(msg)
        self.stdin = self.process.stdin
        self.stdout = self.process.stdout
        self.stderr = self.process.stderr
        self.timer = threading.Timer(10, self.process.kill)
        self.timer.start()
        self.transcript: list[str] = []
        try:
            self.initial = self.read()
        except BaseException:
            self.close()
            raise

    def read(self) -> list[str]:
        lines: list[str] = []
        while True:
            line = self.stdout.readline()
            if not line:
                raise AssertionError("Native board stopped: " + self.stderr.read())
            line = line.rstrip()
            self.transcript.append(line)
            if line == "HOST_READY":
                return lines
            lines.append(line)

    def command(self, command: str) -> list[str]:
        self.stdin.write(command + "\n")
        self.stdin.flush()
        return self.read()

    def status(self) -> dict[str, Any]:
        return next(
            json.loads(line.removeprefix("HOST_STATUS "))
            for line in self.command("STATUS")
            if line.startswith("HOST_STATUS ")
        )

    def close(self) -> None:
        self.stdin.close()
        self.process.wait(timeout=5)
        self.timer.cancel()
        self.stdout.close()
        self.stderr.close()


def frames(lines: Iterable[str]) -> list[bytes]:
    return [
        bytes.fromhex(line.removeprefix("HOST_FRAME "))
        for line in lines
        if line.startswith("HOST_FRAME ")
    ]


class MvpRoundtripTests(unittest.TestCase):
    directory: tempfile.TemporaryDirectory[str]
    binaries: dict[str, Path]
    task_host_warning: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory(prefix="lora-mvp-host-")
        cls.binaries = {}
        compiler = shutil.which("g++") or shutil.which("clang++")
        if compiler is None:
            raise RuntimeError("C++ host compiler required for firmware role simulation")
        for role in ("sender", "receiver"):
            binary = Path(cls.directory.name) / role
            ssot_object = Path(cls.directory.name) / (role + "_ssot.o")
            role_defines = (
                ["-DHELLO_TEST_MODE=1", "-DHELLO_RAM_ONLY_TEST=1", "-DLORA_ROLE_SENDER=1"]
                if role == "sender"
                else ["-DLORA_ROLE_RECEIVER=1"]
            )
            c_result = subprocess.run(
                [
                    "g++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Wshadow",
                    "-Wconversion",
                    "-Wstrict-prototypes",
                    "-Wmissing-prototypes",
                    "-Werror",
                    *role_defines,
                    "-I" + str(ROOT / "stable_lib/ssot"),
                    "-I" + str(ROOT / "include"),
                    "-c",
                    str(ROOT / "stable_lib/ssot/ssot_codec.cpp"),
                    "-o",
                    str(ssot_object),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            check=False,
            )
            if c_result.returncode:
                raise AssertionError(c_result.stdout + c_result.stderr)
            command = [
                compiler,
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Wno-implicit-fallthrough",
                "-Wno-unused-but-set-variable",
                "-D_Bool=bool",
                '-DLORA_BUILD_ID="HOST_SIMULATION"',
                "-I" + str(ROOT / "tests/mvp_stub"),
                "-I" + str(ROOT / "tests/avr_stub"),
                "-I" + str(ROOT / "tests/radio_stub"),
                "-I" + str(ROOT / "stable_lib/shared"),
                "-I" + str(ROOT / "stable_lib/ssot"),
                "-I" + str(ROOT / "include"),
                "-I" + str(ROOT / "src"),
                "-I" + str(ROOT / "stable_lib/gateway_app"),
                "-I" + str(ROOT / "stable_lib/reliable_app"),
                "-I" + str(ROOT / "stable_lib/lora"),
                "-I" + str(ROOT / "stable_lib/updi_uart"),
                "-I" + str(PROJECT_LIB / "task"),
                "-I" + str(PROJECT_LIB / "sleep"),
                "-I" + str(PROJECT_LIB / "time-utils"),
                "-I" + str(PROJECT_LIB / "iw_core"),
                "-I" + str(PROJECT_LIB / "iw_tracker_radio_protocol"),
                *role_defines,
                str(ROOT / "tests/mvp_board.cpp"),
                str(ROOT / "src/features/diagnostics/radio_diagnostics.cpp"),
                str(ROOT / "src/features/radio_link/radio_link.cpp"),
                str(ssot_object),
                str(ROOT / "stable_lib/ssot/ssot_session.cpp"),
                str(ROOT / "stable_lib/ssot/ssot_control_input.cpp"),
                str(Path(cls.directory.name) / "task.o"),
                str(PROJECT_LIB / "iw_tracker_radio_protocol/tracker_radio_codec.cpp"),
                str(PROJECT_LIB / "iw_core/byte_codec.cpp"),
                "-o",
                str(binary),
            ]
            if role == "sender":
                flags = command[: command.index(str(ROOT / "tests/mvp_board.cpp"))]
                dependency = subprocess.run(
                    [
                        *flags,
                        "-c",
                        str(PROJECT_LIB / "task/task.cpp"),
                        "-o",
                        str(Path(cls.directory.name) / "task.o"),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                check=False,
                )
                if dependency.returncode:
                    raise AssertionError(dependency.stdout + dependency.stderr)
                cls.task_host_warning = dependency.stderr
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=30, check=False
            )
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            cls.binaries[role] = binary

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def board(self, role: str) -> Board:
        board = Board(self.binaries[role])
        self.addCleanup(board.close)
        output = "\n".join(board.initial)
        self.assertTrue("RADIO_INIT_OK" in output or "RX_READY" in output)
        return board

    def start(self, sender: Board) -> bytes:
        result = frames(sender.initial)
        self.assertEqual(len(result), 1)
        frame = result[0]
        self.assertEqual(frame[:2], bytes.fromhex("0100"))
        self.assertNotEqual(frame[2:4], b"\x00\x00")
        self.assertEqual(frame[4:6], bytes.fromhex("0801"))
        self.assertEqual(frame[6:], b"hello world")
        return frame

    def test_sender_receiver_complete_data_ack_and_second_cycle(self) -> None:
        receiver = self.board("receiver")
        sender = self.board("sender")
        data = self.start(sender)
        result = receiver.command("RX " + data.hex())
        self.assertIn("DATA_VALIDATED", "\n".join(result))
        self.assertIn("ACK_TX_BEGIN", "\n".join(result))
        ack = frames(result)[0]
        expected_ack = bytes.fromhex("0001") + data[2:4] + bytes.fromhex("0301")
        self.assertEqual(ack, expected_ack)
        result = sender.command("RX " + ack.hex())
        self.assertIn("ACK_ACCEPTED", "\n".join(result))
        self.assertEqual(sender.status()["state"], "COMPLETE")

        second = frames(sender.command("S"))
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0][:2], bytes.fromhex("0100"))
        self.assertEqual(second[0][2:4], data[2:4])
        self.assertEqual(second[0][4:6], bytes.fromhex("0802"))
        self.assertEqual(second[0][6:], b"hello world")
        result = receiver.command("RX " + second[0].hex())
        self.assertIn("DATA_VALIDATED", "\n".join(result))
        expected_ack = bytes.fromhex("0001") + data[2:4] + bytes.fromhex("0302")
        self.assertEqual(frames(result), [expected_ack])
        result = sender.command("RX " + frames(result)[0].hex())
        self.assertIn("ACK_ACCEPTED", "\n".join(result))
        print("HOST_SIMULATION DATA_ACK=PASS CYCLES=2 PAYLOAD=11")

    def test_wrong_payload_gets_nack_and_sender_retries(self) -> None:
        receiver = self.board("receiver")
        sender = self.board("sender")
        data = self.start(sender)
        bad = bytearray(data)
        bad[-1] ^= 1
        result = receiver.command("RX " + bad.hex())
        self.assertIn("NACK_TX_BEGIN", "\n".join(result))
        nack = frames(result)[0]
        expected_nack = bytes.fromhex("0001") + data[2:4] + bytes.fromhex("0901")
        self.assertEqual(nack, expected_nack)
        retry = frames(sender.command("RX " + nack.hex()))
        self.assertEqual(retry, [data])

    def test_wrong_session_data_is_discarded_without_ack(self) -> None:
        receiver = self.board("receiver")
        sender = self.board("sender")
        data = self.start(sender)
        accepted = receiver.command("RX " + data.hex())
        self.assertIn("DATA_VALIDATED", "\n".join(accepted))
        self.assertEqual(len(frames(accepted)), 1)

        wrong_session = bytearray(data)
        wrong_session[2:4] = bytes.fromhex("AABB")
        result = receiver.command("RX " + wrong_session.hex())
        output = "\n".join(result)
        self.assertIn("RX_DISCARD", output)
        self.assertNotIn("DATA_VALIDATED", output)
        self.assertNotIn("ACK_TX_BEGIN", output)
        self.assertNotIn("NACK_TX_BEGIN", output)
        self.assertEqual(receiver.status()["tx"], 1)

    def test_wrong_peer_ack_does_not_complete(self) -> None:
        sender = self.board("sender")
        data = self.start(sender)
        wrong_peer_ack = (
            bytes.fromhex("0009") + data[2:4] + bytes.fromhex("0301")
        )
        result = sender.command("RX " + wrong_peer_ack.hex())
        self.assertNotIn("ACK_ACCEPTED", "\n".join(result))
        self.assertNotEqual(sender.status()["state"], "COMPLETE")

    def test_timeout_retries_are_bounded(self) -> None:
        sender = self.board("sender")
        self.start(sender)
        sender.command("TICK 3001")
        self.assertLessEqual(sender.status()["tx"], 4)

    def test_new_boot_starts_a_fresh_data_attempt(self) -> None:
        first = self.board("sender")
        self.start(first)
        rebooted = self.board("sender")
        self.start(rebooted)


class TaskRestartTests(unittest.TestCase):
    def test_restart_resets_continuation_and_scheduler_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = str(Path(directory) / "restart")
            subprocess.run(
                [
                    "clang",
                    "--driver-mode=g++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wno-implicit-fallthrough",
                    "-Itests/mvp_stub",
                    "-Istable_lib/task",
                    "-Istable_lib/sleep",
                    "-Istable_lib/time-utils",
                    "tests/task_restart_test.cpp",
                    "stable_lib/task/task.cpp",
                    "-o",
                    binary,
                ],
                cwd=ROOT,
                check=True,
            )
            subprocess.run([binary], check=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
