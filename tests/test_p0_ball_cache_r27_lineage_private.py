"""Synthetic-only test of original PPC Ball cache r27 and r3 argument lineage."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"scripts"/"p0_ball_cache_r27_lineage_private.py"
spec=importlib.util.spec_from_file_location("ball_cache_r27_source",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,rt,ra,off):
    return (op<<26)|(rt<<21)|(ra<<16)|(off&0xFFFF)


def mr(dest,src):
    return (31<<26)|(src<<21)|(dest<<16)|(src<<11)|(444<<1)


def bl(pc,target):
    delta=target-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("Invalid bounded synthetic BL target")
    return (18<<26)|(delta&0x03FFFFFC)|1


def program():
    codes={
        m.FN_START+0x20:mr(27,3),
    }
    for group,offsets in m.GROUPS.items():
        fields=(
            (0xCC,0xD0,0xD4) if group.startswith("CC") else
            (0xF0,0xF4,0xF8) if group.startswith("F0") else
            (0xFC,0x100,0x104))
        for i,(off,disp) in enumerate(zip(offsets,fields)):
            pc=m.SOURCE_BALL+off
            codes[pc]=d(52,0 if group.startswith("CC") else i+1,27,disp)
    for off in m.CALLS:
        pc=m.SOURCE_BALL+off
        codes[pc]=bl(pc,m.FN_START)
        codes[pc-4]=mr(3,31)
    for i,off in enumerate(m.GROUPS["CC_D0_D4"]):
        pc=m.SOURCE_BALL+off
        codes[pc-4]=d(48,0,28,0x30+i*4)
    return codes


def read(mapping):
    return lambda pc:mapping.get(pc,0x60000000)


class BallCacheR27LineageTests(unittest.TestCase):
    def test_mr_is_an_explicit_source_register_move(self):
        x=m.gpr_writers(mr(27,3))
        self.assertEqual(x,[(27,"mr",3,None)])
        self.assertEqual(m.gpr_writers(d(36,27,1,4)),[])

    def test_incoming_r27_source_earlier_than_first_cache_store(self):
        x=m.groups(read(program()))
        report=x["CC_D0_D4"]["source_preceding_r27_definitions"]
        self.assertEqual(report["recognized_candidate_GPR_definition_count"],1)
        item=report["recognized_GPR_definition_sites"][0]
        self.assertEqual(item["syntactic_writer_class"],"mr")
        self.assertEqual(item["source_gpr_if_simple"],3)
        self.assertFalse(item["selected_ball_receiver_ownership_proven"])

    def test_all_three_triplets_remain_same_r27_without_proving_selected_ball(self):
        x=m.groups(read(program()))
        self.assertEqual(set(x),set(m.GROUPS))
        for item in x.values():
            self.assertEqual(item["source_float_store_base_GPR"],27)
            self.assertFalse(item["same_active_selected_Ball_receiver_proven"])

    def test_fpr_nearest_lfs_source_offsets_and_registers(self):
        x=m.groups(read(program()))
        item=x["CC_D0_D4"]["source_nearest_fpr_producers"]
        self.assertEqual([x["classification"] for x in item],
                         ["lfs_or_lfsu"]*3)
        self.assertEqual([x["syntactic_source_displacement"] for x in item],
                         [0x30,0x34,0x38])
        self.assertEqual([x["syntactic_source_base_GPR"] for x in item],
                         [28,28,28])

    def test_two_static_direct_callers_have_simple_r3_arguments(self):
        x=m.caller_arguments(read(program()))
        self.assertEqual(len(x),2)
        self.assertTrue(all(t["exact_source_entry_is_cache_fn_80299C70"]
                            for t in x))
        for t in x:
            a=t["nearest_bounded_r3_argument_assignment"][0]
            self.assertEqual(a["syntactic_writer_class"],"mr")
            self.assertEqual(a["source_GPR_if_simple"],31)
            self.assertFalse(t["actual_runtime_r3_object_identity_proven"])

    def test_branch_before_argument_assignment_abstains(self):
        x=program()
        call=m.SOURCE_BALL+m.CALLS[0]
        x[call-4]=0x48000000
        x[call-8]=mr(3,31)
        results=m.caller_arguments(read(x))
        self.assertEqual(results[0]["bounded_backward_stop_reason"],
                         "intervening_call_branch_or_return_unknown")
        self.assertEqual(results[0]["nearest_bounded_r3_argument_assignment"],[])

    def test_modified_exact_call_to_source_entry_refuses(self):
        x=program()
        call=m.SOURCE_BALL+m.CALLS[0]
        x[call]=bl(call,m.FN_START+4)
        with self.assertRaises(ValueError):
            m.caller_arguments(read(x))

    def test_changed_cache_receiver_register_refuses(self):
        x=program()
        pc=m.SOURCE_BALL+m.GROUPS["CC_D0_D4"][0]
        x[pc]=d(52,0,26,0xCC)
        with self.assertRaises(ValueError):
            m.groups(read(x))

    def test_fpr_control_flow_abstains_on_unknown_producer(self):
        x=program()
        pc=m.SOURCE_BALL+m.GROUPS["CC_D0_D4"][0]
        x[pc-4]=0x48000000
        q=m.scan_fp_origin(read(x),pc)
        self.assertEqual(q["classification"],
                         "abstain_prior_control_transfer")
        self.assertFalse(q["source_float_producer_is_same_object_proven"])

    def test_powerpc_xor_destination_is_ra_not_rs(self):
        # PPC xor r27,r3,r4 encodes rS=3,rA=27,rB=4,XO=316.
        w=(31<<26)|(3<<21)|(27<<16)|(4<<11)|(316<<1)
        self.assertEqual(m.gpr_writers(w),
                         [(27,"X_form_logic_dest_rA",3,None)])
        # Distinguish rS==27 from destination rA=2.
        w2=(31<<26)|(27<<21)|(2<<16)|(4<<11)|(316<<1)
        self.assertFalse(any(t[0]==27 for t in m.gpr_writers(w2)))

    def test_wide_register_restore_does_not_become_receiver_proof(self):
        r=m.gpr_writers(d(46,26,1,0x20))
        self.assertIn((27,"lmw_register_restored_from_memory",None,None),r)
        self.assertTrue(any(t[0]==31 for t in r))

    def test_safe_synthetic_report_rejects_native_physics_promotion(self):
        r=m.inspect(read(program()))
        text=json.dumps(r,sort_keys=True)
        self.assertFalse(r["source_store_base_r27_is_live_selected_ball_proven"])
        self.assertFalse(r["runtime_wood_vs_leaves_branch_or_impact_proven"])
        self.assertFalse(r["training_approved"])
        self.assertNotIn("0x90008000",text)
        self.assertNotIn("original_PPC_word",text)


if __name__=="__main__":
    unittest.main()
