"""Synthetic fixture tests only; do not treat them as live Dolphin validation."""
from pathlib import Path
import importlib.util
import struct
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'probe_scene_id_dump.py'
spec = importlib.util.spec_from_file_location('scene_id_dump', MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SceneIdDumpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.mem1 = Path(self.temp.name) / 'mem1.bin'
        self.mem2 = Path(self.temp.name) / 'mem2.bin'
        with self.mem1.open('wb') as f:
            f.truncate(mod.MEM1_SIZE)
        with self.mem2.open('wb') as f:
            f.truncate(mod.MEM2_SIZE)
        self.write(0x80000000, b'RSPE')
        self.write(0x80000007, b'\x01')

    def write(self, addr, payload):
        if isinstance(payload, int):
            payload = struct.pack('>I', payload)
        if mod.MEM1_BASE <= addr < mod.MEM1_BASE+mod.MEM1_SIZE:
            path, offset = self.mem1, addr-mod.MEM1_BASE
        else:
            path, offset = self.mem2, addr-mod.MEM2_BASE
        with path.open('r+b') as f:
            f.seek(offset)
            f.write(payload)

    def good(self, mgr=0x90001000, scene=0x90002000, scene_id=5, slot=0x804BF4D8):
        self.write(slot, mgr)
        self.write(mgr + 0x0C, scene)
        self.write(mgr + 0x18, scene_id)
        self.write(scene + 0x1C, scene_id)
        self.write(scene + 0x20, mgr)

    def scan(self, expected=5):
        with mod.Banks(self.mem1, self.mem2) as b:
            return mod.examine(b, expected)

    def test_rev1_golf_validates_two_independent_scene_ids(self):
        self.good()
        result = self.scan()
        self.assertEqual(result['status'], 'snapshot_consistent_not_runtime_verified')
        self.assertEqual(result['candidate_slots'][0]['scene_id_field_address'], '0x90001018')
        self.assertFalse(result['verified_live'])

    def test_second_sbss_slot_can_contain_singleton(self):
        self.good(slot=0x804BF4DC)
        result = self.scan()
        self.assertEqual(result['candidate_slots'][1]['status'], 'source_layout_consistent')

    def test_wrong_scene_refused(self):
        self.good(scene_id=9)
        self.assertEqual(self.scan()['status'], 'no_consistent_slot')
        self.assertEqual(self.scan(expected=9)['status'], 'snapshot_consistent_not_runtime_verified')

    def test_wrong_game_or_revision_refused(self):
        self.good()
        self.write(0x80000007, b'\x00')
        with self.assertRaises(mod.DumpError):
            self.scan()

    def test_scene_object_mismatch_refused(self):
        self.good()
        self.write(0x9000201C, 4)
        self.assertEqual(self.scan()['status'], 'no_consistent_slot')

    def test_backpointer_mismatch_refused(self):
        self.good()
        self.write(0x90002020, 0x80001000)
        self.assertEqual(self.scan()['status'], 'no_consistent_slot')

    def test_out_of_bounds_pointer_refused(self):
        self.good()
        self.write(0x804BF4D8, 0xFFFFFFFF)
        self.assertEqual(self.scan()['status'], 'no_consistent_slot')

    def test_ambiguous_two_slots_refused(self):
        self.good()
        self.good(mgr=0x90003000,scene=0x90004000,slot=0x804BF4DC)
        self.assertEqual(self.scan()['status'], 'ambiguous_multiple_slots')

    def test_truncated_bank_refused(self):
        self.mem2.write_bytes(b'')
        with self.assertRaises(mod.DumpError):
            mod.Banks(self.mem1, self.mem2)

    def test_no_writes_to_dumps(self):
        self.good()
        before = (self.mem1.stat().st_mtime_ns, self.mem2.stat().st_mtime_ns)
        self.scan()
        self.assertEqual(before,(self.mem1.stat().st_mtime_ns, self.mem2.stat().st_mtime_ns))

if __name__ == '__main__':
    unittest.main()
