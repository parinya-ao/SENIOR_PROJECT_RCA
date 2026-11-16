"""Simulation at firmware setup/loop boundaries; does not establish electrical isolation."""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RadioOnlyTests(unittest.TestCase):
    def test_radio_only_images_resolve_to_the_existing_role_application_ranges(self) -> None:
        from tools import rf_proof

        config = subprocess.check_output(
            ["pio", "project", "config", "--json-output"], cwd=ROOT, text=True
        )

        self.assertEqual(
            rf_proof.application_bounds_for_environment(config, "sender_arq_radio_only"),
            (0, 130048),
        )
        self.assertEqual(
            rf_proof.application_bounds_for_environment(config, "receiver_arq_radio_only"),
            (0, 130048),
        )
        self.assertTrue(
            rf_proof.application_layout_verified(
                ("sender_arq_radio_only", "receiver_arq_radio_only"), config
            )
        )

    def test_diagnostic_has_exact_payload_and_one_physical_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "check.cpp"
            source.write_text(r"""#include "arq.h"
#include <assert.h>
#include <string.h>
int main(void) {
    assert(arq::config::kMaxRetries==0);
    assert(!strcmp(arq::config::kPayload,"HELLO_LORA"));
    arq::Sender s; arq::InitSender(&s); assert(arq::ArmSender(&s,7));
    assert(arq::RequestTransmission(&s,(const uint8_t*)arq::config::kPayload,10,0,ARQ_ACK_MIN_MS));
    assert(s.attempts==1 && s.frame.sequence==0);
    arq::Receiver r; arq::InitReceiver(&r); assert(arq::ArmReceiver(&r,7));
    arq::Frame ack; assert(arq::HandleDataFrame(&r,&s.frame,&ack,false));
    assert(ack.type==arq::kAck && r.deliveries==1);
    arq::HandleTxCompletion(&s,50,true);
    arq::PollSender(&s,50+ARQ_ACK_MIN_MS);
    assert(s.attempts==1 && s.result==arq::Result::kTimeoutExhausted);
}
""")
            binary = Path(directory) / "check"
            subprocess.run(
                [
                    "clang",
                    "--driver-mode=g++",
                    "-std=c++17",
                    "-DARQ_RADIO_ONLY_DIAGNOSTIC=1",
                    "-Iinclude",
                    "-Isrc/arq",
                    str(source),
                    "src/arq/codec.cpp",
                    "src/arq/sender.cpp",
                    "src/arq/receiver.cpp",
                    "-o",
                    str(binary),
                ],
                cwd=ROOT,
                check=True,
            )
            subprocess.run([str(binary)], check=True)

    def test_radio_only_setup_preserves_arq_and_refuses_unpowered_sd_bus_use(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            objects = []
            for source in ("codec", "sender", "receiver"):
                obj = str(Path(directory) / (source + ".o"))
                objects.append(obj)
                subprocess.run(
                    [
                        "clang",
                        "--driver-mode=g++",
                    "-std=c++17",
                        "-DARQ_RADIO_ONLY_DIAGNOSTIC=1",
                        "-Isrc/arq",
                        "-Iinclude",
                        "-c",
                        f"src/arq/{source}.cpp",
                        "-o",
                        obj,
                    ],
                    cwd=ROOT,
                    check=True,
                )
            for role in ("SENDER", "RECEIVER"):
                binary = str(Path(directory) / role)
                subprocess.run(
                    [
                        "clang",
                        "--driver-mode=g++",
                        "-std=c++17",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-Wno-unused-variable",
                        "-Wno-unused-function",
                        "-Itests/arq/stub",
                        "-Itests/raw_mvp_stub",
                        "-Iinclude",
                        "-Isrc/arq",
                        "-DLORA_ROLE_" + role,
                        "-DARQ_TEST_MODE",
                        "-DARQ_RADIO_ONLY_DIAGNOSTIC=1",
                        '-DLORA_BUILD_ID="host-radio-only"',
                        "tests/arq/adapter_test.cpp",
                        *objects,
                        "-o",
                        binary,
                    ],
                    cwd=ROOT,
                    check=True,
                )
                subprocess.run([binary], check=True)
                subprocess.run([binary, "status-rx-burst"], check=True)
                if role == "RECEIVER":
                    subprocess.run([binary, "card"], check=True)


if __name__ == "__main__":
    unittest.main()
