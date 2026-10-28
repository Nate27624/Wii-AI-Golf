"""P0 fabricated-only 13 PPC word draw main callee source/stop-rule tests."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import review_p0_golf_draw_main_13word_source as probe

NOP=0x60000000

def d(op, rt, ra, disp=0):
    return (op<<26)|(rt<<21)|(ra<<16)|(disp&0xFFFF)

def bl(pc, to):
    return (18<<26)|((to-pc)&0x03FFFFFC)|1

def b(pc, to):
    return (18<<26)|((to-pc)&0x03FFFFFC)

def run(code):
    def reader(pc):
        if pc < probe.ENTRY or pc >= probe.END:
            raise ValueError("outside finite func")
        return code.get(pc,NOP)
    return probe.census(reader)

class DrawMainTests(unittest.TestCase):
    def test_source_is_exactly_thirteen_words(self):
        self.assertEqual(probe.SIZE,0x34)
        self.assertEqual(probe.WORD_COUNT,13)
        self.assertEqual(probe.END,0x8028E0E4)

    def test_valid_13_word_direct_map_ball_bl_source_only(self):
        addr=probe.ENTRY+4
        code={addr:bl(addr,probe.MAP_OBJ_BALL_LO),
              probe.ENTRY+8:d(32,4,3,0x4C),
              probe.ENTRY+12:0x4E800020}
        r=run(code)
        self.assertEqual(r["source_direct_BL_count"],1)
        self.assertEqual(r["source_direct_BL_sites"][0]["target_public_golf_unit_hint"],
                         "RPGolMapObjBall_source_unit_ONLY")
        self.assertEqual(r["source_d_form_base_r3_accesses"][0]["source_field_displacement"],0x4C)
        self.assertEqual(r["source_plain_blr_count"],1)
        self.assertFalse(r["render_object_submit_function_typed_and_verified"])
        self.assertFalse(r["source_global_or_player_selected_ball_drawn_verified"])
        self.assertFalse(r["visual_frame_and_guest_physics_step_join_verified"])
        self.assertFalse(r["training_approved"])

    def test_direct_simulator_bl_is_not_automatically_a_physics_step(self):
        addr=probe.ENTRY+4
        r=run({addr:bl(addr,probe.SIMULATE_MANAGER_LO)})
        self.assertEqual(r["source_direct_BL_count"],1)
        self.assertEqual(r["source_direct_BL_sites"][0]["target_public_golf_unit_hint"],
                         "RPGolSimulateManager_source_unit_ONLY")
        self.assertFalse(r["actual_guest_render_execution_verified"])
        self.assertFalse(r["physical_ball_xyz_velocity_contact_power_score_verified"])

    def test_conditional_branch_not_invocation(self):
        r=run({probe.ENTRY+4:(16<<26)|8})
        self.assertEqual(r["source_direct_BL_count"],0)
        self.assertEqual(r["source_branch_instructions_count"],1)

    def test_ppc_sc_is_not_a_branch_or_golf_simulation_tick(self):
        r=run({probe.ENTRY:17<<26})
        self.assertEqual(r["source_branch_instructions_count"],0)
        self.assertEqual(r["source_system_call_instruction_count"],1)
        self.assertFalse(r["visual_frame_and_guest_physics_step_join_verified"])

    def test_indirect_control_and_plain_return_separately_counted(self):
        r=run({probe.ENTRY:0x4E800020,probe.ENTRY+4:0x4E800420})
        self.assertEqual(r["source_plain_blr_count"],1)
        self.assertEqual(r["source_noncanonical_indirect_or_return_control_count"],1)
        self.assertEqual(r["source_direct_BL_count"],0)

    def test_nonlinking_branch_never_counted_as_bl(self):
        pc=probe.ENTRY+4
        r=run({pc:b(pc,pc+8)})
        self.assertEqual(r["source_direct_BL_count"],0)
        self.assertEqual(r["source_branch_instructions_count"],1)

    def test_large_immediate_redacted(self):
        r=run({probe.ENTRY:d(32,4,3,0x6B4)})
        self.assertIsNone(r["source_d_form_base_r3_accesses"][0]["source_field_displacement"])

    def test_zerobase_not_r3_and_store_is_not_load(self):
        r=run({probe.ENTRY:d(32,4,0,0x4C),
               probe.ENTRY+4:d(36,4,3,0x30)})
        self.assertEqual(len(r["source_d_form_base_r3_accesses"]),1)
        self.assertEqual(r["source_d_form_base_r3_accesses"][0]["syntactic_access"],"store")

    def test_malformed_word_refuses_source(self):
        for bad in (None,True,-1,2**32,1.2):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):run({probe.ENTRY:bad})

    def test_unmapped_direct_branch_still_only_static(self):
        pc=probe.ENTRY+4
        r=run({pc:bl(pc,0x80004000)})
        self.assertEqual(r["source_direct_BL_sites"][0]["target_public_golf_unit_hint"],
                         "OTHER_OR_UNKNOWN_PUBLIC_TEXT")
        self.assertFalse(r["render_object_submit_function_typed_and_verified"])

    def test_all_output_sensitive_runtime_flags_false(self):
        r=run({})
        for key in ("all_path_draw_call_role_verified",
                    "source_global_or_player_selected_ball_drawn_verified",
                    "actual_guest_render_execution_verified",
                    "visual_frame_and_guest_physics_step_join_verified",
                    "physical_ball_xyz_velocity_contact_power_score_verified",
                    "training_approved","allowed_to_publish"):
            self.assertFalse(r[key])
        s=json.dumps(r)
        for secret in ("PRIVATE_PATH","0x9000","source_code_word","local_SHA256"):
            self.assertNotIn(secret,s)

    def test_strict_reads_exact_source_window(self):
        pcs=[]
        r=probe.census(lambda pc: (pcs.append(pc), NOP)[1])
        self.assertEqual(pcs,list(range(probe.ENTRY,probe.END,4)))
        self.assertEqual(r["published_function_size_PPC_words"],13)

if __name__=="__main__":
    unittest.main()
