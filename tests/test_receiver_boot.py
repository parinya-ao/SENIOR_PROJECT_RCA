import unittest
from pathlib import Path
import subprocess
import tempfile
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import receiver_boot as boot


class ReceiverBootTests(unittest.TestCase):
    def test_page0_overlay_preserves_every_other_byte(self):
        original = bytes(range(256)) * 512
        stub = b'\xf8\x94\x11\x24'
        patched, changes = boot.patch_page0(original, stub)
        self.assertEqual(len(patched), 512)
        self.assertEqual(patched[len(stub):], original[len(stub):512])
        self.assertEqual(changes, [[0, 4]])

    def test_rejects_invalid_backup_and_out_of_page_stub(self):
        for original, stub in [(b'bad', b'ab'), (b'\xff'*131072, b'x'*513),
                               (b'\xff'*131072, b'')]:
            with self.assertRaises(ValueError):
                boot.patch_page0(original, stub)

    def test_write_command_is_exact_page_erase_not_chip_or_fuses(self):
        command = boot.page_write_command('avrdude', 'avrdude.conf', 'receiver', 'page.hex', 0, 512)
        self.assertNotIn('-e', command)
        self.assertNotIn('-V', command)
        self.assertIn('-D', command)
        self.assertEqual(command[command.index('-T')+1], 'erase flash 0x0 0x200')
        self.assertEqual([command[i+1] for i,x in enumerate(command) if x == '-U'],
                         ['flash:w:page.hex:i', 'flash:v:page.hex:i'])
        for start, size in [(1,512), (0,513), (0x5800,512), (0,1024)]:
            with self.assertRaises(ValueError):
                boot.page_write_command('a', 'c', 'p', 'f', start, size)

    def test_address_units_use_byte_addresses(self):
        self.assertEqual(boot.reset_target(bytes.fromhex('0c94002c'), 0), 0x5800)
        self.assertEqual(boot.reset_target(bytes.fromhex('52c00000'), 0x5800), 0x58a6)
        with self.assertRaises(ValueError):
            boot.reset_target(b'\xff'*4, 0x5800)

    def test_missing_or_wrong_specific_authorization_opens_no_port(self):
        proof = SimpleNamespace(note=lambda *_: None)
        args = SimpleNamespace(authorize_receiver_boot_page0=None,
                               receiver_boot_package=None, authorize_upload=True)
        with patch.object(boot, 'read_snapshot') as snapshot:
            self.assertEqual(boot.install(proof, args), 2)
            snapshot.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)/'map.json'
            package.write_text('{}')
            args.receiver_boot_package = package
            args.authorize_receiver_boot_page0 = 'wrong'
            with patch.object(boot, 'load_package', return_value={}), patch.object(boot, 'read_snapshot') as snapshot:
                with self.assertRaises(ValueError):
                    boot.install(proof, args)
                snapshot.assert_not_called()

    def test_unapproved_flash_fuse_or_eeprom_changes_fail_preservation(self):
        before = {name: b'abc' for name in ('signature','sernum','fuses','eeprom','lock')}
        before['flash'] = b'\xff'*131072
        after = dict(before)
        after['flash'] = b'\0'*512 + before['flash'][512:]
        boot.require_preserved(before, after, 0, 512)
        for name in ('signature','sernum','fuses','eeprom','lock','flash'):
            changed = dict(after)
            changed[name] = changed[name][:-1] + b'\x00'
            with self.subTest(name=name), self.assertRaises(ValueError):
                boot.require_preserved(before, changed, 0, 512)

    def test_no_meter_still_blocks_write_without_wiring_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / 'map.json'
            package.write_text('{}')
            args = SimpleNamespace(receiver_boot_package=package, authorize_upload=True,
                authorize_receiver_boot_page0=boot.sha(package.read_bytes()),
                no_meter_mode=True, physical_mapping_verified=False, power_verified=False)
            proof = SimpleNamespace(note=lambda *_: None)
            with patch.object(boot, 'load_package', return_value={}), \
                    patch.object(boot, 'read_snapshot') as snapshot:
                self.assertEqual(boot.install(proof, args), 2)
                snapshot.assert_not_called()


class CompiledHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        (directory/'handoff_config.h').write_text('#define APP_START 0x5800\n#define CCP_IOREG_VALUE 0xD8\n' +
            ''.join(f'#define RESET_BYTE_{i} {byte}\n' for i,byte in enumerate(bytes.fromhex('52c00000'))))
        elf, binary = directory/'boot.elf', directory/'boot.bin'
        subprocess.run([str(boot.TOOLCHAIN/'avr-gcc'), '-mmcu=avr128da28', '-nostdlib', '-nostartfiles',
            '-I', str(directory), '-Wl,-e,_start', str(boot.ROOT/'boot/receiver_handoff.S'), '-o', str(elf)], check=True)
        subprocess.run([str(boot.TOOLCHAIN/'avr-objcopy'), '-O', 'binary', str(elf), str(binary)], check=True)
        cls.code = binary.read_bytes()

    def test_compiled_handoff_uses_correct_byte_target_and_interrupt_state(self):
        result = boot.trace_stub(self.code, bytes.fromhex('52c00000'))
        self.assertEqual(result, dict(application_entered=True, cpuint=0, interrupts=False))
        self.assertLess(len(self.code), 512)
        self.assertIn(bytes.fromhex('0c94002c'), self.code)

    def test_blank_or_any_wrong_reset_byte_parks(self):
        cases = [b'\xff'*4]
        for index in range(4):
            entry = bytearray.fromhex('52c00000')
            entry[index] ^= 1
            cases.append(entry)
        for entry in cases:
            with self.subTest(entry=entry):
                result = boot.trace_stub(self.code, entry)
                self.assertFalse(result['application_entered'])
                self.assertFalse(result['interrupts'])
                self.assertEqual(result['cpuint'], 0)


class BootPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.directory = Path(temporary.name)
        def command(name, argv, timeout=None):
            result = subprocess.run(argv, capture_output=True, timeout=timeout)
            (cls.directory/(name+'.stdout.log')).write_bytes(result.stdout)
            (cls.directory/(name+'.stderr.log')).write_bytes(result.stderr)
            return result.returncode, result.stdout, result.stderr
        proof = SimpleNamespace(run_dir=cls.directory, command=command,
            note=lambda name, content: (cls.directory/name).write_text(content))
        boot.prepare(proof)
        cls.package = cls.directory/'receiver-boot-overwrite-map.json'

    def test_exact_installed_compiler_and_avrdude_simulation_package(self):
        report = boot.load_package(self.package)
        self.assertEqual(report['boot_pages_written'], [0])
        self.assertEqual(report['stub_size'], 48)
        self.assertEqual(report['physical_restore_test'], 'NOT_RUN')
        self.assertEqual(report['physical_programming'], 'NOT_RUN')
        self.assertTrue((self.directory/'receiver-handoff.map').is_file())

    def test_modified_package_image_is_rejected(self):
        image = self.directory/'receiver-boot-page0.hex'
        original = image.read_bytes()
        try:
            image.write_bytes(original.replace(b'F894', b'0000', 1))
            with self.assertRaises(ValueError):
                boot.load_package(self.package)
        finally:
            image.write_bytes(original)

    def snapshots(self):
        original = boot.BACKUP.read_bytes()
        report = boot.load_package(self.package)
        spi = boot.normalize_ihex_region((self.directory/'receiver-spi-full-pages.hex').read_text(), boot.APP_START, report['application_write_range'][1])
        base = dict(signature=bytes.fromhex('1e970a'), sernum=bytes.fromhex(report['expected_serial']),
            fuses=boot.BACKUP.with_name('receiver-candidate-backup-fuses.bin').read_bytes(),
            eeprom=boot.BACKUP.with_name('receiver-candidate-backup-eeprom.bin').read_bytes(), lock=bytes.fromhex('5cc5c55c'), flash=original)
        app = dict(base, flash=original[:boot.APP_START]+spi+original[report['application_write_range'][1]:])
        page = boot.normalize_ihex_region((self.directory/'receiver-boot-page0.hex').read_text(), 0, 512)
        patched = dict(app, flash=page+app['flash'][512:])
        return base, app, patched

    def test_authorized_installer_programs_app_before_boot_with_preservation(self):
        import rf_proof as rf
        snapshots = self.snapshots()
        commands = []
        proof = SimpleNamespace(run_dir=self.directory, command=lambda name, argv, *a: (commands.append(argv) or (0,b'',b'')),
            note=lambda name, text:(self.directory/name).write_text(text))
        args = SimpleNamespace(receiver_boot_package=self.package, authorize_upload=True,
            authorize_receiver_boot_page0=boot.sha(self.package.read_bytes()), physical_mapping_verified=True, power_verified=True)
        with patch.object(boot, 'read_snapshot', side_effect=snapshots), \
                patch.object(rf, 'physical_readiness_errors', return_value=[]), \
                patch.object(rf, 'check_port_owners', return_value=[]):
            self.assertEqual(boot.install(proof, args), 0)
        self.assertEqual([command[command.index('-T')+1] for command in commands],
                         ['erase flash 0x5800 0x7800', 'erase flash 0x0 0x200'])
        self.assertTrue(all('-e' not in command for command in commands))

    def test_restore_can_recover_partly_erased_page_without_rewriting_app(self):
        import rf_proof as rf
        base, app, _ = self.snapshots()
        damaged = dict(app, flash=b'\xff'*512 + app['flash'][512:])
        commands = []
        proof = SimpleNamespace(run_dir=self.directory, command=lambda name, argv, *a:(commands.append(argv) or (0,b'',b'')),
            note=lambda name, text:(self.directory/name).write_text(text))
        report = boot.load_package(self.package)
        args = SimpleNamespace(receiver_boot_package=self.package, authorize_upload=True,
            authorize_receiver_boot_restore=report['restore_hex_sha256'], physical_mapping_verified=True, power_verified=True)
        with patch.object(boot, 'read_snapshot', side_effect=[damaged, app]), \
                patch.object(rf, 'physical_readiness_errors', return_value=[]), \
                patch.object(rf, 'check_port_owners', return_value=[]):
            self.assertEqual(boot.install(proof, args, restore=True), 0)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][commands[0].index('-T')+1], 'erase flash 0x0 0x200')

    def test_app_preservation_failure_prevents_boot_write(self):
        import rf_proof as rf
        base, app, _ = self.snapshots()
        broken = bytearray(app['flash']); broken[1000] ^= 1
        app['flash'] = bytes(broken)
        commands = []
        proof = SimpleNamespace(run_dir=self.directory, command=lambda name, argv, *a:(commands.append(argv) or (0,b'',b'')), note=lambda *_:None)
        args = SimpleNamespace(receiver_boot_package=self.package, authorize_upload=True,
            authorize_receiver_boot_page0=boot.sha(self.package.read_bytes()), physical_mapping_verified=True, power_verified=True)
        with patch.object(boot, 'read_snapshot', side_effect=[base, app]), \
                patch.object(rf, 'physical_readiness_errors', return_value=[]), \
                patch.object(rf, 'check_port_owners', return_value=[]):
            with self.assertRaises(ValueError):
                boot.install(proof, args)
        self.assertEqual(len(commands), 1)


