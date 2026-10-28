"""Synthetic-only tests: never use or publish Nintendo game memory."""
from pathlib import Path
import importlib.util
import struct
import unittest

script = Path(__file__).resolve().parents[1] / 'scripts' / 'triage_golf_float_candidates.py'
spec = importlib.util.spec_from_file_location('float_triage', script)
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)


class FakeBanks:
    names = ['B0', 'B1', 'B2', 'B3']
    root = 0x90010000
    def __init__(self):
        self.memory = {n:{} for n in self.names}
        for i,n in enumerate(self.names):
            self.put(n, triage.FLOAT_REGION, struct.pack('>fff', float(i), float(i*3), 7.5))
    def put(self, name, addr, b):
        for i,v in enumerate(b):
            self.memory[name][addr+i] = v
    def read(self, name, addr, size):
        return bytes(self.memory[name].get(addr+i,0) for i in range(size))
    def valid(self, addr, size):
        return 0x80000000 <= addr and addr+size <= 0x94000000
    def validate_root(self):
        return self.root


def report(b):
    addr = triage.FLOAT_REGION
    return {
        'root_pointer': f'0x{b.root:08X}', 'captures': list(b.names),
        'coverage_status': 'complete',
        'unique_changed_addresses_outside_root': [
            {'address': f'0x{addr:08X}',
             'values': [b.read(n,addr,4).hex().upper() for n in b.names]}],
        'total_unique_changed_addresses_outside_root': 1,
        'ranked_pointees': [
            {'pointee': f'0x{addr-0x20:08X}',
             'references': ['0x80923018+0x030'],
             'changed_words_outside_4k_root': 2}]
    }


class TestFloatTriage(unittest.TestCase):
    def test_two_components_change_third_stable(self):
        b=FakeBanks()
        out=triage.triage(b,report(b))
        center=next(x for x in out['vector_hypotheses']
                    if x['address']==f'0x{triage.FLOAT_REGION:08X}')
        self.assertEqual(center['varying_components_xyz'],[True,True,False])
        self.assertEqual(center['vectors_by_capture']['B2'],[2.0,6.0,7.5])
        self.assertFalse(out['verified_ball_world_xyz'])
        self.assertEqual(out['report_changed_addresses_verified_against_banks'],1)

    def test_stale_report_rejected(self):
        b=FakeBanks()
        r=report(b)
        r['unique_changed_addresses_outside_root'][0]['values'][0]='DEADBEEF'
        with self.assertRaises(ValueError):triage.triage(b,r)

    def test_wrong_root_rejected(self):
        b=FakeBanks();r=report(b);r['root_pointer']='0x90020000'
        with self.assertRaises(ValueError):triage.triage(b,r)

    def test_capture_order_rejected(self):
        b=FakeBanks();r=report(b);r['captures']=list(reversed(b.names))
        with self.assertRaises(ValueError):triage.triage(b,r)

    def test_missing_coverage_rejected(self):
        b=FakeBanks();r=report(b);r.pop('coverage_status')
        with self.assertRaises(ValueError):triage.triage(b,r)

    def test_nonfinite_vector_rejected(self):
        b=FakeBanks()
        for n in b.names:
            b.put(n,triage.FLOAT_REGION+8,struct.pack('>f',float('nan')))
        r=report(b)
        out=triage.triage(b,r)
        self.assertFalse(any(v['address']==f'0x{triage.FLOAT_REGION:08X}'
                             for v in out['vector_hypotheses']))

    def test_source_refs_retained(self):
        b=FakeBanks()
        out=triage.triage(b,report(b))
        self.assertEqual(out['provenance'][0]['source_references'],
                         ['0x80923018+0x030'])


if __name__=='__main__':
    unittest.main()
