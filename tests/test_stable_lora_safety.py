"""Regression probes for the immutable stable LoRa implementation."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <Arduino.h>
#include "lora.h"

namespace fake_radio { State state{}; }
namespace fake_spi { State state{}; }
SPIClass SPI;
uint32_t host_ms;
alignas(16) static uint8_t module_storage[16];
void* operator new(size_t size) {
    if (size > sizeof(module_storage)) abort();
    return module_storage;
}

int main(int argc, char** argv) {
    LoRa radio(PIN_PC3, PIN_PD2, PIN_PD0, PIN_PD3);
    const char* mode = argc > 1 ? argv[1] : "";
    if (!strcmp(mode, "init-config")) {
        fake_radio::state.config_status = RADIOLIB_ERR_UNKNOWN;
        fake_radio::state.start_receive_status = RADIOLIB_ERR_UNKNOWN;
        if (radio.init(0, 915.0f, 2, 0) == 0) {
            fprintf(stderr, "init returned success after RadioLib setup errors\n");
            return 1;
        }
        return 0;
    }
    if (radio.init(0, 915.0f, 2, 0) != 0) return 2;
    if (!strcmp(mode, "send-done")) {
        uint8_t data = 1;
        if (radio.send(1, &data, 1) != 0) return 4;
        fake_radio::state.sent_action();
        fake_radio::state.finish_transmit_status = RADIOLIB_ERR_UNKNOWN;
        fake_radio::state.start_receive_status = RADIOLIB_ERR_UNKNOWN;
        if (radio.send_done() >= 0) {
            fprintf(stderr, "send_done returned success after cleanup errors\n");
            return 1;
        }
        return 0;
    }
    if (!strcmp(mode, "rx-short")) {
        fake_radio::state.rx_size = 1;
        fake_radio::state.rx_data[0] = 1;
        fake_radio::state.received_action();
        Address source = 0, destination = 0;
        uint8_t length = 0, payload[256] = {};
        if (radio.recv(&source, &destination, payload, sizeof payload, &length) >= 0 || length != 0) return 4;
        return 0;
    }
    if (!strcmp(mode, "tx-oversize")) {
        uint8_t payload[255] = {};
        if (radio.send(1, payload, sizeof(payload)) != RADIOLIB_ERR_PACKET_TOO_LONG || fake_radio::state.transmit_starts) return 4;
        return 0;
    }
    if (!strcmp(mode, "bounds")) {
        uint8_t payload[255] = {};
        const uint8_t sizes[] = {0, 1, 251, 252, 255};
        for (uint8_t size : sizes) {
            const int before = fake_radio::state.transmit_starts;
            const int16_t result = radio.send(1, payload, size);
            if (size > 251) {
                if (result != RADIOLIB_ERR_PACKET_TOO_LONG || before != fake_radio::state.transmit_starts) return 5;
            } else {
                if (result != 0) return 6;
                if (radio.send_done() != 0) return 7;
                fake_radio::state.sent_action();
                if (radio.send_done() != 1) return 8;
                const int finished = fake_radio::state.finish_transmits;
                if (radio.send_done() != 1 || finished != fake_radio::state.finish_transmits) return 9;
            }
        }
        if (radio.send(1, nullptr, 1) != RADIOLIB_ERR_NULL_POINTER) return 10;
        Address source = 0, destination = 0;
        uint8_t length = 0, output[253] = {};
        const size_t frames[] = {0, 1, 3, 4, 255, 256};
        for (size_t size : frames) {
            fake_radio::state.rx_size = size;
            fake_radio::state.received_action();
            const int16_t result = radio.recv(&source, &destination, output, sizeof output, &length);
            if ((size < 4 || size > 255) ? result >= 0 : result != 0) return 11;
        }
        fake_radio::state.rx_size = 6;
        fake_radio::state.received_action();
        if (radio.recv(&source, &destination, output, 1, &length) != RADIOLIB_ERR_PACKET_TOO_LONG || length) return 12;
        if (radio.recv(nullptr, &destination, output, sizeof output, &length) != RADIOLIB_ERR_NULL_POINTER) return 13;
        return 0;
    }
    if (!strcmp(mode, "recovery")) {
        uint8_t payload = 8;
        fake_radio::state.start_transmit_status = -4;
        if (radio.send(1, &payload, 1) != -4) return 4;
        fake_radio::state.start_transmit_status = 0;
        if (radio.send(1, &payload, 1) != 0) return 5;
        // Reinitialize a timed-out TX; a late ISR must not poison the next TX.
        if (radio.init(0, 915.0f, 2, 0) != 0) return 6;
        if (radio.send(1, &payload, 1) != 0) return 7;
        fake_radio::state.sent_action();
        if (radio.send_done() != 1) return 8;
        fake_radio::state.rx_size = 6;
        fake_radio::state.read_data_status = RADIOLIB_ERR_CRC_MISMATCH;
        fake_radio::state.received_action();
        Address source = 0, destination = 0;
        uint8_t length = 99, output[4] = {};
        if (radio.recv(&source, &destination, output, sizeof output, &length) != RADIOLIB_ERR_CRC_MISMATCH || length) return 9;
        fake_radio::state.start_receive_status = -6;
        fake_radio::state.received_action();
        if (radio.recv(&source, &destination, output, sizeof output, &length) != -6) return 11;
        if (radio.init(0, 915.0f, 2, 0) != -6) return 10;
        fake_radio::state.start_receive_status = 0;
        return radio.init(0, 915.0f, 2, 0);
    }
    return 3;
}
"""


class StableLoraSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory(prefix="stable-lora-safety-")
        cls.binary = Path(cls.directory.name) / "probe"
        cls.source = Path(cls.directory.name) / "probe.cpp"
        cls.source.write_text(PROBE)
        compiler = shutil.which("clang")
        if compiler is None:
            raise RuntimeError("Clang with its ASan/UBSan runtime is required for these probes")
        command = [
            compiler,
            "--driver-mode=g++",
            "-nostdlib++",
            "-std=c++11",
            "-fno-exceptions",
            "-fno-rtti",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer",
            "-fno-sanitize-link-c++-runtime",
            "-D_Bool=bool",
            "-I" + str(ROOT / "tests/radio_stub"),
            "-I" + str(ROOT / "src"),
            "-I" + str(ROOT / "stable_lib/lora"),
            "-I" + str(ROOT / "stable_lib/ssot"),
            str(cls.source),
            str(ROOT / "src/features/radio_link/radio_link.cpp"),
            "-o",
            str(cls.binary),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode:
            cls.directory.cleanup()
            raise AssertionError(result.stdout + result.stderr)
        cls.compiler_warning = result.stderr

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def test_payload_and_frame_boundaries(self) -> None:
        self.run_probe("bounds")

    def test_failed_operations_and_reinitialization(self) -> None:
        self.run_probe("recovery")

    def run_probe(self, mode: str) -> None:
        result = subprocess.run(
            [str(self.binary), mode],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr + self.compiler_warning,
        )

    def test_init_reports_radio_configuration_and_rx_start_errors(self) -> None:
        self.run_probe("init-config")

    def test_send_done_reports_finish_and_rx_rearm_errors(self) -> None:
        self.run_probe("send-done")

    def test_short_receive_frame_stays_within_internal_buffer(self) -> None:
        self.run_probe("rx-short")

    def test_oversized_transmit_is_rejected_without_buffer_overflow(self) -> None:
        self.run_probe("tx-oversize")


if __name__ == "__main__":
    unittest.main()
