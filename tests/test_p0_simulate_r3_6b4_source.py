"""Synthetic-only P0 PPC base-r3 provenance tests. No ROM or native RAM."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_simulate_r3_6b4_source as triage

NOP=0x60000000

def mr(dst,src):
    return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)
def lwz(dst,base,disp):
    return (32<<26)|(dst<<21)|(base<<16)|(disp&65535)
def bl(pc,target):
    return (18<<26)|((target-pc)&0x3FFFFFC)|1

def baseline():
    e=triage.ENTRY
    return {e+8:mr(3,31),
            e+0x14:lwz(4,3,0x6B4),
            e+0x18:mr(3,4),
            e+0x20:bl(e+0x20,triage.CALLEE)}
def run(mem):
    return triage.analyze(lambda pc:mem.get(pc,NOP))

class SourceBaseTests(unittest.TestCase):
    def test_basic_syntactic_r3_producer_not_runtime_identity(self):
        r=run(baseline())
        self.assertEqual(r["candidate_r3_source_class"],"mr_from_r31")
        self.assertEqual(r["candidate_r3_definition_entry_relative_offset"],"+0x008")
        self.assertEqual(r["candidate_load_entry_relative_offset"],"+0x014")
        self.assertTrue(r["actual_source_load_is_lwz_r4_plus_0x6b4_r3"])
        self.assertEqual(r["status"],"SOURCE_SYNTAX_ONLY_R3_PRODUCER_CANDIDATE")
        for flag in ("source_entry_is_verified_function_extent",
                     "all_path_r3_reaching_definition_verified",
                     "base_r3_is_simulate_manager_or_ball_object_verified",
                     "value_loaded_from_6b4_is_global_or_roster_ball_verified",
                     "dynamic_ball_receiver_verified","training_approved",
                     "allowed_to_publish"):
            self.assertFalse(r[flag])

    def test_wrong_offset_abstains(self):
        m=baseline();m[triage.ENTRY+0x14]=lwz(4,3,0x88)
        self.assertEqual(run(m)["status"],"ABSTAIN_SOURCE_LOADER_MISMATCH")

    def test_wrong_base_abstains(self):
        m=baseline();m[triage.ENTRY+0x14]=lwz(4,30,0x6B4)
        self.assertFalse(run(m)["actual_source_load_is_lwz_r4_plus_0x6b4_r3"])

    def test_missing_call_abstains(self):
        m=baseline();del m[triage.ENTRY+0x20]
        self.assertEqual(run(m)["status"],"ABSTAIN_SOURCE_LOADER_MISMATCH")

    def test_unknown_no_r3_definition_abstains(self):
        m=baseline();del m[triage.ENTRY+8]
        self.assertEqual(run(m)["status"],"ABSTAIN_ENTRY_R3_OR_UNSUPPORTED_PRODUCER")

    def test_prior_linked_call_has_return_hazard(self):
        m=baseline();del m[triage.ENTRY+8]
        e=triage.ENTRY
        m[e+4]=bl(e+4,e+0x70)
        r=run(m)
        self.assertEqual(r["status"],"ABSTAIN_R3_POSSIBLE_CALL_RETURN")
        self.assertTrue(r["nearby_call_before_load_could_write_r3"])

    def test_conditional_branch_after_r3_source_abstains(self):
        m=baseline();m[triage.ENTRY+0x10]=16<<26
        r=run(m)
        self.assertTrue(r["static_control_transfer_after_candidate_r3_definition"])
        self.assertEqual(r["status"],"ABSTAIN_R3_CONTROL_TRANSFER_OR_UNKNOWN_WRITER")

    def test_conditional_branch_before_r3_source_abstains(self):
        m=baseline();m[triage.ENTRY+4]=16<<26
        self.assertTrue(run(m)["static_branch_or_call_before_load"])

    def test_nearest_r3_writer_overrides_prior(self):
        m=baseline();m[triage.ENTRY+0x10]=lwz(3,30,0x40)
        r=run(m)
        self.assertEqual(r["candidate_r3_source_class"],"integer_load_base_r30")
        self.assertEqual(r["candidate_r3_definition_entry_relative_offset"],"+0x010")

    def test_rejects_malformed_words(self):
        for value in (None,True,-1,2**32,1.5):
            m=baseline();m[triage.ENTRY]=value
            with self.subTest(value=value):
                with self.assertRaises(ValueError):run(m)

    def test_sanitized_report_excludes_source_words(self):
        payload=json.dumps(run(baseline()))
        for leaked in ("0x8029B43C","0x80299ACC","0x9000","PRIVATE_HEAP"):
            self.assertNotIn(leaked,payload)

if __name__=="__main__":
    unittest.main()
