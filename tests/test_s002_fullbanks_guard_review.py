"""Offline S002 native-bank exporter falsification tests; no Dolphin, RAM, or networking.

Stacked review-only tests for #201.  The fake memory engine deliberately limits
banks to bytes; neither real game content nor raw memory appears in test output.
"""
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'capture_golf_fullbanks_private.py'
spec = importlib.util.spec_from_file_location('s002_fullbanks_under_review', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HEADER = b'RSPE01\x00\x01'
SMALL_BANKS = (('MEM1', 'mem1.raw', 0x80000000, 16),
               ('MEM2', 'mem2.raw', 0x90000000, 24))


class MemoryEngineFake:
    def __init__(self, *, header=HEADER, hook_ok=True, broken_bank=None):
        self.header = header
        self.hook_ok = hook_ok
        self.broken_bank = broken_bank
        self.hook_calls = 0
        self.unhook_calls = 0
        self.reads = []

    def hook(self):
        self.hook_calls += 1

    def is_hooked(self):
        return self.hook_ok

    def un_hook(self):
        self.unhook_calls += 1

    def read_bytes(self, address, size):
        self.reads.append((address, size))
        if address == 0x80000000:
            result = (self.header + b'\x11' * size)[:size]
        elif address == 0x90000000:
            result = b'\x22' * size
        else:
            raise AssertionError('unexpected synthetic address')
        if self.broken_bank == address and size > 8:
            return result[:-1]
        return result


class KeeperFake:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = []

    def preserve(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError('synthetic keeper failure')
        a = kwargs['mem1_source']
        b = kwargs['mem2_source']
        assert a.read_bytes() == HEADER + b'\x11' * 8
        assert b.read_bytes() == b'\x22' * 24
        return {'preserved_native_banks': 2}


class NativeBankGuardReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'Wii-AI-Golf-Data'
        self.root.mkdir()
        self.session = self.root / 'SHOT-test-PRIVATE'
        self.session.mkdir()

    def invoke(self, flags=(), *, engine=None, keeper=None, session=None):
        engine = engine if engine is not None else MemoryEngineFake()
        keeper = keeper if keeper is not None else KeeperFake()
        argv = ['capture_golf_fullbanks_private.py', '--session',
                str(session if session is not None else self.session),
                '--phase', 'PRE', *flags]
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(module, 'PRIVATE', self.root), \
             patch.object(module, 'BANKS', SMALL_BANKS), \
             patch.dict(sys.modules, {
                 'dolphin_memory_engine': engine,
                 'preserve_golf_shot_distance_checkpoint_private': keeper,
             }), patch.object(sys, 'argv', argv), \
             redirect_stdout(stdout), redirect_stderr(stderr):
            result = module.main()
        return result, engine, keeper, stdout.getvalue(), stderr.getvalue()

    def test_native_bank_dimensions_are_real_wii_sizes(self):
        self.assertEqual(module.BANKS[0][3], 24 * 1024 * 1024)
        self.assertEqual(module.BANKS[1][3], 64 * 1024 * 1024)

    def test_success_cleans_staging_and_never_claims_guest_frame_atomicity(self):
        result, engine, keeper, output, error = self.invoke(['--paused-confirmed'])
        self.assertEqual((result, error), (0, ''))
        self.assertEqual(engine.hook_calls, 1)
        self.assertEqual(engine.unhook_calls, 1)
        self.assertEqual(len(keeper.calls), 1)
        self.assertFalse((self.session / 'STAGING-PRE').exists())
        self.assertIn('"same_guest_frame_independently_verified": false', output)
        self.assertIn('"allowed_to_publish": false', output)
        self.assertIn('"training_allowed": false', output)
        self.assertTrue(keeper.calls[0]['paused_confirmed'])

    def test_missing_pause_opt_in_fails_without_hook_or_files(self):
        result, engine, keeper, _, error = self.invoke()
        self.assertEqual(result, 1)
        self.assertEqual(engine.hook_calls, 0)
        self.assertEqual(len(keeper.calls), 0)
        self.assertFalse((self.session / 'STAGING-PRE').exists())
        self.assertIn('refused', error)

    def test_post_requires_visible_displacement_and_same_process_hole(self):
        result, engine, keeper, _, error = self.invoke(['--phase', 'POST', '--paused-confirmed'])
        self.assertEqual(result, 1)
        self.assertEqual(engine.hook_calls, 0)
        self.assertEqual(len(keeper.calls), 0)
        self.assertIn('POST', error)
        flags = ['--phase', 'POST', '--paused-confirmed', '--shot-observed',
                 '--same-process-confirmed', '--same-hole-confirmed']
        result, engine, keeper, _, _ = self.invoke(flags)
        self.assertEqual(result, 0)
        self.assertEqual(keeper.calls[0]['checkpoint'], 'POST')
        self.assertTrue(keeper.calls[0]['shot_observed'])

    def test_result_requires_visible_result_attestation(self):
        result, engine, keeper, _, _ = self.invoke(['--phase', 'RESULT', '--paused-confirmed'])
        self.assertEqual((result, engine.hook_calls, len(keeper.calls)), (1, 0, 0))

    def test_session_outside_private_root_is_rejected_before_hook(self):
        outside = Path(self.temp.name) / 'SHOT-outside-PRIVATE'
        outside.mkdir()
        result, engine, keeper, _, _ = self.invoke(['--paused-confirmed'], session=outside)
        self.assertEqual((result, engine.hook_calls, len(keeper.calls)), (1, 0, 0))

    def test_wrong_revision_header_fails_without_preservation(self):
        engine = MemoryEngineFake(header=b'RSPE01\x00\x00')
        result, engine, keeper, _, error = self.invoke(['--paused-confirmed'], engine=engine)
        self.assertEqual(result, 1)
        self.assertEqual((engine.hook_calls, engine.unhook_calls), (1, 1))
        self.assertEqual(len(keeper.calls), 0)
        self.assertFalse((self.session / 'STAGING-PRE').exists())
        self.assertIn('header', error)

    def test_failed_engine_hook_fails_before_native_dump(self):
        result, engine, keeper, _, error = self.invoke(['--paused-confirmed'],
                                                        engine=MemoryEngineFake(hook_ok=False))
        self.assertEqual(result, 1)
        self.assertEqual(len(keeper.calls), 0)
        self.assertFalse((self.session / 'STAGING-PRE').exists())
        self.assertIn('hook', error)

    def test_truncated_mem2_never_reaches_keeper(self):
        engine = MemoryEngineFake(broken_bank=0x90000000)
        result, engine, keeper, _, error = self.invoke(['--paused-confirmed'], engine=engine)
        self.assertEqual(result, 1)
        self.assertEqual(len(keeper.calls), 0)
        self.assertEqual(engine.unhook_calls, 1)
        self.assertIn('Incomplete', error)
        self.assertFalse((self.session / 'PRE-MEM1.bin').exists())
        self.assertFalse((self.session / 'PRE-MEM2.bin').exists())
        # Current implementation leaves private, incomplete staging. Not a completed capture.
        self.assertTrue((self.session / 'STAGING-PRE').exists())

    def test_keeper_failure_never_reports_success_or_deletes_private_evidence(self):
        result, engine, keeper, output, error = self.invoke(['--paused-confirmed'],
                                                             keeper=KeeperFake(fail=True))
        self.assertEqual(result, 1)
        self.assertEqual(engine.unhook_calls, 1)
        self.assertNotIn('native_banks_saved', output)
        self.assertIn('synthetic keeper failure', error)
        self.assertEqual(len(keeper.calls), 1)
        # Known follow-up: staged data currently blocks same-phase retries.
        self.assertTrue((self.session / 'STAGING-PRE').exists())

    def test_preexisting_staging_is_not_overwritten(self):
        stage = self.session / 'STAGING-PRE'
        stage.mkdir()
        original = stage / 'mem1.raw'
        original.write_bytes(b'keep-existing-private-capture')
        result, _, keeper, _, _ = self.invoke(['--paused-confirmed'])
        self.assertEqual(result, 1)
        self.assertEqual(original.read_bytes(), b'keep-existing-private-capture')
        self.assertEqual(len(keeper.calls), 0)

    def test_read_bank_refuses_nonbytes_and_short_reads(self):
        target = self.session / 'incomplete-test.raw'
        for returned in ('bad-response', b'\x00' * 3):
            class BadReader:
                def read_bytes(self, _address, _size):
                    return returned
            with self.subTest(response_type=type(returned).__name__):
                target.unlink(missing_ok=True)
                with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
                    module.read_bank(BadReader(), 0x80000000, 8, target)


if __name__ == '__main__':
    unittest.main()
