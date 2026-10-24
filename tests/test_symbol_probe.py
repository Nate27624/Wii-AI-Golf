"""Symbol hints are version-gated and tested against fake bytes only."""
import unittest
from wii_ai_golf.symbol_probe import STATIC, probe_rev1


class Mock:
    def __init__(self, game=b"RSPE01\x00\x01"):
        self.game = game
        self.queries = []
        self.pointers = {
            0x804BF8C4: 0x80500000,
            0x804BF868: 0x80510000,
            0x804BF708: 0x80520000,
        }

    def call(self, name, args):
        self.queries.append((name, args))
        if name == "memory.read_bytes":
            assert args == [0x80000000, 8]
            return self.game.hex()
        if name == "memory.read_u32":
            return self.pointers.get(args[0], 0x13)
        raise AssertionError(name)


class SymbolProbeTests(unittest.TestCase):
    def test_wrong_region_never_reads_structs(self):
        bridge = Mock(b"RSPP01\x00\x01")
        result = probe_rev1(bridge)
        self.assertFalse(result["supported"])
        self.assertEqual(len(bridge.queries), 1)

    def test_wrong_revision_never_reads_structs(self):
        bridge = Mock(b"RSPE01\x00\x00")
        result = probe_rev1(bridge)
        self.assertFalse(result["supported"])
        self.assertEqual(len(bridge.queries), 1)

    def test_version_gated_raw_pointers(self):
        bridge = Mock()
        result = probe_rev1(bridge)
        self.assertTrue(result["supported"])
        self.assertEqual(set(result["fields"]), set(STATIC))
        self.assertEqual(result["fields"]["golf_config"]["instance_pointer"], "0x80500000")
        self.assertIn("hole_raw", result["fields"]["golf_config"]["raw_fields"])
        self.assertEqual(result["fields"]["golf_field"]["raw_fields"]["current_pin_obj_ptr"]["offset"], "+0x44")
        self.assertFalse(any("write" in name for name, _ in bridge.queries))

    def test_invalid_pointer_not_dereferenced(self):
        bridge = Mock()
        bridge.pointers[0x804BF868] = 0xFFFFFFFF
        result = probe_rev1(bridge)
        self.assertFalse(result["fields"]["golf_field"]["plausible_mem_pointer"])
        self.assertEqual(result["fields"]["golf_field"]["raw_fields"], {})


if __name__ == "__main__":
    unittest.main()
