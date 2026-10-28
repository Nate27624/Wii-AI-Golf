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

    def test_lmw_stops_unknown_multi_register_clobber(self):
        w = [dform(7, 8, 6, 0xCC), dform(46, 8, 7, 0),
             add(9, 8, 10), dform(32, 3, 9, 0x8C)]
        self.assertEqual(m.analyze_words(w)['mulli_sites_with_bounded_index_plus_base_add'], 0)

    def test_joined_zero_offset_load(self):
        w = [dform(7, 8, 6, 0xCC), add(9, 8, 10), dform(32, 3, 9, 0)]
        r = m.analyze_words(w)
        self.assertEqual(r['post_join_site_shape_counts']['joined_zero_offset_memory_load'], 1)
        self.assertEqual(r['mulli_sites_with_bounded_index_add_then_member_access'], 0)

    def test_member_addi_then_zero_load(self):
        w = [dform(7, 8, 6, 0xCC), add(9, 8, 10),
             dform(14, 11, 9, 0x8C), dform(32, 3, 11, 0)]
        r = m.analyze_words(w)
        self.assertEqual(r['post_join_site_shape_counts']['joined_plus_candidate_member_addi'], 1)
        self.assertEqual(r['post_join_site_shape_counts']['joined_addi_member_then_zero_memory_load'], 1)

    def test_joined_indexed_load(self):
        # PPC lwzx r3, r9, r11; X-form XO 23.
        lwzx = (31 << 26) | (3 << 21) | (9 << 16) | (11 << 11) | (23 << 1)
        w = [dform(7, 8, 6, 0xCC), add(9, 8, 10), lwzx]
        r = m.analyze_words(w)
        self.assertEqual(r['post_join_site_shape_counts']['joined_indexed_memory_load'], 1)
        self.assertEqual(r['joined_site_trace_stop_reason_counts']['window_end'], 1)

    def test_joined_unknown_instruction_is_stop_not_receiver_proof(self):
        w = [dform(7, 8, 6, 0xCC), add(9, 8, 10),
             (31 << 26), dform(32, 3, 9, 0)]
        r = m.analyze_words(w)
        self.assertEqual(r['joined_site_trace_stop_reason_counts']['unsupported_ppc_opcode'], 1)
        self.assertEqual(r['post_join_site_shape_counts']['joined_zero_offset_memory_load'], 0)
        self.assertFalse(r['index_provenance_and_receiver_identity_verified'])

    def test_site_diagnostic_unsupported_family_and_addi_immediate(self):
        w = [dform(7, 8, 6, 0xCC), add(9, 8, 10),
             dform(14, 11, 9, 0x48), (31 << 26) | (444 << 1)]
        r = m.analyze_words(w)
        sites = r['bounded_mulli_site_diagnostics']
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0]['mulli_site_ordinal'], 1)
        self.assertTrue(sites[0]['bounded_addition_found'])
        self.assertEqual(sites[0]['post_join_addi_immediates'], ['+0x48'])
        self.assertEqual(sites[0]['stop_reason'], 'unsupported_ppc_opcode')
        self.assertEqual(sites[0]['stop_instruction_family'], 'primary31_xo444')
        self.assertFalse(r['register_receiver_dataflow_proven'])

    def test_site_diagnostic_branch_and_no_raw_code_word(self):
        w = [dform(7, 8, 6, 0xCC), add(9, 8, 10), 18 << 26]
        r = m.analyze_words(w)
        site = r['bounded_mulli_site_diagnostics'][0]
        self.assertEqual(site['stop_reason'], 'branch_before_complete_trace')
        self.assertEqual(site['stop_instruction_family'], 'primary_18')
        self.assertNotIn('0x7C000378', str(site))
        self.assertFalse(r['ball_xyz_verified'])

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
