"""Synthetic-only source 94-tree firstword and Ball indirect dispatch tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"
TESTS=ROOT/"tests"
sys.path.insert(0,str(SCRIPTS))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m=load("tree_indirect",SCRIPTS/"p0_tree_ball_indirect_dispatch_private.py")
prior=load("active_fixture",TESTS/"test_p0_ball_kcol_active_resource_private.py")


TREE_OBJECT=0x90000100
TABLE=0x80000200


def fixture():
    words,read=prior.source_fixture()
    # Synthetic native FieldManager 94x84 tree loop: the new analyzer
    # also gates the original loop; fixture must supply those words.
    loop=m.native.LOOP
    words[loop+0x06E8]=(32<<26)|(0<<21)|(28<<16)|0x20
    pc=loop+0x06F0
    target=m.native.UNITS["Tree"][0]+0x000C
    words[pc]=(18<<26)|((target-pc)&0x03FFFFFC)|1
    words[loop+0x06F4]=(14<<26)|(31<<21)|(31<<16)|84
    words[loop+0x06FC]=(32<<26)|(0<<21)|(28<<16)|0x1C
    ram={}
    for i in range(94):
        ram[TREE_OBJECT+i*84]=TABLE
    ram[TABLE+0]=m.native.UNITS["Tree"][0]+0x10
    ram[TABLE+4]=m.native.UNITS["Ball"][0]+0x20
    ram[TABLE+8]=m.native.UNITS["FieldManager"][0]+0x30
    def u32(pc):
        return ram.get(pc,0)
    def bank(pc,n):
        if 0x80000000<=pc and pc+n<=0x81800000:
            return "MEM1"
        if 0x90000000<=pc and pc+n<=0x94000000:
            return "MEM2"
        return None
    return words,read,ram,u32,bank


class TreeBallIndirectDispatchTests(unittest.TestCase):
    def test_all_94_shared_table_and_method_candidates(self):
        _,_,_,u32,bank=fixture()
        r=m.inspect_tree_firstword(u32,TREE_OBJECT,94,bank)
        self.assertTrue(r["all_94_tree_firstwords_identical"])
        self.assertEqual(r["table_slots_inspected"],64)
        self.assertEqual(len(r["source_relative_candidate_entries"]),3)
        self.assertEqual(r["public_unit_target_counts"]["Tree"],1)
        self.assertFalse(r["firstword_is_vtable_proven"])
        self.assertFalse(r["candidate_target_is_tree_collision_handler_proven"])

    def test_one_tree_firstword_change_abstains(self):
        _,_,ram,u32,bank=fixture()
        ram[TREE_OBJECT+5*84]=TABLE+4
        with self.assertRaises(ValueError):
            m.inspect_tree_firstword(u32,TREE_OBJECT,94,bank)

    def test_tree_count_and_bank_abstain(self):
        _,_,_,u32,bank=fixture()
        with self.assertRaises(ValueError):
            m.inspect_tree_firstword(u32,TREE_OBJECT,93,bank)
        with self.assertRaises(ValueError):
            m.inspect_tree_firstword(u32,0x80001000,94,bank)

    def test_one_native_bctrl_has_mtctr_syntax(self):
        words,read,_,_,_=fixture()
        ball=m.native.UNITS["Ball"][0]
        words[ball+0x1200]=0x7D8903A6  # mtspr CTR,r12
        words[ball+0x1208]=0x4E800421  # bctrl
        result=m.inspect_indirect_calls(read)
        r=next(x for x in result["per_unit"] if x["source_unit"]=="Ball")
        self.assertEqual(r["indirect_call_total"],1)
        self.assertEqual(r["sites"][0]["source_relative_site"],"+0x1208")
        self.assertEqual(r["sites"][0]["nearby_mtctr_syntax_at_relative_site"],"-0x08")
        self.assertFalse(r["sites"][0]["CTR_reaching_target_or_tree_receiver_proven"])

    def test_source_validated_bounded_detail_output(self):
        words,read,ram,u32,bank=fixture()
        ball=m.native.UNITS["Ball"][0]
        words[ball+0x1200]=0x7D8903A6
        words[ball+0x1208]=0x4E800421
        compact=m.inspect(read,u32,TREE_OBJECT,94,bank,False)
        detailed=m.inspect(read,u32,TREE_OBJECT,94,bank,True)
        self.assertTrue(compact["original_native_ball_kcol_source_gates"])
        self.assertFalse(compact["tree_collision_receiver_proven"])
        self.assertFalse(compact["training_approved"])
        compact_sites=compact["indirect"]["per_unit"][0]["sites"]
        full_sites=detailed["indirect"]["per_unit"][0]["sites"]
        self.assertFalse(any("operator_local_original_code_context" in x
                             for x in compact_sites))
        self.assertEqual(len(full_sites[0]["operator_local_original_code_context"]),
                         m.PREVIOUS_WORDS+m.FOLLOWING_WORDS+1)
        self.assertLessEqual(detailed["indirect"]["operator_local_detail_windows"],30)

    def test_detail_budget_preserves_fieldmanager_source_context(self):
        words,read,_,_,_=fixture()
        ball=m.native.UNITS["Ball"][0]
        field=m.native.UNITS["FieldManager"][0]
        for i in range(22):
            words[ball+0x1100+i*0x10]=0x4E800421
        words[field+0x1200]=0x4E800421
        result=m.inspect_indirect_calls(read,True)
        ball_sites=next(x["sites"] for x in result["per_unit"]
                        if x["source_unit"]=="Ball")
        field_sites=next(x["sites"] for x in result["per_unit"]
                         if x["source_unit"]=="FieldManager")
        self.assertEqual(sum("operator_local_original_code_context" in s
                             for s in ball_sites),m.MAX_DETAIL_PER_OWNER)
        self.assertEqual(sum("operator_local_original_code_context" in s
                             for s in field_sites),1)
        self.assertLessEqual(result["operator_local_detail_windows"],
                             m.MAX_DETAIL_WINDOWS)

    def test_missing_prism_source_anchor_abstains(self):
        words,read,ram,u32,bank=fixture()
        ball=m.native.UNITS["Ball"][0]
        words[ball+0x0B84]=0
        with self.assertRaises(ValueError):
            m.inspect(read,u32,TREE_OBJECT,94,bank)

    def test_ctr_syntax_not_assumed_receiver_semantics(self):
        words,read,_,_,_=fixture()
        ball=m.native.UNITS["Ball"][0]
        words[ball+0x1208]=0x4E800421
        r=m.inspect_indirect_calls(read)
        self.assertFalse(r["known_tree_method_invoked_from_ball_proven"])
        self.assertFalse(r["indirect_tree_contact_handler_proven"])
        site=r["per_unit"][0]["sites"][0]
        self.assertIsNone(site["nearby_mtctr_syntax_at_relative_site"])


if __name__=="__main__":
    unittest.main()
