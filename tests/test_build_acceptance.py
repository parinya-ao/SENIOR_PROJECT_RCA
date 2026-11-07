import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_rf_proof import effective_platformio_config
import rf_proof as rf


class BuildAcceptanceTests(unittest.TestCase):
    def test_unsafe_image_makes_build_stage_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            proof = SimpleNamespace(run_dir=Path(directory), command=lambda *_: (0,b'',b''), note=lambda *_: None)
            measurement = dict(environment='sender', hex=dict(address_range=dict(start=1,end_exclusive=8,data_bytes=7)))
            with (patch.object(rf, 'ENVIRONMENTS', ('sender',)),
                  patch.object(rf, 'firmware_measurement', return_value=measurement)):
                self.assertEqual(rf.clean_builds(proof, effective_platformio_config()), 1)
