"""Synthetic original PPC source-register context tests, no private ROM."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"scripts"/"p0_tree_ball_writer_register_context_private.py"
spec=importlib.util.spec_from_file_location("original_writer_context",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,t,a,off):
    return (op<<26)|(t<<21)|(a<<16)|(off&0xffff)


def code_map():
    code={}
    for name,(unit,offs,fields) in m.TRIPLETS.items():
        for i,(site,offset) in enumerate(zip(offs,fields)):
            code[m.srcpc(unit,site)]=d(52,i+1,31,offset)
    for name,(unit,load,stores) in m.POINTER_WRITERS.items():
        code[m.srcpc(unit,load)]=d(32,7,31,0x4C)
        for i,site in enumerate(stores):
            code[m.srcpc(unit,site)]=d(52,i+1,7,4*i)
    return code


def read(code):
    return lambda pc:code.get(pc,0x60000000)


def bl(pc,dest):
    delta=dest-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("Synthetic branch out of signed PPC range")
    return (18<<26)|(delta&0x03FFFFFC)|1


class OriginalPpcRegisterContextTests(unittest.TestCase):
    def test_eight_triplets_have_complete_exact_fields_and_same_base(self):
        out=m.direct_triplets(read(code_map()))
        self.assertEqual(len(out),8)
        self.assertTrue(all(
            t["all_three_stores_use_same_register"] for t in out.values()))
        self.assertEqual(
            out["Ball_cache_CC_D0_D4_in_fn_80299C70"]["member_displacements"],
            ["+0x0CC","+0x0D0","+0x0D4"])
        self.assertEqual(
            out["Ball_cache_F0_F4_F8_in_fn_80299C70"]["member_displacements"],
            ["+0x0F0","+0x0F4","+0x0F8"])
        self.assertFalse(
            out["Ball_cache_FC_100_104_in_fn_80299C70"][
                "store_receiver_is_selected_active_Ball_proven"])

    def test_syntactically_distinct_registers_keep_receiver_unproven(self):
        code=code_map()
        site=m.srcpc("Ball",0x2D0C)
        code[site]=d(52,2,30,0xD0)
        out=m.direct_triplets(read(code))
        self.assertFalse(out["Ball_cache_CC_D0_D4_in_fn_80299C70"][
            "all_three_stores_use_same_register"])
        self.assertFalse(out["Ball_cache_CC_D0_D4_in_fn_80299C70"][
            "store_receiver_is_selected_active_Ball_proven"])

    def test_wrong_source_displacement_abstains(self):
        code=code_map()
        site=m.srcpc("Ball",0x2D14)
        code[site]=d(52,3,31,0xD8)
        with self.assertRaises(ValueError):
            m.direct_triplets(read(code))

    def test_register_provenance_nearest_lfs_is_only_syntax(self):
        code=code_map()
        site=m.srcpc("Ball",0x2D04)
        code[site-4]=d(48,1,3,0x48)
        result=m.direct_triplets(read(code))
        producer=result["Ball_cache_CC_D0_D4_in_fn_80299C70"][
            "nearest_linear_fpr_producer_syntax"][0]
        self.assertEqual(producer["classification"],"lfs")
        self.assertEqual(
            producer["source_site_delta_instructions_before_store"],1)
        self.assertFalse(producer["op_is_definite_last_dynamic_producer"])

    def test_control_transfer_blocks_linear_fpr_lookup(self):
        code=code_map()
        site=m.srcpc("Ball",0x2D04)
        code[site-8]=d(48,1,3,0x48)
        code[site-4]=0x48000000
        item=m.direct_triplets(read(code))[
            "Ball_cache_CC_D0_D4_in_fn_80299C70"][
            "nearest_linear_fpr_producer_syntax"][0]
        self.assertEqual(item["classification"],"unresolved_prior_control_flow")

    def test_seven_pointer_syntax_candidates_validate_same_loaded_gpr(self):
        out=m.pointer_chains(read(code_map()))
        self.assertEqual(len(out),7)
        self.assertTrue(all(
            item["all_three_component_store_bases_match_loaded_ptr"]
            for item in out.values()))
        self.assertFalse(any(
            item["source_receiver_equals_active_live_Ball_proven"]
            for item in out.values()))

    def test_pointer_register_known_clobber_demotes_consistent_syntax(self):
        code=code_map()
        # This instruction writes r7 between the source pointer load
        # and the three stores. Even if stores use r7, its origin is lost.
        pc=m.srcpc("Ball",0x178C)
        code[pc]=d(14,7,6,8)
        item=m.pointer_chains(read(code))["Ball_ptr_writer_1788"]
        self.assertTrue(item[
            "control_or_known_gpr_clobber_between_load_and_last_store"])
        self.assertFalse(item["source_receiver_equals_active_live_Ball_proven"])

    def test_changed_pointer_load_abstains(self):
        code=code_map()
        code[m.srcpc("Ball",0x1788)]=d(32,7,31,0x50)
        with self.assertRaises(ValueError):
            m.pointer_chains(read(code))

    def test_two_direct_entry_call_targets_are_static_only(self):
        code=code_map()
        start=m.srcpc("Ball",0x230)
        dest=m.ENTRY_TARGETS["ball_cache_fn_80299C70"]
        code[start]=bl(start,dest)
        player=m.srcpc("Player",0x400)
        code[player]=bl(player,m.ENTRY_TARGETS[
            "player_translation_fn_802A0320"])
        found=m.entry_callsites(read(code))
        self.assertEqual(
            found["ball_cache_fn_80299C70"][
                "qualified_direct_bl_to_exact_entry_count"],1)
        self.assertEqual(
            found["player_translation_fn_802A0320"][
                "qualified_direct_bl_to_exact_entry_count"],1)
        self.assertFalse(
            found["ball_cache_fn_80299C70"][
                "executed_for_current_selected_Ball_proven"])

    def test_bounded_source_code_output_has_no_original_game_bytes(self):
        result=m.inspect(read(code_map()))
        serial=json.dumps(result,sort_keys=True)
        self.assertNotIn("original_ppc_words",serial)
        self.assertNotIn("0x9000",serial)
        self.assertNotIn("MEM2_original_heap_address",serial)
        self.assertFalse(result["selected_ball_receiver_binding_proven"])
        self.assertFalse(result["training_approved"])

    def test_public_unit_offset_outside_bounds_abstains(self):
        with self.assertRaises(ValueError):
            m.srcpc("Ball",0xFFFFF)
        with self.assertRaises(ValueError):
            m.srcpc("Player",-4)


if __name__=="__main__":
    unittest.main()
