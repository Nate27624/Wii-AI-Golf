"""Synthetic-only tests: alias overlap is not independent child-state evidence."""
from pathlib import Path
import importlib.util
import struct
import unittest

script = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_golf_main_aliases.py'
spec = importlib.util.spec_from_file_location('alias_audit', script)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class FakeCaptures:
    names = ('B0', 'B1', 'B2', 'B3')
    main = 0x90010000
    child = 0x90020000
    grandchild = 0x90030000

    def __init__(self):
        self.data = {n: {} for n in self.names}
        for i, n in enumerate(self.names):
            self.put(n, 0x80000000, b'RSPE')
            self.put(n, 0x80000007, b'\x01')
            self.word_put(n, audit.SCENE_MGR_SLOT, 0x80001000)
            self.word_put(n, 0x8000100C, 0x90008000)
            self.word_put(n, 0x80001018, 5)
            self.word_put(n, 0x9000801C, 5)
            self.word_put(n, 0x90008020, 0x80001000)
            self.word_put(n, 0x9000809C, self.main)
            # Repeated aliases of the same source bytes.
            self.word_put(n, self.main + 0x008, self.main + 0x014)
            self.word_put(n, self.main + 0x010, self.main + 0x014)
            self.word_put(n, self.main + 0x024, self.child)
            self.word_put(n, self.main + 0x074, 6000 + i)
            self.word_put(n, self.main + 0x1DC, (1 if i == 2 else 0))
            self.word_put(n, self.child + 0x100, i + 42)
            self.word_put(n, self.child + 0x000, self.grandchild)
            self.word_put(n, self.grandchild + 0x020, i + 100)

    def put(self, n, addr, data):
        for i, val in enumerate(data):
            self.data[n][addr+i] = val

    def word_put(self, n, addr, value):
        self.put(n, addr, struct.pack('>I', value))

    def read(self, n, addr, size):
        return bytes(self.data[n].get(addr+i, 0) for i in range(size))

    def word(self, n, addr):
        return struct.unpack('>I', self.read(n, addr, 4))[0]

    def valid(self, addr, size):
        return audit.Captures.valid(addr, size)

    def validate_root(self):
        return self.main


class TestAliasAudit(unittest.TestCase):
    def test_big_endian_changed_word(self):
        fake = FakeCaptures()
        changes = audit.changed_words(fake, fake.main, 512)
        self.assertIn(fake.main + 0x74, changes)
        self.assertEqual(changes[fake.main + 0x74], ['00001770','00001771','00001772','00001773'])

    def test_stable_pointer_dedup(self):
        fake = FakeCaptures()
        pointers = audit.stable_pointers(fake, fake.main, 512)
        aliases = [p for _, p in pointers if p == fake.main + 0x14]
        self.assertEqual(len(aliases), 2)

    def test_self_alias_not_novel_change(self):
        fake = FakeCaptures()
        report = audit.analyze(fake, depth=1)
        self.assertEqual(len(report['root_4k_changed_words']), 2)
        self.assertEqual(report['total_unique_changed_addresses_outside_root'], 1)
        row = next(r for r in report['ranked_pointees']
                   if r['pointee'] == f'0x{fake.main+0x14:08X}')
        self.assertTrue(row['overlaps_4k_root'])
        self.assertEqual(row['changed_words_outside_4k_root'], 0)
        self.assertEqual(len(row['references']), 2)

    def test_second_hop_finds_distinct_region(self):
        fake = FakeCaptures()
        report = audit.analyze(fake, depth=2)
        addresses = {r['address'] for r in report['unique_changed_addresses_outside_root']}
        self.assertIn(f'0x{fake.child+0x100:08X}', addresses)
        self.assertIn(f'0x{fake.grandchild+0x20:08X}', addresses)
        self.assertEqual(report['total_unique_changed_addresses_outside_root'], 2)

    def test_node_limit_fails_closed(self):
        with self.assertRaises(audit.ReadError):
            audit.analyze(FakeCaptures(), depth=1, max_nodes=1)

    def test_bad_snapshot_scene_rejected(self):
        fake = FakeCaptures()
        fake.word_put('B2', 0x9000801C, 9)
        self.assertNotEqual(fake.word('B2', 0x9000801C), 5)


if __name__ == '__main__':
    unittest.main()
