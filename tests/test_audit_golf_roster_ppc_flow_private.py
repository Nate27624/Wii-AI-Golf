"""No private ROM/RAM needed. Synthetic PowerPC opcode shapes only."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_golf_roster_ppc_flow_private.py'
spec = importlib.util.spec_from_file_location('roster_ppc_flow', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def dform(op, rt, ra, imm):
    return (op << 26) | (rt << 21) | (ra << 16) | (imm & 0xffff)


def add(dst, ra, rb):
    return (31 << 26) | (dst << 21) | (ra << 16) | (rb << 11) | (266 << 1)


class TestRosterPPCFlow(unittest.TestCase):
    def test_synthetic_strided_both_member_reads(self):
        w = [dform(7, 8, 6, 0xCC), add(9, 8, 10), dform(32, 3, 9, 0x8C),
             dform(36, 3, 9, 0xC8)]
        r = m.analyze_words(w)
        self.assertEqual(r['stride_immediate_0xcc']['mulli'], 1)
        self.assertEqual(r['mulli_sites_with_bounded_index_plus_base_add'], 1)
        self.assertEqual(r['mulli_sites_with_bounded_index_add_then_member_access'], 1)
        self.assertEqual(r['syntactic_candidate_chains']['+0x08C_load'], 1)
        self.assertEqual(r['syntactic_candidate_chains']['+0x0C8_store'], 1)
        self.assertFalse(r['register_receiver_dataflow_proven'])
        self.assertFalse(r['ball_xyz_verified'])

    def test_unrelated_add_not_joined(self):
        w = [dform(7, 8, 6, 0xCC), add(9, 10, 11), dform(32, 3, 9, 0x8C)]
        r = m.analyze_words(w)
        self.assertEqual(r['mulli_sites_with_bounded_index_add_then_member_access'], 0)

    def test_branch_breaks_window(self):
        w = [dform(7, 8, 6, 0xCC), 18 << 26, add(9, 8, 10), dform(32, 3, 9, 0x8C)]
        self.assertEqual(m.analyze_words(w)['mulli_sites_with_bounded_index_plus_base_add'], 0)

    def test_unknown_op_breaks_window(self):
        w = [dform(7, 8, 6, 0xCC), 31 << 26, add(9, 8, 10), dform(32, 3, 9, 0xC8)]
        self.assertEqual(m.analyze_words(w)['mulli_sites_with_bounded_index_plus_base_add'], 0)

    def test_overwrite_kills_lineage(self):
        w = [dform(7, 8, 6, 0xCC), dform(32, 8, 7, 12),
             add(9, 8, 10), dform(32, 3, 9, 0xC8)]
        self.assertEqual(m.analyze_words(w)['mulli_sites_with_bounded_index_plus_base_add'], 0)

    def test_addi_0xcc_not_mulli(self):
        w = [dform(14, 8, 6, 0xCC), dform(32, 3, 9, 0x8C)]
        r = m.analyze_words(w)
        self.assertEqual(r['stride_immediate_0xcc']['addi'], 1)
        self.assertEqual(r['stride_immediate_0xcc']['mulli'], 0)
        self.assertEqual(r['mulli_sites_with_bounded_index_plus_base_add'], 0)

    def test_window_bounds_and_private_flags(self):
        with self.assertRaises(ValueError):
            m.analyze_words([0], lookahead=33)
        with self.assertRaises(ValueError):
            m.analyze_words([])
        r = m.analyze_words([0x60000000])
        self.assertFalse(r['allowed_to_publish'])
        self.assertNotIn('0x60000000', str(r))

    def test_member_offset_without_multiply_is_not_chain(self):
        r = m.analyze_words([dform(32, 3, 9, 0x8C), dform(36, 4, 8, 0xC8)])
        self.assertEqual(r['direct_candidate_member_memory_opcode_counts']['+0x08C_load'], 1)
        self.assertEqual(r['mulli_sites_with_bounded_index_add_then_member_access'], 0)


if __name__ == '__main__':
    unittest.main()
