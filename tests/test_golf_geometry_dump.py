"""Synthetic-only tee/pin pointer checks; no actual Dolphin memory is included."""
from pathlib import Path
import importlib.util
import struct
import unittest

module = Path(__file__).resolve().parents[1] / 'scripts' / 'probe_golf_geometry_dump.py'
spec = importlib.util.spec_from_file_location('golfgeo', module)
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)

class StubBanks:
    def __init__(self):
        self.data = {}
        self.put(0x80000000, b'RSPE')
        self.put(0x80000007, b'\x01')
        self.u32(geo.FIELD_MANAGER_SINGLETON, 0x90500000)
        self.u32(0x90500000 + geo.CURRENT_PIN, 0x90001000)
        self.u32(0x90500000 + geo.CURRENT_START, 0x90002000)
        self.put(0x90001030, struct.pack('>fff', 1.,2.,3.))
        self.put(0x90002030, struct.pack('>fff', 4.,5.,6.))
    def put(self, address, data):
        for i, v in enumerate(data): self.data[address+i] = v
    def u32(self, address, value): self.put(address, struct.pack('>I', value))
    def read(self, address, size):
        if not (geo.MEM1_BASE <= address and address + size <= geo.MEM1_BASE+geo.MEM1_LEN or geo.MEM2_BASE <= address and address + size <= geo.MEM2_BASE+geo.MEM2_LEN):
            raise geo.DiagnosticError('invalid range')
        return bytes(self.data.get(address+i, 0) for i in range(size))
    def word(self, address):
        return struct.unpack('>I', self.read(address,4))[0]
    def vec3(self, address):
        return list(struct.unpack('>fff', self.read(address,12)))

class TestGeo(unittest.TestCase):
    def test_good_source_candidates(self):
        r = geo.inspect(StubBanks())
        self.assertEqual(r['status'], 'two_candidate_translations_found_not_verified')
        self.assertEqual(r['observations']['pin']['candidate_translation_xyz'], [1.,2.,3.])
        self.assertEqual(r['observations']['start']['candidate_translation_xyz'], [4.,5.,6.])
        self.assertFalse(r['verified_target_xyz'])
    def test_revision_gate(self):
        b=StubBanks(); b.put(0x80000007,b'\x00')
        with self.assertRaises(geo.DiagnosticError):geo.inspect(b)
    def test_null_singleton(self):
        b=StubBanks();b.u32(geo.FIELD_MANAGER_SINGLETON,0)
        with self.assertRaises(geo.DiagnosticError):geo.inspect(b)
    def test_unaligned_pointer(self):
        b=StubBanks();b.u32(0x90500000+geo.CURRENT_START,0x90002003)
        self.assertEqual(geo.inspect(b)['observations']['start']['status'],'rejected')
    def test_nan_floats_rejected(self):
        b=StubBanks();b.put(0x90001030,struct.pack('>fff',float('nan'),0.,0.))
        self.assertEqual(geo.inspect(b)['observations']['pin']['status'],'rejected')
    def test_bad_pointer_range_rejected(self):
        b=StubBanks();b.u32(0x90500000+geo.CURRENT_PIN,0xFFFFFFFF)
        self.assertEqual(geo.inspect(b)['observations']['pin']['status'],'rejected')
    def test_nonfloat_huge_rejected(self):
        b=StubBanks();b.put(0x90001030,struct.pack('>fff',1e30,0.,0.))
        self.assertEqual(geo.inspect(b)['observations']['pin']['status'],'rejected')

    def test_cup_and_targets_are_explicitly_unverified(self):
        b = StubBanks()
        b.u32(0x90500000 + geo.CUP_OBJECT, 0x90003000)
        b.put(0x90003030, struct.pack('>fff', 7., 8., 9.))
        b.u32(0x90500000 + geo.NUM_TARGET_OBJECTS, 2)
        b.u32(0x90500000 + geo.TARGET_OBJECTS_ARRAY, 0x90004000)
        r = geo.inspect(b)
        self.assertEqual(r['optional_context']['cup']['status'], 'unverified_base_layout_hypothesis')
        self.assertEqual(r['optional_context']['cup']['candidate_translation_xyz'], [7., 8., 9.])
        self.assertEqual(r['optional_context']['target_collection']['count_candidate'], 2)
        self.assertFalse(r['verified_target_xyz'])
        self.assertFalse(r['approved_for_training'])
    def test_optional_bad_cup_does_not_invalidate_pin_start(self):
        b = StubBanks()
        b.u32(0x90500000 + geo.CUP_OBJECT, 0xFFFFFFFF)
        r = geo.inspect(b)
        self.assertEqual(r['optional_context']['cup']['status'], 'no_usable_cup_candidate')
        self.assertEqual(r['status'], 'two_candidate_translations_found_not_verified')
    def test_implausible_target_count_rejected(self):
        b = StubBanks()
        b.u32(0x90500000 + geo.NUM_TARGET_OBJECTS, 0xFFFFFFFF)
        r = geo.inspect(b)
        self.assertEqual(r['optional_context']['target_collection']['status'],
                         'no_usable_target_collection')

if __name__=='__main__':unittest.main()
