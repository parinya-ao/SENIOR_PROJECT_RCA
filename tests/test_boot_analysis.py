import unittest

from tools.boot_analysis import analyze


class BootAnalysisTests(unittest.TestCase):
    def test_does_not_count_unreachable_data_as_handoff(self):
        result = analyze(
            "0: 00 c0 rjmp .+0 ; 0x2\n2: ff cf rjmp .-2 ; 0x2\n4: 0c 94 00 2c jmp 0x5800", 0x5800
        )
        self.assertEqual(result["verdict"], "NO_APPLICATION_HANDOFF")

    def test_direct_handoff_and_indirect_unknown(self):
        self.assertEqual(
            analyze("0: 0c 94 00 2c jmp 0x5800", 0x5800)["application_transfers"], [0x5800]
        )
        self.assertEqual(analyze("0: 09 94 ijmp", 0x5800)["verdict"], "UNRESOLVED")
