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
PROJECT_LIB = ROOT / "lib"


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
                    "-I" + str(ROOT / "src"),
                    "-I" + str(ROOT / "include"),
                    "-c",
                    str(ROOT / "stable_lib/ssot/src/ssot/codec.cpp"),
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
                "-I" + str(ROOT / "tests/radio_stub"),
                "-I" + str(ROOT / "stable_lib/shared"),
                "-I" + str(ROOT / "src"),
                "-I" + str(ROOT / "include"),
                "-I" + str(ROOT / "stable_lib/lora"),
                "-I" + str(ROOT / "stable_lib/updi_uart/src"),
                "-I" + str(PROJECT_LIB / "task/src"),
                "-I" + str(PROJECT_LIB / "iw_core/src"),
                "-I" + str(PROJECT_LIB / "iw_tracker_radio_protocol/src"),
                *role_defines,
                str(ROOT / "tests/mvp_board.cpp"),
                str(ROOT / "stable_lib/lora/lora.cpp"),
                str(ssot_object),
                str(ROOT / "stable_lib/ssot/src/ssot/session.cpp"),
                str(ROOT / "stable_lib/ssot/src/ssot/control_input.cpp"),
                str(Path(cls.directory.name) / "task.o"),
                str(PROJECT_LIB / "iw_tracker_radio_protocol/src/codec.cpp"),
                str(PROJECT_LIB / "iw_core/src/byte_codec.cpp"),
                "-o",
                str(binary),
            ]
            if role == "sender":
                flags = command[: command.index(str(ROOT / "tests/mvp_board.cpp"))]
                dependency = subprocess.run(
                    [
                        *flags,
                        "-c",
                        str(PROJECT_LIB / "task/src/task.cpp"),
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
        self.assertIn("RADIO_READY", "\n".join(board.initial))
        return board

    def start(self, sender: Board) -> bytes:
        result = frames(sender.initial)
        self.assertEqual(result, [bytes.fromhex("01000000080168656c6c6f20776f726c64")])
        return result[0]

    def test_sender_receiver_complete_data_ack_and_second_cycle(self) -> None:
        receiver = self.board("receiver")
        sender = self.board("sender")
        data = self.start(sender)
        result = receiver.command("RX " + data.hex())
        self.assertIn("DATA_RX", "\n".join(result))
        self.assertIn("ACK_TX", "\n".join(result))
        ack = frames(result)[0]
        self.assertEqual(ack, bytes.fromhex("000100000301"))
        result = sender.command("RX " + ack.hex())
        self.assertIn("ACK_ACCEPTED", "\n".join(result))
        self.assertEqual(sender.status()["state"], "COMPLETE")

        second = frames(sender.command("START"))
        self.assertEqual(second, [bytes.fromhex("01000000080268656c6c6f20776f726c64")])
        result = receiver.command("RX " + second[0].hex())
        self.assertIn("DATA_RX", "\n".join(result))
        self.assertEqual(frames(result), [bytes.fromhex("000100000302")])
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
        self.assertIn("DATA_REJECTED", "\n".join(result))
        nack = frames(result)[0]
        self.assertEqual(nack, bytes.fromhex("000100000901"))
        retry = frames(sender.command("RX " + nack.hex()))
        self.assertEqual(retry, [data])

    def test_wrong_peer_ack_does_not_complete(self) -> None:
        sender = self.board("sender")
        self.start(sender)
        result = sender.command("RX " + bytes.fromhex("000900000301").hex())
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
        self.assertEqual(frames(rebooted.initial), [
            bytes.fromhex("01000000080168656c6c6f20776f726c64")
        ])


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
