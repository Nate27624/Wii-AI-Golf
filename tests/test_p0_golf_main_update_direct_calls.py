"""Fully fabricated PPC and privacy tests, no native data."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_golf_main_update_direct_calls as m

def direct_b(pc,dest,lk=1,aa=0):
    off=dest if aa else dest-pc
    return (18<<26)|(off&0x03FFFFFC)|(aa<<1)|lk

def words(mods=None):
    w=[0x60000000]*m.SOURCE_WORDS
    if mods:
        for offset,word in mods.items():
            if offset%4 or not 0<=offset<m.MAIN_SIZE: raise ValueError("bad fabricated offset")
            w[offset//4]=word
    return w

def classify(mods=None):
    return m.classify_source_words(words(mods),thunk_target="0x8028E158")

class Source101Tests(unittest.TestCase):
    def test_public_rev1_function_bounds(self):
        self.assertEqual(m.MAIN_ENTRY,0x8028E158)
        self.assertEqual(m.MAIN_END,0x8028E2EC)
        self.assertEqual(m.SOURCE_WORDS,101)

    def test_positive_simulation_code_unit_direct_BL_is_not_physics_proof(self):
        pc=m.MAIN_ENTRY+12
        r=classify({12:direct_b(pc,0x8029B57C)})
        self.assertEqual(r["source_direct_BL_target_in_simulate_manager_code_unit_count"],1)
        self.assertEqual(r["source_direct_linked_calls"][0]["target_public_code_pc"],"0x8029B57C")
        self.assertFalse(r["all_paths_call_simulator_exactly_once_verified"])
        self.assertFalse(r["any_call_is_game_ball_physics_update_verified"])

    def test_linked_call_outside_source_unit_keeps_exact_target(self):
        pc=m.MAIN_ENTRY+32
        r=classify({32:direct_b(pc,0x800A3244)})
        self.assertEqual(r["source_direct_BL_target_in_simulate_manager_code_unit_count"],0)
        self.assertEqual(r["source_direct_linked_calls"][0]["target_source_code_unit_class"],"outside_three_published_Golf_source_units")

    def test_ball_source_call_classified_separately(self):
        pc=m.MAIN_ENTRY+48
        r=classify({48:direct_b(pc,0x8029A5EC)})
        self.assertEqual(r["source_direct_linked_calls"][0]["target_source_code_unit_class"],"published_RPGolMapObjBall_text_only")

    def test_nonlinking_b_is_not_BL(self):
        pc=m.MAIN_ENTRY+8
        r=classify({8:direct_b(pc,0x8029B57C,lk=0)})
        self.assertEqual(r["source_direct_linked_call_count"],0)
        self.assertEqual(r["source_direct_nonlinking_branch_count"],1)

    def test_conditional_control_is_not_exactly_once_execution(self):
        pc=m.MAIN_ENTRY+20
        r=classify({20:(16<<26)|(12<<21)|(2<<16)|8,24:direct_b(pc+4,0x8029B57C)})
        self.assertEqual(r["source_conditional_branch_count"],1)
        self.assertEqual(r["source_direct_BL_target_in_simulate_manager_code_unit_count"],1)
        self.assertFalse(r["all_paths_call_simulator_exactly_once_verified"])

    def test_bcl_and_bctrl_are_not_direct_BL(self):
        r=classify({4:(16<<26)|(12<<21)|(2<<16)|9,
                    8:(19<<26)|(20<<21)|(528<<1)|1})
        self.assertEqual(r["source_direct_linked_call_count"],0)
        self.assertEqual(r["source_indirect_linked_branch_count"],1)
        self.assertEqual(r["source_conditional_link_or_unclassified_branch_count"],1)

    def test_plain_bctr_and_blr_are_not_direct_update_calls(self):
        # Exactly scoped indirect non-linking branch forms: no direct BL.
        r=classify({
            4:(19<<26)|(528<<1),   # bctr
            8:(19<<26)|(16<<1),    # blr
        })
        self.assertEqual(r["source_direct_linked_call_count"],0)
        self.assertEqual(r["source_indirect_branch_instruction_count"],2)
        self.assertEqual(r["source_indirect_linked_branch_count"],0)
        self.assertFalse(r["guest_physics_step_clock_verified"])

    def test_negative_signed_relative_BL(self):
        pc=m.MAIN_ENTRY+0x60
        r=classify({0x60:direct_b(pc,0x8028E158)})
        self.assertEqual(r["source_direct_linked_calls"][0]["target_public_code_pc"],"0x8028E158")

    def test_unit_and_function_offsets_distinguish_c0_origin(self):
        pc=m.MAIN_ENTRY+0x7C
        r=classify({0x7C:direct_b(pc,0x8029B554)})
        call=r["source_direct_linked_calls"][0]
        self.assertEqual(call["source_main_function_relative_pc"],"+0x007C")
        self.assertEqual(call["source_main_unit_relative_pc"],"+0x013C")

    def test_independent_original_prefix_positive_and_bad_targets_refused(self):
        # Recreate ONLY the previously attested 0x100 code call-count witness.
        linked={
            0x04:0x800A3244,
            0x14:0x8028E3A4,
            0x24:0x8029A5EC,
            0x34:0x8028E2EC,
            0x44:0x8028E3A4,
            0x54:0x802A28DC,
            0x64:0x8028E2EC,
            0x74:0x8029A5EC,
            0x7C:0x8029B554,
            0x90:0x8029B43C,
        }
        ops={off:direct_b(m.MAIN_ENTRY+off,dest) for off,dest in linked.items()}
        positive=classify(ops)
        self.assertTrue(m.require_prior_prefix_match(positive))
        self.assertFalse(positive["guest_physics_step_clock_verified"])
        bad_target=dict(ops)
        bad_target[0x90]=direct_b(m.MAIN_ENTRY+0x90,0x8029B554)
        with self.assertRaisesRegex(ValueError,"prefix"):
            m.require_prior_prefix_match(classify(bad_target))
        with self.assertRaisesRegex(ValueError,"prefix"):
            m.require_prior_prefix_match(classify({0x7C:ops[0x7C],0x90:ops[0x90]}))
        altered=classify(ops)
        altered["source_direct_linked_calls"][0]["source_main_unit_relative_pc"]="+0x0004"
        with self.assertRaisesRegex(ValueError,"crosswalk"):
            m.require_prior_prefix_match(altered)

    def test_wrong_thunk_target_and_length_abstain(self):
        with self.assertRaises(ValueError):
            m.classify_source_words(words(),thunk_target="0x8028E15C")
        with self.assertRaises(ValueError):
            m.classify_source_words(words()[:-1],thunk_target="0x8028E158")

    def test_malformed_word_and_non_code_target_abstain(self):
        with self.assertRaises(ValueError):
            m.classify_source_words(words({4:-1}),thunk_target="0x8028E158")
        # PPC absolute AA=1 at low address has no qualified published target.
        with self.assertRaises(ValueError):
            classify({4:direct_b(m.MAIN_ENTRY+4,0x1024,aa=1)})

    def test_report_has_no_unqualified_runtime_or_training_evidence(self):
        r=classify()
        for key in ("all_paths_call_simulator_exactly_once_verified",
                    "any_call_is_game_ball_physics_update_verified",
                    "guest_physics_step_clock_verified",
                    "dynamic_run_or_scene_vtable_dispatch_verified",
                    "rendered_ball_visual_join_verified",
                    "physical_xyz_velocity_power_impact_score_verified",
                    "training_approved","allowed_to_publish"):
            self.assertIs(r[key],False)
        text=json.dumps(r)
        for marker in ("private_path","MEM1.bin","raw_words","heap_pointer","frame_id"):
            self.assertNotIn(marker,text)

    def test_empty_direct_call_census_does_not_exclude_indirect_update(self):
        r=classify({4:(19<<26)|(528<<1)|1})
        self.assertEqual(r["source_direct_BL_target_in_simulate_manager_code_unit_count"],0)
        self.assertEqual(r["source_indirect_linked_branch_count"],1)
        self.assertFalse(r["any_call_is_game_ball_physics_update_verified"])

if __name__=="__main__":
    unittest.main()
