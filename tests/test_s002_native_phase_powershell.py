"""CLI-only native bank phase safety tests; fake/sparse files, no game or Dolphin."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'scripts'
PWSH = shutil.which('pwsh')


def _hash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


@unittest.skipUnless(PWSH, 'PowerShell 7 needed for cross-platform synthetic tests')
class NativeP0PowerShellTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='golf-p0-powershell-')
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.repo = self.workspace / 'Wii-AI-Golf'
        self.scripts = self.repo / 'scripts'
        self.scripts.mkdir(parents=True)
        for name in ('New-GolfNativeShotSession.ps1', 'Test-GolfNativeShotPair.ps1'):
            shutil.copy2(TOOLS / name, self.scripts / name)
        self.session = self.run_ps('New-GolfNativeShotSession.ps1', '-Id', 'rehearsal001').stdout.strip()
        self.assertTrue(Path(self.session).is_dir())

    def run_ps(self, script, *args):
        return subprocess.run([PWSH, '-NoProfile', '-NonInteractive', '-File', str(self.scripts / script), *map(str, args)],
                              cwd=str(self.repo), capture_output=True, text=True, timeout=100)

    def save_manifest(self, phases):
        p = Path(self.session)
        manifest = {'kind': 'local-private-golf-shot-cup-distance-checkpoints',
                    'schema_version': 1, 'allowed_to_publish': False,
                    'training_allowed': False, 'same_guest_frame_verified': False,
                    'checkpoints': {}}
        for phase in phases:
            banks = {}
            for name, size in (('MEM1', 24*1024**2), ('MEM2', 64*1024**2)):
                target = p / f'{phase}-{name}.bin'
                with target.open('wb') as fd:
                    fd.truncate(size)  # fully sized, sparse/synthetic zero bank
                    if name == 'MEM1':
                        fd.seek(0)
                        fd.write(b'RSPE01\x00\x01')
                        if phase == 'POST':
                            fd.write(b'\x7f')  # distinct synthetic post game word
                    elif phase == 'POST':
                        fd.seek(0)
                        fd.write(b'\x55')
                banks[name] = _hash(target)
            manifest['checkpoints'][phase] = {
                'phase_label': phase,
                'operator_reports_gui_paused': True,
                'operator_reports_same_pause_mem1_mem2': True,
                'operator_observed_displaced_ball': phase == 'POST',
                'operator_reports_same_process': phase == 'POST',
                'operator_reports_same_hole': phase == 'POST',
                'operator_observed_result_visible': phase == 'RESULT',
                'sha256': banks,
            }
        path = p / 'shot-distance-captures-PRIVATE.json'
        path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        return path, manifest

    def test_session_creation_is_unique_and_rejects_reuse(self):
        p = Path(self.session)
        self.assertEqual(p.parent.name, 'captures')
        self.assertEqual(p.parent.parent.name, 'Wii-AI-Golf-Data')
        bad = self.run_ps('New-GolfNativeShotSession.ps1', '-Id', 'rehearsal001')
        self.assertNotEqual(bad.returncode, 0)
        self.assertTrue(p.exists())
        good = self.run_ps('New-GolfNativeShotSession.ps1')
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertNotEqual(good.stdout.strip(), self.session)

    def test_one_pre_is_integrity_checked_but_not_a_shot_pair(self):
        self.save_manifest(['PRE'])
        out = self.run_ps('Test-GolfNativeShotPair.ps1', '-Session', self.session)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('NativeBankLengthsAndSHA256Verified', out.stdout)
        self.assertIn('HasPrePostBanks', out.stdout)
        self.assertIn('False', out.stdout)
        self.assertNotIn(self.session, out.stdout)
        self.assertNotIn('RSPE01', out.stdout)

    def test_pre_post_exact_binary_pair_passes_integrity_only(self):
        self.save_manifest(['PRE', 'POST'])
        out = self.run_ps('Test-GolfNativeShotPair.ps1', '-Session', self.session, '-RequirePost')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('HasPrePostBanks', out.stdout)
        self.assertIn('True', out.stdout)
        self.assertIn('BallWorldXYZOrVelocityVerified', out.stdout)
        self.assertIn('TrainingApproved', out.stdout)
        self.assertNotIn('sha256:', out.stdout.lower())

    def test_require_post_rejects_pre_only_without_inventing_hit(self):
        self.save_manifest(['PRE'])
        out = self.run_ps('Test-GolfNativeShotPair.ps1', '-Session', self.session, '-RequirePost')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('POST', out.stderr)

    def test_hash_mismatch_rejected_without_leaking_bank_bytes(self):
        self.save_manifest(['PRE'])
        with (Path(self.session) / 'PRE-MEM1.bin').open('r+b') as fd:
            fd.seek(120)
            fd.write(b'\x42')
        out = self.run_ps('Test-GolfNativeShotPair.ps1', '-Session', self.session)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('mismatch', out.stderr)
        self.assertNotIn('RSPE01', out.stderr)

    def test_manifest_cannot_authorize_training_or_publication(self):
        path, manifest = self.save_manifest(['PRE'])
        manifest['training_allowed'] = True
        path.write_text(json.dumps(manifest), encoding='utf-8')
        out = self.run_ps('Test-GolfNativeShotPair.ps1', '-Session', self.session)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('Unsupported', out.stderr)

    def test_out_of_order_result_is_rejected(self):
        self.save_manifest(['RESULT'])
        out = self.run_ps('Test-GolfNativeShotPair.ps1', '-Session', self.session)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('phase prefix', out.stderr)

    def test_missing_displacement_attestation_rejected(self):
        path, manifest = self.save_manifest(['PRE', 'POST'])
        manifest['checkpoints']['POST']['operator_observed_displaced_ball'] = False
        path.write_text(json.dumps(manifest), encoding='utf-8')
        out = self.run_ps('Test-GolfNativeShotPair.ps1', '-Session', self.session, '-RequirePost')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('attestations', out.stderr)


if __name__ == '__main__':
    unittest.main()
