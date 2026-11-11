"""Synthetic-only strict Rev1 PPC CC->FC cache copy/receiver tests."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"scripts"/"p0_ball_cc_fc_copy_receiver_private.py"
spec=importlib.util.spec_from_file_location("ball_copy_receiver",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,rt,ra,offset):
    return op<<26 | rt<<21 | ra<<16 | (offset&65535)


def mr(dest,src):
    return 31<<26 | src<<21 | dest<<16 | src<<11 | 444<<1


def bl(pc,dest):
    delta=dest-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("Synthetic BL out of range")
    return 18<<26 | (delta&0x3FFFFFC) | 1


def program():
    data={}
    data[m.BASE+m.MOVE]=mr(27,3)
    for idx,(load,store,src,dest) in enumerate(m.FIRST_COPY):
        data[m.BASE+load]=d(48,0,3,src)
        data[m.BASE+store]=d(52,0,27,dest)
    for load,fpr,src in m.SECOND_LOADS:
        data[m.BASE+load]=d(48,fpr,27,src)
    for store,fpr,dest in m.SECOND_STORES:
        data[m.BASE+store]=d(52,fpr,27,dest)
    data[m.BASE+0x2FA4]=0x60000000
    for off in m.CALLS:
        pc=m.BASE+off
        data[pc]=bl(pc,m.ENTRY)
        data[pc-4]=mr(3,31)
        data[pc-8]=mr(31,3)
    return data


def read(data):
    return lambda pc:data.get(pc,0x60000000)


class BallCCFCCopyTests(unittest.TestCase):
    def test_six_exact_consecutive_first_source_load_stores(self):
        x=m.check_first_copy(read(program()))
        self.assertTrue(x["exact_consecutive_native_lfs_stfs_triplet"])
        self.assertEqual(
            [n["source_member_displacement"] for n in
             x["source_r3_triplet_to_r27_plus_0xCC_syntax"]],
            ["+0x000","+0x004","+0x008"])
        self.assertEqual(
            [n["destination_member_displacement"] for n in
             x["source_r3_triplet_to_r27_plus_0xCC_syntax"]],
            ["+0x0CC","+0x0D0","+0x0D4"])
        self.assertFalse(x["native_r3_points_to_ball_plus_0x30_proven"])

    def test_nonmatching_source_float_load_abstains(self):
        p=program()
        p[m.BASE+0x2D00]=d(48,0,4,0)
        with self.assertRaises(ValueError):
            m.check_first_copy(read(p))

    def test_wrong_first_store_float_register_abstains(self):
        p=program()
        p[m.BASE+0x2D0C]=d(52,1,27,0xD0)
        with self.assertRaises(ValueError):
            m.check_first_copy(read(p))

    def test_second_copy_loads_source_CC_and_stores_dest_FC(self):
        x=m.check_second_copy(read(program()))
        self.assertTrue(x["exact_load_store_triplets_verified"])
        self.assertFalse(x["native_static_copy_of_CC_to_FC_verified"])
        self.assertEqual(x["intervening_instruction_type"],
                         "noncontrol_nonrecognized_clobber")

    def test_second_copy_prior_FP_clobber_abstains(self):
        p=program()
        p[m.BASE+0x2FA4]=d(48,2,31,0x10)
        with self.assertRaises(ValueError):
            m.check_second_copy(read(p))

    def test_second_copy_source_cache_write_abstains(self):
        p=program()
        p[m.BASE+0x2FA4]=d(52,1,27,0xCC)
        with self.assertRaises(ValueError):
            m.check_second_copy(read(p))

    def test_second_copy_branch_abstains(self):
        p=program()
        p[m.BASE+0x2FA4]=0x48000000
        with self.assertRaises(ValueError):
            m.check_second_copy(read(p))

    def test_r27_prologue_mr_r3_and_local_r3_reassignment(self):
        p=program()
        p[m.BASE+0x2CE8]=d(14,3,27,0x30)
        x=m.r3_between_entry_and_cc(read(p))
        self.assertEqual(x["entry_source_r27_mr_r3_site"],"Ball+0x2CB8")
        self.assertEqual(x[
            "source_r3_writes_after_r27_binding_before_first_CC_source_load"][0][
            "syntactic_writer_class"],"addi")
        self.assertFalse(x["source_r3_at_CC_load_is_selected_ball_pointer_proven"])

    def test_modified_original_r27_move_abstains(self):
        p=program()
        p[m.BASE+m.MOVE]=mr(27,4)
        with self.assertRaises(ValueError):
            m.r3_between_entry_and_cc(read(p))

    def test_two_direct_callers_are_exact_and_candidate_r31_defs_only(self):
        x=m.caller_r31_recent_defs(read(program()))
        self.assertEqual(len(x),2)
        self.assertTrue(all(y["closest_r31_definition_candidate"] is not None
                            for y in x))
        self.assertFalse(x[0]["source_r31_definitely_same_this_pointer_through_call"])

    def test_static_direct_call_changed_abstains(self):
        p=program()
        call=m.BASE+m.CALLS[0]
        p[call]=bl(call,m.ENTRY+4)
        with self.assertRaises(ValueError):
            m.caller_r31_recent_defs(read(p))

    def test_safe_report_source_only_and_no_impact_claims(self):
        x=m.inspect(read(program()))
        encoded=json.dumps(x,sort_keys=True)
        self.assertNotIn("original_native_word",encoded)
        self.assertNotIn("0x90008000",encoded)
        self.assertNotIn("private_archive_path",encoded)
        self.assertFalse(x["selected_active_ball_receiver_identity_proven"])
        self.assertFalse(x["training_approved"])


if __name__=="__main__":
    unittest.main()
