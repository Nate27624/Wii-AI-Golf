"""P0: fabricated Golf-specific sequence pointer relationship tests only."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_golf_nearpin_sequence_roots_private as audit

MANAGER = 0x90050000
ROOTS = (0x90060000,0x90061000,0x90062000)

def sample(*,manager=MANAGER,roots=ROOTS,phase=None,slot=0,hole=0):
    vals=(*roots,roots[1] if phase is None else phase)
    return {
        "owner_class":"IN_NATIVE_RAM" if manager else "NULL",
        "owner":manager if manager else None,
        "slot":slot,"hole":hole,
        "pointers":vals if manager else None,
        "pointer_classes":tuple(audit._resolved_pointer(p) for p in vals)
            if manager else None
    }

def cohort(**kw):
    return {i:sample(**kw) for i in range(1,8)}

class P0SequencePointerTests(unittest.TestCase):
    def test_singleton_source_static_is_not_generic_score_table(self):
        self.assertEqual(audit.GOLF_SEQUENCE_SINGLETON_STATIC,0x804BF920)
        self.assertNotEqual(audit.GOLF_SEQUENCE_SINGLETON_STATIC,0x804BF708)
        self.assertEqual(audit.TRAINING_FIELDS,(0x0C,0x10,0x14))
        self.assertEqual(audit.PHASE_FIELD,0x18)

    def test_in_range_four_source_fields_without_dereference(self):
        words={audit.GOLF_SEQUENCE_SINGLETON_STATIC:MANAGER,
               MANAGER+0xC:ROOTS[0],MANAGER+0x10:ROOTS[1],
               MANAGER+0x14:ROOTS[2],MANAGER+0x18:ROOTS[1]}
        calls=[]
        def read(addr):
            calls.append(addr)
            return words[addr]
        r=audit._observation(read,{"selected_index":0,"hole":0})
        self.assertEqual(len(calls),5)
        self.assertEqual(r["pointers"],(*ROOTS,ROOTS[1]))
        self.assertNotIn(ROOTS[1],calls)  # no child dereference

    def test_active_alias_is_only_root_pointer_equality(self):
        r=audit.summarize(cohort())
        self.assertEqual(r["records"][0]["active_phase_equals_training_root_indices"],[1])
        self.assertFalse(r["nearpin_sequence_training_number_verified"])
        self.assertFalse(r["active_phase_cpp_type_or_nested_alias_verified"])

    def test_active_phase_nested_no_root_alias_is_not_absent_result(self):
        s=audit.summarize(cohort(phase=0x90062020))
        self.assertEqual(s["records"][0]["active_phase_equals_training_root_indices"],[])
        self.assertEqual(s["records"][0]["active_phase_pointer_class"],"IN_NATIVE_RAM")
        self.assertFalse(s["on_screen_result_or_backing_state_verified"])

    def test_singleton_absent_all_seven_is_reported_without_claim(self):
        s=audit.summarize(cohort(manager=0))
        self.assertEqual(s["records"][0]["GolfSequenceManager_singleton"],"NULL")
        self.assertEqual(s["records"][0]["training_1_2_3_pointer_classes"],None)
        self.assertFalse(s["nearpin_sequence_training_number_verified"])

    def test_selected_stable_manager_phase_changed_edge_count_only(self):
        seq=cohort()
        seq[6]=sample(phase=0x90064000)
        seq[7]=sample(phase=0x90064000)
        z=audit.summarize(seq)
        e=next(x for x in z["numbered_edges"] if x["numbered_edge"]=="5_to_6")
        self.assertTrue(e["active_phase_pointer_changed_when_same_owner"])
        self.assertEqual(e["training_1_2_3_and_active_phase_pointer_equal_by_field"],
                         [True,True,True,False])
        self.assertFalse(e["human_phase_file_labels_machine_verified"])

    def test_owner_changes_refuse_field_alias_comparison(self):
        seq=cohort()
        seq[2]=sample(manager=0x90051000)
        z=audit.summarize(seq)
        e=next(x for x in z["numbered_edges"] if x["numbered_edge"]=="1_to_2")
        self.assertFalse(e["GolfSequenceManager_singleton_pointer_equal"])
        self.assertIsNone(e["training_1_2_3_and_active_phase_pointer_equal_by_field"])
        self.assertFalse(z["same_boot_or_guest_frame_verified"])

    def test_non_pointer_word_is_only_categorized_not_dereferenced(self):
        s=audit.summarize(cohort(roots=(0,0x80001234,0x12345678)))
        self.assertEqual(s["records"][0]["training_1_2_3_pointer_classes"],
                         ["NULL","IN_NATIVE_RAM","OUTSIDE_CAPTURED_RAM_OR_UNALIGNED"])
        self.assertFalse(s["training_member_offsets_source_native_rev1_proven"])

    def test_unmapped_sequence_manager_singleton_abstains(self):
        with self.assertRaises(ValueError):
            audit._observation(lambda addr:0x12345678,{"selected_index":0,"hole":0})

    def test_bad_selected_slot_hole_abstains(self):
        for value in (-1,4,10,"0",True):
            with self.subTest(value=value),self.assertRaises(ValueError):
                audit._observation(lambda _:0,{"selected_index":value,"hole":0})

    def test_not_exact_seven_refused(self):
        for cases in ({}, {1:sample()}, {i:sample() for i in range(8)}):
            with self.assertRaises(ValueError):
                audit.summarize(cases)

    def test_malformed_field_classes_fail_closed(self):
        cases=cohort()
        cases[4]["pointers"]=()
        with self.assertRaises(ValueError):
            audit.summarize(cases)

    def test_raw_pointer_and_private_bank_never_in_report(self):
        r=audit.summarize(cohort(phase=0x90062020))
        blob=json.dumps(r)
        self.assertNotIn(hex(MANAGER),blob)
        self.assertNotIn("0x90062020",blob)
        self.assertNotIn("MEM1.bin",blob)
        self.assertNotIn("sha256",blob)
        self.assertFalse(r["training_approved"])
        self.assertFalse(r["allowed_to_publish"])

    def test_source_runtime_offset_presence_cannot_claim_on_screen(self):
        r=audit.summarize(cohort())
        self.assertTrue(r["mode4_source_selected_gated"])
        self.assertFalse(r["on_screen_result_or_backing_state_verified"])
        self.assertFalse(r["training_member_offsets_source_native_rev1_proven"])

    def test_isolated_help_does_not_read_user_archive(self):
        file=Path(audit.__file__).resolve()
        r=subprocess.run([sys.executable,"-I",str(file),"--help"],
                         capture_output=True,text=True,timeout=15,cwd=file.parents[2])
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn("--archive",r.stdout)

if __name__=="__main__":
    unittest.main()
