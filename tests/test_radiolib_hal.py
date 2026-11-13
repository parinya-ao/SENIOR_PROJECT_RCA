"""Characterize installed RadioLib, without replacing any driver method."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class RadioLibHalTests(unittest.TestCase):
    def test_real_sx1276_public_hal(self):
        lib=ROOT/'.pio/libdeps/sender_arq/RadioLib'
        self.assertTrue(lib.exists(), 'install pinned PlatformIO RadioLib dependency first')
        src=lib/'src'
        files=['Hal.cpp','Module.cpp','protocols/PhysicalLayer/PhysicalLayer.cpp',
               'modules/SX127x/SX127x.cpp','modules/SX127x/SX1278.cpp','modules/SX127x/SX1276.cpp',
               'utils/Utils.cpp']
        with tempfile.TemporaryDirectory() as d:
            binary=str(Path(d)/'hal')
            subprocess.run(['g++','-std=c++11','-ffunction-sections','-fdata-sections',
                '-Wl,--gc-sections','-I'+str(src),'tests/radiolib_hal_test.cpp',
                *[str(src/f) for f in files],'-o',binary],cwd=ROOT,check=True)
            subprocess.run([binary],check=True,timeout=10)