class ApplicationPageWriteTests(unittest.TestCase):
    def test_guarded_app_writer_erases_only_its_page_with_installed_avrdude_dryrun(self):
        import rf_proof as rf
        from test_rf_proof import effective_platformio_config
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root/'.pio/build/receiver_spi'
            build.mkdir(parents=True)
            payload = bytes.fromhex('52c00000')
            (build/'firmware.hex').write_text(boot.ihex(payload, boot.APP_START))
            original = bytes(range(256))*512
            before = {name: b'unchanged' for name in ('signature','sernum','fuses','eeprom','lock')}
            before['flash'] = original
            (root/'before.bin').write_bytes(original)
            commands = []
            def command(name, argv, *args):
                commands.append(argv)
                if '--version' in argv:
                    return 0, b'avrdude version 8.1', b''
                self.assertIn('erase flash 0x5800 0x200', argv)
                self.assertNotIn('-e', argv)
                simulated = list(argv)
                simulated[simulated.index('-c')+1] = 'dryrun'
                at = simulated.index('-T')
                simulated[at:at] = ['-U', f'flash:w:{root/"before.bin"}:r']
                simulated += ['-U', f'flash:r:{root/"after.bin"}:r']
                result = subprocess.run(simulated, capture_output=True)
                return result.returncode, result.stdout, result.stderr
            def snapshot(proof, name, role):
                if 'before' in name:
                    return dict(before)
                return dict(before, flash=(root/'after.bin').read_bytes())
            proof = SimpleNamespace(run_dir=root, command=command, note=lambda *_:None)
            with patch.object(rf, 'ROOT', root), patch.object(boot, 'read_snapshot', side_effect=snapshot):
                self.assertEqual(rf.program_application(proof, 'receiver_spi', effective_platformio_config()), 0)
            after = (root/'after.bin').read_bytes()
            self.assertEqual(after[:boot.APP_START], original[:boot.APP_START])
            self.assertEqual(after[boot.APP_START+512:], original[boot.APP_START+512:])
            self.assertEqual(after[boot.APP_START:boot.APP_START+512], payload+b'\xff'*508)
