"""S002 standalone PowerShell phase guard tests; synthetic sparse Wii-size banks only."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'Invoke-GolfNativeShot.ps1'
# Windows PowerShell 5.1 is named powershell.exe; PowerShell 7 is pwsh.
# NEVER skip the suite silently: CI must fail when the shell is unavailable.
SHELL = shutil.which('powershell.exe') or shutil.which('powershell') or shutil.which('pwsh')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class NativeStandalonePowerShellTests(unittest.TestCase):
    def setUp(self):
        if not SHELL:
            raise RuntimeError('PowerShell 5.1 or 7 is REQUIRED; skipped tests must not pass')
        tmp = tempfile.TemporaryDirectory(prefix='golf-native-standalone-')
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'Wii-AI-Golf'
        self.tools = self.repo / 'scripts'
        self.tools.mkdir(parents=True)
        shutil.copy2(SCRIPT, self.tools / SCRIPT.name)
        ret = self.run_ps('-Action', 'Start', '-Id', 'rehearsal001')
        self.assertEqual(ret.returncode, 0, ret.stderr)
        self.session = Path(ret.stdout.strip())
        self.assertTrue(self.session.is_dir())

    def run_ps(self, *args):
        return subprocess.run(
            [SHELL, '-NoProfile', '-NonInteractive', '-File',
             str(self.tools / SCRIPT.name), *map(str, args)],
            cwd=str(self.repo), capture_output=True, text=True, timeout=120)

    def save_manifest(self, phases):
        manifest = {
            'kind': 'local-private-golf-shot-cup-distance-checkpoints',
            'schema_version': 1, 'allowed_to_publish': False,
            'training_allowed': False, 'same_guest_frame_verified': False,
            'checkpoints': {},
        }
        for phase in phases:
            bank_hashes = {}
            for name, size in (('MEM1', 24 * 1024**2), ('MEM2', 64 * 1024**2)):
                target = self.session / f'{phase}-{name}.bin'
                with target.open('wb') as f:
                    f.truncate(size)
                    if name == 'MEM1':
                        f.seek(0)
                        f.write(b'RSPE01\x00\x01')
                        if phase == 'POST':
                            f.write(b'\x7f')
                    elif phase == 'POST':
                        f.seek(0)
                        f.write(b'\x55')
                bank_hashes[name] = sha256(target)
            manifest['checkpoints'][phase] = {
                'phase_label': phase,
                'operator_reports_gui_paused': True,
                'operator_reports_same_pause_mem1_mem2': True,
                'operator_observed_displaced_ball': phase == 'POST',
                'operator_reports_same_process': phase == 'POST',
                'operator_reports_same_hole': phase == 'POST',
                'operator_observed_result_visible': phase == 'RESULT',
                'sha256': bank_hashes,
            }
        manifest_file = self.session / 'shot-distance-captures-PRIVATE.json'
        manifest_file.write_text(json.dumps(manifest), encoding='utf-8')
        return manifest_file, manifest

    def test_start_is_one_command_and_reuse_is_refused(self):
        self.assertEqual(self.session.parent.name, 'captures')
        self.assertEqual(self.session.parent.parent.name, 'Wii-AI-Golf-Data')
        duplicate = self.run_ps('-Action', 'Start', '-Id', 'rehearsal001')
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertTrue(self.session.is_dir())
        distinct = self.run_ps('-Action', 'Start')
        self.assertEqual(distinct.returncode, 0, distinct.stderr)
        self.assertNotEqual(distinct.stdout.strip(), str(self.session))

    def test_status_of_fresh_session_is_pending_not_failure_or_capture(self):
        result = self.run_ps('-Action', 'Status', '-Session', self.session)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('AWAITING_PRE', result.stdout)
        self.assertIn('HasNativePrePostPair', result.stdout)
        self.assertIn('False', result.stdout)
        self.assertNotIn('PREPOST_INTEGRITY_VERIFIED', result.stdout)

    def test_verify_of_fresh_session_fails_closed(self):
        result = self.run_ps('-Action', 'Verify', '-Session', self.session)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('NOT READY', result.stderr)

    def test_only_pre_is_awaiting_post_and_verify_refuses(self):
        self.save_manifest(['PRE'])
        status = self.run_ps('-Action', 'Status', '-Session', self.session)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn('AWAITING_POST', status.stdout)
        verify = self.run_ps('-Action', 'Verify', '-Session', self.session)
        self.assertNotEqual(verify.returncode, 0)
        self.assertIn('NOT READY', verify.stderr)

    def test_prepost_full_native_integrity_not_ball_physics(self):
        self.save_manifest(['PRE', 'POST'])
        result = self.run_ps('-Action', 'Verify', '-Session', self.session)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PREPOST_INTEGRITY_VERIFIED', result.stdout)
        self.assertIn('HasNativePrePostPair', result.stdout)
        self.assertIn('True', result.stdout)
        self.assertIn('BallWorldXYZOrVelocityVerified', result.stdout)
        self.assertIn('TrainingApproved', result.stdout)
        self.assertNotIn(str(self.session), result.stdout)
        self.assertNotIn('RSPE01', result.stdout)

    def test_changed_native_byte_rejected(self):
        self.save_manifest(['PRE'])
        with (self.session / 'PRE-MEM1.bin').open('r+b') as f:
            f.seek(80)
            f.write(b'\x42')
        result = self.run_ps('-Action', 'Status', '-Session', self.session)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('digest mismatch', result.stderr)

    def test_training_claim_never_accepted(self):
        file, manifest = self.save_manifest(['PRE'])
        manifest['training_allowed'] = True
        file.write_text(json.dumps(manifest), encoding='utf-8')
        result = self.run_ps('-Action', 'Status', '-Session', self.session)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unsupported training', result.stderr)

    def test_result_without_pre_post_refused(self):
        self.save_manifest(['RESULT'])
        result = self.run_ps('-Action', 'Status', '-Session', self.session)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('phase order', result.stderr)

    def test_missing_human_post_observation_refused(self):
        file, manifest = self.save_manifest(['PRE', 'POST'])
        manifest['checkpoints']['POST']['operator_observed_displaced_ball'] = False
        file.write_text(json.dumps(manifest), encoding='utf-8')
        result = self.run_ps('-Action', 'Verify', '-Session', self.session)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('human-observed displacement', result.stderr)

    def test_legacy_unindexed_bank_is_not_a_valid_capture(self):
        (self.session / 'PRE-MEM1.bin').write_bytes(b'not even a dump')
        result = self.run_ps('-Action', 'Status', '-Session', self.session)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unindexed native banks', result.stderr)


if __name__ == '__main__':
    unittest.main()
