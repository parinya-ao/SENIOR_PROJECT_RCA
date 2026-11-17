import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SenderStableTransportTests(unittest.TestCase):
    source: str
    transport: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (ROOT / "src/app/gateway_radio.cpp").read_text()
        cls.transport = (ROOT / "src/features/reliable_transfer/reliable_transport.h").read_text()

    def test_gateway_radio_transaction_has_a_src_app_owner(self) -> None:
        self.assertTrue(
            (ROOT / "src/app/gateway_radio.cpp").is_file(),
            "Gateway radio transaction must be implemented under src/app",
        )

    def test_sender_constructs_stable_radio_from_role_pins(self) -> None:
        self.assertIn("#include <lora.h>", self.source)
        self.assertIn("LoRa lora(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1)",
                      self.source)
        self.assertIn("HELLO_RF_FREQUENCY_MHZ", self.source)

    def test_sender_uses_bounded_shared_ack_nack_transport(self) -> None:
        self.assertIn("transport.SendReliableData", self.source)
        self.assertIn("ssot::kMaxAttempts", self.transport)
        self.assertIn("LORA_ACK_TIMEOUT_MS", self.transport)
        self.assertIn("ssot::kNackType", self.transport)

    def test_legacy_radio_and_eeprom_gate_calls_are_gone(self) -> None:
        for name in (
            "read_chip_version", "last_error", "time_on_air_us", "last_irq",
            "read_register", "start_receive", "standby", "recover", "EEPROM",
            "CampaignBuildGateResult",
        ):
            with self.subTest(name=name):
                self.assertNotIn(name, self.source)

if __name__ == "__main__":
    unittest.main()
