"""Acquisition boundary: command recovery cannot authorize incomplete evidence."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from tools.arq_trial import Capture


class CaptureTests(unittest.TestCase):
    def test_programming_failure_still_attempts_verified_normal_restore(self):
        from tools import arq_trial
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'generated').mkdir()
            (root/'generated/arq_manifest.json').write_text('{}')
            build=root/'.pio/build/receiver_arq_test';build.mkdir(parents=True)
            for suffix in ('hex','elf'):(build/('firmware.'+suffix)).write_text('image')
            with patch.object(arq_trial,'ROOT',root),patch('generate_lora_config.generate'),\
                 patch.object(arq_trial.subprocess,'check_output',return_value='config'),\
                 patch.object(arq_trial.rf,'check_port_owners',return_value=[]),\
                 patch.object(arq_trial.rf,'program_application',return_value=1),\
                 patch.object(arq_trial,'prepare',return_value=root/'standby') as restore:
                with self.assertRaisesRegex(ValueError,'programming failed'):arq_trial.campaign()
                restore.assert_called_once()

    def make_capture(self, responses=True):
        c = Capture(None)
        get = c.queue.get
        c.queue.get = lambda **kwargs: get(block=False)
        c.monitors = {r: {'process': SimpleNamespace(poll=lambda: None)}
                      for r in ('sender', 'receiver')}
        self.clock = 0
        def monotonic():
            self.clock += .25
            return self.clock
        def command(role, text):
            c.commands.append(dict(role=role, text=text))
            if responses and text == 'STATUS':
                for event in self.status(role):
                    c.queue.put((role, 'stdout', event.encode()))
        c.command = command
        return c, monotonic

    def status(self, role, overflow=0, build='build'):
        return [f'A t=1 e=BOOT s=0 rc=0 v=4',
                f'A t=1 e=IDENTITY s=0 build={build} config=config',
                f'A t=1 e=STATUS s=0 ready=1 overflow={overflow}',
                'A t=1 e=REG s=0 bytes=8100',
                f'A t=1 e=STATUS_END s=0 v={overflow}']

    def acquire(self, c, clock):
        with patch('tools.arq_trial.time.monotonic', clock):
            c.acquire({r: {'build_id': 'build'} for r in c.monitors}, 'config')

    def test_missing_startup_recovers_once_and_drains_each_role(self):
        c, clock = self.make_capture()
        self.acquire(c, clock)
        self.assertEqual(c.commands, [dict(role=r, text='STATUS') for r in ('sender', 'receiver')])
        self.assertLess(self.clock, 45)

    def test_absent_and_partial_responses_stop_without_arm(self):
        for partial in (False, True):
            c, clock = self.make_capture(False)
            if partial:
                c.queue.put(('sender', 'stdout', b'A t=1 e=STATUS s=0 ready=1 overflow=0'))
            with self.assertRaisesRegex(ValueError, 'capture deadline'):
                self.acquire(c, clock)
            self.assertTrue(all(x['text'] == 'STATUS' for x in c.commands))
            self.assertLessEqual(self.clock, 46)

    def test_complete_startup_needs_no_recovery(self):
        c, clock = self.make_capture()
        for role in c.monitors:
            for e in self.status(role): c.queue.put((role, 'stdout', e.encode()))
        self.acquire(c, clock)
        self.assertEqual(c.commands, [])

    def test_next_gate_requires_complete_status_from_previous_session(self):
        c, clock = self.make_capture()
        for role in c.monitors:
            for e in self.status(role):c.queue.put((role,'stdout',e.replace('s=0','s=10').encode()))
        with patch('tools.arq_trial.time.monotonic',clock):
            c.acquire({r:{'build_id':'build'} for r in c.monitors},'config',expected_session=16)
        self.assertEqual(c.commands,[])

    def test_overflow_identity_and_monitor_exit_fail_closed(self):
        for problem in ('overflow', 'identity', 'exit'):
            c, clock = self.make_capture()
            for role in c.monitors:
                for e in self.status(role, overflow=int(problem == 'overflow'),
                                     build='wrong' if problem == 'identity' else 'build'):
                    c.queue.put((role, 'stdout', e.encode()))
            if problem == 'exit': c.monitors['sender']['process'].poll = lambda: 1
            with self.assertRaises(ValueError): self.acquire(c, clock)
            self.assertEqual(c.commands, [])

    def test_cleanup_stops_all_monitors_and_retains_partial_evidence(self):
        c, _ = self.make_capture()
        c.queue.put(('sender', 'stdout', b'A t=1 e=STATUS s=0 ready=1 overflow=0'))
        with patch('tools.arq_trial.rf.stop_rf_monitor') as stop:
            c.close()
        self.assertEqual(stop.call_count, 2)
        self.assertEqual(c.events[0]['e'], 'STATUS')

    def test_cleanup_records_truncated_tail_without_masking_original_failure(self):
        c, _ = self.make_capture()
        c.queue.put(('sender','stdout',b'A t=1 e=IDEN'))
        with patch('tools.arq_trial.rf.stop_rf_monitor'):c.close()
        self.assertTrue(c.errors)
