"""Synthetic-only native original Ball source-global and caller register tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"scripts"/"p0_ball_cc_global_caller_source_private.py"
spec=importlib.util.spec_from_file_location("native_cache_source_global",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,t,base,off):
    return (op<<26)|(t<<21)|(base<<16)|(off&0xffff)


def mr(dest,src):
    return (31<<26)|(src<<21)|(dest<<16)|(src<<11)|(444<<1)


def bl(pc,target):
    delta=target-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("Invalid native synthetic direct branch")
    return (18<<26)|(delta&0x03FFFFFC)|1


def program():
    a={
        m.BASE+m.copy.MOVE:mr(27,3),
        m.BASE+m.GLOBAL_LOADS[0]:d(32,3,13,m.SOURCE_SLOT_DISP),
        m.BASE+m.GLOBAL_LOADS[1]:d(32,3,13,m.SOURCE_SLOT_DISP),
        m.BASE+m.DEREF:d(32,3,3,0x4C),
        m.BASE+0x2FA4:d(32,0,27,0x108),
    }
    for load,store,src,dst in m.copy.FIRST_COPY:
        a[m.BASE+load]=d(48,0,3,src)
        a[m.BASE+store]=d(52,0,27,dst)
    for load,fpr,offset in m.copy.SECOND_LOADS:
        a[m.BASE+load]=d(48,fpr,27,offset)
    for store,fpr,offset in m.copy.SECOND_STORES:
        a[m.BASE+store]=d(52,fpr,27,offset)
    for item in m.CALLERS:
        a[m.BASE+item["bind"]]=mr(31,3)
        a[m.BASE+item["arg"]]=mr(3,31)
        pc=m.BASE+item["bl"]
        a[pc]=bl(pc,m.ENTRY)
    return a


def read(program):
    return lambda pc:program.get(pc,0x60000000)


class OriginalSourceGlobalCacheTests(unittest.TestCase):
    def test_original_global_load_and_pointer_deref_strict_sequence(self):
        r=m.exact_source_pointer(read(program()))
        self.assertTrue(r["exact_second_global_load_followed_by_member_deref_and_lfs"])
        self.assertEqual(r["global_slot_source_base_gpr"],13)
        self.assertEqual(r["global_slot_source_signed_displacement"],-23304)
        self.assertEqual(r["source_member_pointer_displacement"],"+0x04C")
        self.assertTrue(r["r3_from_static_global_pointer_not_incoming_receiver_at_CC_source"])
        self.assertFalse(r["global_object_is_selected_live_Ball_proven"])

    def test_original_statically_copied_CC_and_FC_without_Ball_promotion(self):
        result=m.analyze(read(program()))
        self.assertTrue(result["source_0xCC_copy_from_pointer_target_verified"])
        self.assertTrue(result["source_0xFC_static_copy_from_0xCC_verified"])
        self.assertFalse(result["selected_live_Ball_as_cache_destination_verified"])
        self.assertFalse(result["selected_live_Ball_as_global_source_verified"])
        self.assertFalse(result["training_approved"])

    def test_first_global_load_changed_refuses(self):
        p=program()
        p[m.BASE+m.GLOBAL_LOADS[0]]=d(32,3,13,-23308)
        with self.assertRaises(ValueError):
            m.exact_source_pointer(read(p))

    def test_source_global_pointer_deref_wrong_member_refuses(self):
        p=program()
        p[m.BASE+m.DEREF]=d(32,3,3,0x50)
        with self.assertRaises(ValueError):
            m.exact_source_pointer(read(p))

    def test_original_direct_caller_bind_and_argument_sequences(self):
        x=m.caller_receiver_lifetime(read(program()))
        self.assertEqual(len(x),2)
        self.assertEqual(
            [r["original_receiver_saved_from_r3_site"] for r in x],
            ["Ball+0x2B08","Ball+0x2C5C"])
        self.assertTrue(all(
            r["recognized_register_syntax_unchanged_in_bounded_linear_source"]
            for r in x))
        self.assertFalse(x[0]["source_original_caller_entry_r3_is_selected_Ball_proven"])

    def test_r31_reassignment_downgrades_receiver_chain(self):
        p=program()
        p[m.BASE+0x2B70]=mr(31,4)
        x=m.caller_receiver_lifetime(read(p))
        self.assertFalse(x[0][
            "recognized_register_syntax_unchanged_in_bounded_linear_source"])
        self.assertTrue(len(x[0][
            "recognized_r31_redefinitions_between_bind_and_call"])>=1)
        self.assertFalse(x[0]["source_r31_preservation_all_CFG_paths_proven"])

    def test_r3_overwritten_after_argument_move_downgrades(self):
        p=program()
        p[m.BASE+0x2B84]=d(32,3,3,0x60)
        x=m.caller_receiver_lifetime(read(p))
        self.assertFalse(x[0][
            "recognized_register_syntax_unchanged_in_bounded_linear_source"])

    def test_wrong_original_r31_bind_abstains(self):
        p=program()
        p[m.BASE+0x2B08]=mr(31,4)
        with self.assertRaises(ValueError):
            m.caller_receiver_lifetime(read(p))

    def test_wrong_direct_BL_target_abstains(self):
        p=program()
        at=m.BASE+0x2C80
        p[at]=bl(at,m.ENTRY+4)
        with self.assertRaises(ValueError):
            m.caller_receiver_lifetime(read(p))

    def test_conditional_and_direct_branch_decode_relative_only(self):
        p=program()
        pc=m.BASE+0x2CCC
        # Native bc BO=12, BI=2, BD=+0x10, not an executed path.
        p[pc]=(16<<26)|(12<<21)|(2<<16)|0x0010
        q=m.branch(read(p),0x2CCC)
        self.assertEqual(q["source_branch_kind"],"conditional_bc")
        self.assertEqual(q["destination_ball_unit_relative"],"+0x2CDC")
        self.assertEqual(q["conditional_BO"],12)
        self.assertFalse(q["branch_direction_or_dynamic_execution_proven"])
        at=m.BASE+0x2CDC
        p[at]=bl(at,m.ENTRY)
        q=m.branch(read(p),0x2CDC)
        self.assertEqual(q["source_branch_kind"],"direct_b_or_bl")
        self.assertTrue(q["link_bit"])

    def test_native_negative_displacement_sign_extend(self):
        self.assertEqual(m.decode_signed(0xFFF0,16),-16)
        self.assertEqual(m.decode_signed(0x3FFFFFC,26),-4)

    def test_report_does_not_export_raw_rom_pointer_or_xyz(self):
        result=m.analyze(read(program()))
        s=json.dumps(result,sort_keys=True)
        self.assertNotIn("0x90008000",s)
        self.assertNotIn("original_PPC_instruction_word",s)
        self.assertNotIn("source_native_heap_address",s)
        self.assertFalse(result["wood_vs_foliage_tree_collision_branch_verified"])


if __name__=="__main__":
    unittest.main()
