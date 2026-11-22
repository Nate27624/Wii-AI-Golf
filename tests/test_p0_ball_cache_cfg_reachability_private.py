"""Synthetic-only exact original PPC Ball cache bounded CFG branch tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
script=ROOT/"scripts"/"p0_ball_cache_cfg_reachability_private.py"
spec=importlib.util.spec_from_file_location("ball_cache_cfg",script)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,reg,base,offset):
    return (op<<26)|(reg<<21)|(base<<16)|(offset&0xFFFF)


def b(pc,target,link=False):
    delta=target-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("Synthetic direct branch out of range")
    return (18<<26)|(delta&0x03FFFFFC)|int(link)


def bc(pc,target,bo=12,bi=2):
    delta=target-pc
    if delta%4 or not -(1<<15)<=delta<(1<<15):
        raise ValueError("Synthetic conditional branch out of range")
    return (16<<26)|(bo<<21)|(bi<<16)|(delta&0xFFFC)


def original_shape():
    code={
        m.BRANCH_SKIP:b(m.BRANCH_SKIP,m.BRANCH_TARGET),
        m.BASE+0x2FA4:d(32,0,27,0x108),
    }
    for load,store,source,dest in m.source.FIRST_COPY:
        code[m.BASE+load]=d(48,0,3,source)
        code[m.BASE+store]=d(52,0,27,dest)
    for load,fpr,source in m.source.SECOND_LOADS:
        code[m.BASE+load]=d(48,fpr,27,source)
    for store,fpr,dest in m.source.SECOND_STORES:
        code[m.BASE+store]=d(52,fpr,27,dest)
    return code


def read(code):
    return lambda pc:code.get(pc,0x60000000)


class BallSourceBoundedCFGTests(unittest.TestCase):
    def test_original_entry_unconditional_branch_skips_both_copy_sites(self):
        report=m.inspect(read(original_shape()))
        self.assertTrue(report["qualified_unconditional_skip"][
            "skips_all_original_CC_and_FC_copy_sites"])
        sites=report["original_key_native_source_site_reachability"]
        self.assertFalse(sites["Ball+0x2D00"][
            "possible_reach_from_published_80299C70_entry_under_bounded_model"])
        self.assertFalse(sites["Ball+0x2FA8"][
            "possible_reach_from_published_80299C70_entry_under_bounded_model"])
        self.assertTrue(sites["Ball+0x2FB8"][
            "possible_reach_from_published_80299C70_entry_under_bounded_model"])
        self.assertFalse(report["native_tree_collision_material_code_proven"])
        self.assertFalse(report["training_approved"])

    def test_back_edge_from_initial_target_reaches_both_original_copies(self):
        code=original_shape()
        code[m.BRANCH_TARGET]=b(m.BRANCH_TARGET,m.BASE+0x2CF8)
        report=m.inspect(read(code))
        sites=report["original_key_native_source_site_reachability"]
        self.assertTrue(sites["Ball+0x2D00"][
            "possible_reach_from_published_80299C70_entry_under_bounded_model"])
        self.assertTrue(sites["Ball+0x2FA8"][
            "possible_reach_from_published_80299C70_entry_under_bounded_model"])
        path=sites["Ball+0x2D00"]["sample_static_branch_route_from_entry"]
        self.assertIn({"source_site":"Ball+0x2FB8",
                       "transfer_kind":"unconditional_b"},path)
        self.assertFalse(sites["Ball+0x2FA8"]["actual_guest_execution_proven"])

    def test_conditional_return_to_cache_can_reach_both_paths(self):
        code=original_shape()
        code[m.BRANCH_TARGET]=bc(m.BRANCH_TARGET,m.BASE+0x2CF8)
        out=m.inspect(read(code))
        self.assertTrue(out["original_key_native_source_site_reachability"][
            "Ball+0x2D04"][
            "possible_reach_from_published_80299C70_entry_under_bounded_model"])
        self.assertGreater(out["bounded_static_graph_branch_syntax_counts"][
            "conditional_bc"],0)

    def test_linked_external_bl_assumed_to_return_to_fallthrough(self):
        code=original_shape()
        code[m.BRANCH_TARGET]=bl=b(m.BRANCH_TARGET,m.BASE+0x28B8,link=True)
        bounded,ext,desc=m.edges(m.BRANCH_TARGET,read(code))
        self.assertEqual(desc["kind"],"direct_bl_call")
        self.assertEqual(bounded,[m.BRANCH_TARGET+4])
        self.assertEqual(ext,[])

    def test_unlinked_external_b_terminates_bounded_path(self):
        code=original_shape()
        code[m.BRANCH_TARGET]=b(m.BRANCH_TARGET,m.BASE+0x28B8)
        out=m.inspect(read(code))
        self.assertGreater(out["bounded_static_graph_external_exit_count"],0)
        self.assertFalse(out["original_key_native_source_site_reachability"][
            "Ball+0x2D04"][
            "possible_reach_from_published_80299C70_entry_under_bounded_model"])

    def test_opaque_bclr_stops_without_false_unreachability_proof(self):
        code=original_shape()
        code[m.BRANCH_TARGET]=(19<<26)|(20<<21)|(16<<1)
        result=m.inspect(read(code))
        self.assertGreater(
            result["bounded_static_graph_unknown_indirect_transfer_count"],0)
        self.assertFalse(result["indirect_calls_or_dynamic_branch_paths_exhausted"])
        self.assertFalse(result["original_key_native_source_site_reachability"][
            "Ball+0x2D00"]["bounded_no_path_proves_true_unreachability"])

    def test_conditional_bclr_keeps_possible_fallthrough_but_unknown_target(self):
        code=original_shape()
        code[m.BRANCH_TARGET]=(19<<26)|(12<<21)|(16<<1)
        within,external,decoded=m.edges(m.BRANCH_TARGET,read(code))
        self.assertEqual(decoded["kind"],"indirect_bclr_or_bcctr")
        self.assertEqual(within,[m.BRANCH_TARGET+4])
        self.assertTrue(decoded["conditional_fallthrough_possible"])
        self.assertFalse(decoded["has_link"])
        self.assertEqual(external,[])
        r=m.inspect(read(code))
        self.assertGreater(r["bounded_static_graph_unknown_indirect_transfer_count"],0)
        self.assertFalse(r["indirect_calls_or_dynamic_branch_paths_exhausted"])

    def test_changed_unconditional_skip_opcode_abstains(self):
        code=original_shape()
        code[m.BRANCH_SKIP]=bc(m.BRANCH_SKIP,m.BRANCH_TARGET)
        with self.assertRaises(ValueError):
            m.inspect(read(code))

    def test_changed_unconditional_skip_target_abstains(self):
        code=original_shape()
        code[m.BRANCH_SKIP]=b(m.BRANCH_SKIP,m.BRANCH_TARGET+4)
        with self.assertRaises(ValueError):
            m.inspect(read(code))

    def test_relative_signed_negative_branch_offsets(self):
        site=m.BASE+0x2FB8
        breg=b(site,m.BASE+0x2CF8)
        decoded=m.decode_transfer(site,breg)
        self.assertEqual(decoded["target"],m.BASE+0x2CF8)
        self.assertEqual(decoded["kind"],"unconditional_b")
        self.assertEqual(m.signed(0xFFFC,16),-4)

    def test_direct_inbound_census_source_only_no_dynamic_execution(self):
        original=original_shape()
        found=m.nearby_public_branches(
            read(original),m.BASE+0x2C98,m.BASE+0x2FD0,
            (m.BRANCH_TARGET,))
        item=found["Ball+0x2FB8"]
        self.assertEqual(item["direct_branch_source_count"],1)
        self.assertEqual(
            item["bounded_original_direct_predecessor_sites"][0][
                "original_Ball_source_relative_site"],"Ball+0x2CCC")
        self.assertFalse(item["indirect_predecessors_exhausted"])

    def test_bounded_cfg_rejects_outside_or_oversized_ranges(self):
        with self.assertRaises(ValueError):
            m.explore(read({}),m.LO,m.HI,m.LO-4)
        with self.assertRaises(ValueError):
            m.explore(read({}),m.LO,m.HI+0x20000,m.LO)

    def test_original_sha_static_report_omits_raw_native_values(self):
        outcome=m.inspect(read(original_shape()))
        content=json.dumps(outcome,sort_keys=True)
        self.assertNotIn("original_ppc_instruction_word",content)
        self.assertNotIn("0x90008000",content)
        self.assertNotIn("raw_source_bytes",content)
        self.assertFalse(outcome["selected_Ball_receiver_or_source_object_verified"])
        self.assertFalse(outcome["original_guest_impact_frame_verified"])


if __name__=="__main__":
    unittest.main()
