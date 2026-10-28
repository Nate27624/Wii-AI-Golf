"""Fabricated, native-free source controls for three exact SimulateManager callees."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_three_sim_callee_footprints as m

def bl(pc,target,linked=True):
    return (18<<26)|((target-pc)&0x03fffffc)|(1 if linked else 0)

def bc(pc,target):
    return (16<<26)|(12<<21)|(2<<16)|((target-pc)&0xfffc)

def d(op,rs,ra,disp):
    return (op<<26)|(rs<<21)|(ra<<16)|(disp&65535)

def fixture():
    main=[0x60000000]*101
    calls=[]
    for name,entry,length,offset in m.CALLEES:
        main[offset//4]=bl(m.ENTRY+offset,entry)
        calls.append({
            "source_main_function_relative_pc":"+0x%04X"%offset,
            "target_public_code_pc":"0x%08X"%entry,
            "target_source_code_unit_class":"published_RPGolSimulateManager_text_only",
        })
    report={
        "kind":"P0-REV1-GOLF-MAIN-UPDATE-DIRECT-BL-BOUNDED-CENSUS",
        "independent_prior_0x100_original_BL_prefix_matched":True,
        "exact_source_words_scanned":101,
        "guest_physics_step_clock_verified":False,
        "source_direct_linked_calls":calls,
    }
    callees={name:[0x60000000]*(size//4)
             for name,entry,size,offset in m.CALLEES}
    return main,callees,report

def run(modmain=None,modcallees=None,modreport=None):
    main,callees,report=fixture()
    for off,w in (modmain or {}).items():main[off//4]=w
    for name,updates in (modcallees or {}).items():
        for off,w in updates.items():callees[name][off//4]=w
    if modreport is not None:
        report.update(modreport)
    return m.analyze(main,callees,report)

class CalleeFootprint(unittest.TestCase):
    def test_exact_10_70_157_words(self):
        d=run()
        self.assertEqual(d["exact_three_source_callee_instruction_total"],237)
        self.assertEqual([x["source_words_verified"] for x in d["callee_footprints"]],[10,70,157])
        self.assertFalse(d["game_update_function_semantics_verified"])

    def test_short_getter_does_not_get_pure_predicate_label(self):
        d=run()
        self.assertEqual(d["callee_footprints"][0]["source_float_D_form_load_count"],0)
        self.assertFalse(d["callee_footprints"][0]["pure_predicate_or_game_ball_integrator_verified"])

    def test_source_float_store_not_typed_ball_write(self):
        x=run(modcallees={"fn_8029B43C":{
            0:d(52,1,3,0x30),
            4:d(36,4,30,-12),
            8:d(48,2,3,8),
        }})["callee_footprints"][1]
        self.assertEqual(x["source_float_D_form_store_sites"][0]["source_signed_displacement"],0x30)
        self.assertFalse(x["source_float_D_form_store_sites"][0]["receiver_alias_or_actual_ball_write_verified"])
        self.assertEqual(x["source_integer_D_form_store_sites"][0]["source_signed_displacement"],-12)
        self.assertEqual(x["source_float_D_form_load_count"],1)

    def test_direct_B_and_linked_callee_branch_differ(self):
        name="fn_8029B57C"
        entry=0x8029B57C
        a=run(modcallees={name:{4:bl(entry+4,0x8029B43C)}})["callee_footprints"][2]
        self.assertEqual(a["direct_call_count"],1)
        self.assertEqual(a["direct_linked_calls"][0]["target_public_code_pc"],"0x8029B43C")
        b=run(modcallees={name:{4:bl(entry+4,0x8029B43C,False)}})["callee_footprints"][2]
        self.assertEqual(b["source_nonlink_direct_b_count"],1)
        self.assertEqual(b["direct_call_count"],0)

    def test_conditional_between_B554_and_B43C_can_bypass(self):
        pc=m.ENTRY+0x84
        x=run(modmain={0x84:bc(pc,m.ENTRY+0x98)})
        row=x["gap_after_first_before_second_call"][1]
        self.assertEqual(row["source_class"],"conditional_branch")
        self.assertTrue(row["forward_branch_bypasses_second_BL_syntactically"])
        self.assertEqual(row["target_main_function_relative_pc"],"+0x0098")
        self.assertFalse(x["either_sim_callee_executes_once_per_scene_callback_verified"])

    def test_compare_r3_with_zero_is_only_source_syntax(self):
        row=run(modmain={0x80:d(11,0,3,0)})[
            "gap_after_first_before_second_call"][0]
        self.assertEqual(row["source_class"],"compare_r3_to_zero_syntax")

    def test_forward_conditional_exit_beyond_main_still_can_bypass_second_call(self):
        pc=m.ENTRY+0x84
        x=run(modmain={0x84:bc(pc,m.ENTRY+0x1A0)})
        self.assertTrue(x["gap_after_first_before_second_call"][1][
            "forward_branch_bypasses_second_BL_syntactically"])
        self.assertIsNone(x["gap_after_first_before_second_call"][1][
            "target_main_function_relative_pc"])
        self.assertFalse(x["game_update_function_semantics_verified"])

    def test_lmw_is_load_not_object_store(self):
        row=run(modcallees={"fn_8029B554":{4:d(46,3,30,8)}})[
            "callee_footprints"][0]
        self.assertEqual(row["source_integer_D_form_store_sites"],[])
        self.assertEqual(row["source_integer_D_form_load_count"],1)

    def test_invalid_or_missing_callee_window_abstains(self):
        main,callees,report=fixture()
        callees["fn_8029B554"]=callees["fn_8029B554"][:-1]
        with self.assertRaises(ValueError):m.analyze(main,callees,report)
        main,callees,report=fixture()
        del callees["fn_8029B43C"]
        with self.assertRaises(ValueError):m.analyze(main,callees,report)

    def test_false_prefix_or_wrong_callee_target_abstains(self):
        with self.assertRaises(ValueError):
            run(modreport={"independent_prior_0x100_original_BL_prefix_matched":False})
        main,callees,report=fixture()
        report["source_direct_linked_calls"][0]["target_public_code_pc"]="0x8029B558"
        with self.assertRaises(ValueError):m.analyze(main,callees,report)

    def test_noncode_direct_call_and_malformed_instruction_refused(self):
        with self.assertRaises(ValueError):
            run(modcallees={"fn_8029B554":{4:-1}})
        with self.assertRaises(ValueError):
            run(modcallees={"fn_8029B554":{4:(18<<26)|0x1027}})

    def test_no_true_dynamic_game_or_training_fields(self):
        x=run()
        for field in ("game_update_function_semantics_verified",
                      "either_sim_callee_executes_once_per_scene_callback_verified",
                      "runtime_global_or_selected_ball_receiver_verified",
                      "guest_physics_step_clock_verified",
                      "rendered_projectile_or_world_xyz_velocity_verified",
                      "training_approved","allowed_to_publish"):
            self.assertIs(x[field],False)
        serialized=json.dumps(x)
        for secret in ("private_path","MEM1.bin","raw_ppc","physical_xyz_values","dump_sha"):
            self.assertNotIn(secret,serialized)

if __name__=="__main__":unittest.main()
