"""Synthetic-only Rev1 PPC cache branch predicate and CFG witness tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/"scripts"/"p0_ball_cache_backedge_condition_private.py"
spec=importlib.util.spec_from_file_location("ball_source_backedge_cr",source)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def d(op,reg,base,disp):
    return (op<<26)|(reg<<21)|(base<<16)|(disp&65535)


def b(pc,dest,link=False):
    delta=dest-pc
    if delta%4 or not -(1<<25)<=delta<(1<<25):
        raise ValueError("out of synthetic branch range")
    return (18<<26)|(delta&0x03FFFFFC)|int(link)


def bc(pc,dest,bo=12,bi=2):
    delta=dest-pc
    if delta%4 or not -(1<<15)<=delta<(1<<15):
        raise ValueError("out of synthetic conditional branch range")
    return (16<<26)|(bo<<21)|(bi<<16)|(delta&0xFFFC)


def source_code():
    program={
        m.cfg.BRANCH_SKIP:b(m.cfg.BRANCH_SKIP,m.cfg.BRANCH_TARGET),
        m.cfg.BASE+0x2FA4:d(32,0,27,0x108),
        m.cfg.BASE+0x2FC4:bc(m.cfg.BASE+0x2FC4,m.cfg.BASE+0x2FCC,bo=12,bi=2),
        m.cfg.BASE+0x2FCC:bc(m.cfg.BASE+0x2FCC,m.cfg.BASE+0x2CD4,bo=4,bi=2),
        m.cfg.BASE+0x2FC0:d(11,0,27,0),
    }
    for load,store,src,dst in m.cfg.source.FIRST_COPY:
        program[m.cfg.BASE+load]=d(48,0,3,src)
        program[m.cfg.BASE+store]=d(52,0,27,dst)
    for load,fpr,src in m.cfg.source.SECOND_LOADS:
        program[m.cfg.BASE+load]=d(48,fpr,27,src)
    for store,fpr,dst in m.cfg.source.SECOND_STORES:
        program[m.cfg.BASE+store]=d(52,fpr,27,dst)
    return program


def reader(data):
    return lambda pc:data.get(pc,0x60000000)


class OriginalCacheBackedgeConditionTests(unittest.TestCase):
    def test_backedge_classifies_CR_true_and_false_without_dynamic_promotion(self):
        out=m.branch_edges(reader(source_code()),m.BACKEDGE_OFFSETS)
        self.assertEqual(len(out),2)
        self.assertEqual(out[0]["branch_predicate"]["condition_kind"],
                         "branch_when_CR_bit_true")
        self.assertEqual(out[1]["branch_predicate"]["condition_kind"],
                         "branch_when_CR_bit_false")
        self.assertEqual(out[0]["branch_target_relative"],"Ball+0x2FCC")
        self.assertEqual(out[1]["branch_target_relative"],"Ball+0x2CD4")
        self.assertFalse(out[1]["runtime_branch_direction_or_feasibility_proven"])

    def test_bounded_cmpwi_producer_classification(self):
        out=m.branch_edges(reader(source_code()),m.BACKEDGE_OFFSETS)
        cmp=out[0]["bounded_nearest_linear_CR_producer"]
        self.assertEqual(cmp["candidate_source_site"],"Ball+0x2FC0")
        self.assertEqual(cmp["producer"]["syntax"],"cmpi_signed_immediate")
        self.assertEqual(cmp["producer"]["source_gpr_index"],27)
        self.assertFalse(cmp["last_dynamic_CR_producer_proven"])

    def test_static_witness_reaches_both_CC_and_FC_sites(self):
        report=m.inspect(reader(source_code()))
        paths=report["source_witnesses_to_CC_and_FC_copy_sites"]
        self.assertTrue(paths["Ball+0x2D00"]["bounded_may_reach"])
        self.assertTrue(paths["Ball+0x2FA8"]["bounded_may_reach"])
        self.assertTrue(any(
            q["original_branch_site"]=="Ball+0x2FCC"
            for q in paths["Ball+0x2D00"]["witness_control_edges"]))
        self.assertFalse(report["cr_predicate_satisfiability_of_witness_proven"])
        self.assertFalse(report["dynamic_guest_cache_execution_proven"])

    def test_branch_condition_feasibility_not_inferred_from_static_route(self):
        result=m.inspect(reader(source_code()))
        one=result["source_witnesses_to_CC_and_FC_copy_sites"]["Ball+0x2D00"]
        self.assertTrue(one["static_witness_available"])
        self.assertFalse(one["native_guest_execution_of_this_witness_proven"])
        self.assertFalse(result["source_r13_global_is_live_selected_Ball_proven"])

    def test_wrong_backedge_opcode_abstains(self):
        src=source_code()
        src[m.cfg.BASE+0x2FCC]=b(m.cfg.BASE+0x2FCC,m.cfg.BASE+0x2CD4)
        with self.assertRaises(ValueError):
            m.branch_edges(reader(src),m.BACKEDGE_OFFSETS)

    def test_false_CR_flag_changes_possible_route_choice_not_contact(self):
        src=source_code()
        src[m.cfg.BASE+0x2FC4]=bc(m.cfg.BASE+0x2FC4,
                                  m.cfg.BASE+0x2FCC,bo=4,bi=2)
        result=m.inspect(reader(src))
        self.assertTrue(result["static_may_reachability_from_published_entry_verified"])
        self.assertFalse(result["original_wood_or_foliage_collision_branch_verified"])

    def test_cmpli_unsigned_immediate_cr_field(self):
        w=d(10,2<<2,31,0xF000)
        q=m.compare_syntax(w)
        self.assertEqual(q["syntax"],"cmpli_unsigned_immediate")
        self.assertEqual(q["CR_field_index"],2)
        self.assertEqual(q["source_gpr_index"],31)
        self.assertEqual(q["immediate_unsigned_bits"],0xF000)

    def test_andi_dot_reports_cr0_without_claiming_object(self):
        q=m.compare_syntax(d(28,9,8,0x20))
        self.assertEqual(q["CR_field_index"],0)
        self.assertFalse(q["comparison_operands_or_runtime_result_verified"])

    def test_prior_control_transfer_blocks_local_comparison(self):
        source=source_code()
        source.pop(m.cfg.BASE+0x2FC0)
        source[m.cfg.BASE+0x2FBC]=d(11,0,27,0)
        source[m.cfg.BASE+0x2FC0]=b(m.cfg.BASE+0x2FC0,m.cfg.BASE+0x2FCC)
        out=m.prior_compare(reader(source),m.cfg.BASE+0x2FC4,0,m.cfg.LO)
        self.assertEqual(out["blocked_by_prior_control_transfer_site"],"Ball+0x2FC0")
        self.assertFalse(out["last_dynamic_CR_producer_proven"])

    def test_unrecognized_BO_remains_uncertain(self):
        q=m.cr_predicate({"kind":"conditional_bc","BO":0,"BI":7})
        self.assertEqual(q["condition_kind"],"complex_BO_CTR_or_CR_semantics_not_decoded")
        self.assertFalse(q["condition_is_complete_PPC_proof"])

    def test_absent_route_is_not_verified_unreachable(self):
        p=source_code()
        p[m.cfg.BASE+0x2FCC]=bc(m.cfg.BASE+0x2FCC,m.cfg.BASE+0x2FCC+4)
        graph=m.cfg.explore(reader(p))
        out=m.edge_witness(reader(p),graph["parent"],m.cfg.BASE+0x2CD4)
        self.assertFalse(out["bounded_may_reach"])
        self.assertFalse(out["native_unreachable_proven"])

    def test_output_has_no_guest_values_or_gameplay_promotion(self):
        out=m.inspect(reader(source_code()))
        text=json.dumps(out,sort_keys=True)
        self.assertNotIn("original_ppc_instruction_word",text)
        self.assertNotIn("0x90008000",text)
        self.assertFalse(out["ball_native_velocity_restitution_or_impulse_proven"])
        self.assertFalse(out["training_approved"])


if __name__=="__main__":
    unittest.main()
