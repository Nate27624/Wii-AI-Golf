"""Fabricated PPC negative controls for the exact 3 BL + +0x4C first-use review."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_global_call_translation_followup as m

UNIT=m.UNIT_BASE
DISP=-100
SITES=(0x2B64,0x2BE0,0x2C64,0x2CD4,0x2CF8,0x2D18,0x2D24,
       0x2D30,0x2DC0,0x2DF8,0x2E04,0x2E30,0x2EF4,0x2FB8,0x2FE4)
UNITS=(
    ("RPGolMain",0x8028E098,0x8028E900),
    ("RPGolFieldManager",0x80290B44,0x80294184),
    ("RPGolMapObjBall",0x80296FD8,0x8029B240),
    ("RPGolSimulateManager",0x8029B240,0x8029BBB4),
    ("RPGolPlayer",0x8029E62C,0x802A2210),
    ("RPGolPlayerManager",0x802A2210,0x802A3560),
)

def d(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xffff)

def bl(pc,dest):
    return (18<<26)|((dest-pc)&0x03fffffc)|1

def _report():
    rows=[]
    for i in SITES:
        row={"global_load_unit_relative_pc":f"+0x{i:04X}",
             "destination_GPR":"r3",
             "first_bounded_consumer_class":"other",
             "first_bounded_consumer_unit_relative_pc":None,
             "source_syntactic_field_displacement":None}
        for start,call in m.CALL_PAIRS:
            if i==start:
                row["first_bounded_consumer_class"]="direct_bl_after_r3_pointer_candidate"
                row["first_bounded_consumer_unit_relative_pc"]=f"+0x{call:04X}"
        if i==0x2CF8:
            row["first_bounded_consumer_class"]="field_load_from_source_global_pointer"
            row["first_bounded_consumer_unit_relative_pc"]="+0x2CFC"
            row["source_syntactic_field_displacement"]=76
        rows.append(row)
    return {"kind":"S002-GLOBAL-SLOT-DIRECT-READ-FIRST-USE-HINTS",
            "exact_known_direct_loads_checked":15,
            "source_only_first_use_hints":rows,
            "approved_for_model_training":False}

def _words():
    words={}
    targets=(0x8029AB78,0x8029B4AC,0x800A3244)
    for (site,call),target in zip(m.CALL_PAIRS,targets):
        words[UNIT+site]=d(32,3,13,DISP)
        words[UNIT+call]=bl(UNIT+call,target)
    words[UNIT+0x2CF8]=d(32,3,13,DISP)
    words[UNIT+0x2CFC]=d(32,30,3,0x4C)
    words[UNIT+0x2D00]=d(48,1,30,0)
    words[UNIT+0x2D04]=d(48,2,30,4)
    words[UNIT+0x2D08]=d(48,3,30,8)
    return words

def analyze(changes=None,report=None):
    words=_words()
    words.update(changes or {})
    return m.analyze(lambda pc:words.get(pc,0x60000000),
                     report if report is not None else _report(),DISP,UNITS)

class SourceFollowup(unittest.TestCase):
    def test_three_exact_public_targets_and_source_units(self):
        o=analyze()
        rows=o["exact_three_candidate_direct_calls"]
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]["direct_bl_public_target_code_pc"],"0x8029AB78")
        self.assertEqual(rows[0]["target_scanned_golf_unit_or_external"],"RPGolMapObjBall")
        self.assertEqual(rows[1]["target_scanned_golf_unit_or_external"],"RPGolSimulateManager")
        self.assertEqual(rows[2]["target_scanned_golf_unit_or_external"],"outside_six_scanned_golf_units")
        self.assertFalse(rows[0]["direct_source_global_pointer_is_runtime_r3_argument_verified"])

    def test_three_float_translation_offsets_syntactically_supported(self):
        x=analyze()["source_global_translation_field_read"]
        self.assertTrue(x["three_distinct_component_offsets_seen"])
        self.assertEqual([r["vector_offset"] for r in x["recognized_direct_f32_accesses"]],[0,4,8])
        self.assertEqual(x["first_syntactic_vector_use_class"],"direct_vector_float_access_syntax_observed")

    def test_branch_interrupts_before_float_triple(self):
        x=analyze({UNIT+0x2D04:(16<<26)|(12<<21)|(2<<16)|8})[
            "source_global_translation_field_read"]
        self.assertFalse(x["three_distinct_component_offsets_seen"])
        self.assertEqual(x["first_syntactic_vector_use_class"],
                         "branch_or_call_before_complete_direct_vector_use")

    def test_modified_global_slot_or_wrong_field_refused(self):
        with self.assertRaises(ValueError):
            analyze({UNIT+0x2CF8:d(32,3,13,DISP+4)})
        with self.assertRaises(ValueError):
            analyze({UNIT+0x2CFC:d(32,30,3,0x48)})

    def test_wrong_BL_or_bad_public_call_destination_refused(self):
        pc=UNIT+0x2B70
        with self.assertRaises(ValueError):
            analyze({pc:bl(pc,0x8029AB78)&~1})
        with self.assertRaises(ValueError):
            analyze({pc:bl(pc,0x81800000)})

    def test_unknown_mr_r30_clobber_abstains(self):
        words={UNIT+0x2D00:(31<<26)|(4<<21)|(30<<16)|(4<<11)|(444<<1)}
        x=analyze(words)["source_global_translation_field_read"]
        self.assertEqual(x["first_syntactic_vector_use_class"],
                         "potential_translation_register_clobber")
        self.assertFalse(x["three_distinct_component_offsets_seen"])

    def test_wrong_first_consumer_class_refused(self):
        report=_report()
        report["source_only_first_use_hints"][0]["first_bounded_consumer_class"]="field_load_from_source_global_pointer"
        with self.assertRaises(ValueError):
            analyze(report=report)

    def test_overlap_public_units_refused(self):
        altered=list(UNITS)
        altered[0]=("fake",0x80000000,0x81800000)
        with self.assertRaises(ValueError):
            m.analyze(lambda pc:_words().get(pc,0x60000000),_report(),DISP,altered)

    def test_plain_instruction_range_returns_unknown_without_inventing_xyz(self):
        words={UNIT+0x2D00:0x60000000,UNIT+0x2D04:0x60000000,
               UNIT+0x2D08:0x60000000}
        x=analyze(words)["source_global_translation_field_read"]
        self.assertFalse(x["three_distinct_component_offsets_seen"])
        self.assertEqual(x["recognized_direct_f32_accesses"],[])

    def test_no_private_values_and_all_runtime_training_false(self):
        o=analyze()
        s=json.dumps(o)
        for forbidden in ("private_path","heap_pointer","MEM1.bin",
                          "raw_ppc_word","source_dump_sha"):
            self.assertNotIn(forbidden,s)
        self.assertFalse(o["whole_function_control_flow_verified"])
        self.assertFalse(o["dynamic_receiver_or_renderer_identity_verified"])
        self.assertFalse(o["physical_xyz_velocity_power_impact_score_verified"])
        self.assertFalse(o["training_approved"])
        self.assertFalse(o["allowed_to_publish"])

if __name__=="__main__":
    unittest.main()
