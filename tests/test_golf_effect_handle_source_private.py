"""Synthetic r31 and typed-effect-handle source parser tests (no user RAM)."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_golf_effect_handle_source_private as h


def ins(op,rt,ra,imm):
    return (op<<26)|(rt<<21)|(ra<<16)|(imm&0xFFFF)


def fixture():
    return {
        h.FIELD_END:0x7FFDFB78,
        h.FIELD_METHOD_SHAPED_PROLOGUE:0x9421FFF0,
        h.R31_FROM_R3_PC:h.R31_FROM_R3_WORD,
        h.LOOP_LOAD_CHILD_PC:h.LOOP_LOAD_CHILD_WORD,
        h.LOOP_ADVANCE_PC:h.LOOP_ADVANCE_WORD,
        h.EFFECT_TEXT_START+0x40: ins(36,3,30,0x78),  # stw ID
        h.EFFECT_TEXT_START+0x44: ins(36,4,30,0x7C),  # stw object
        h.EFFECT_TEXT_START+0x50: ins(32,5,31,0x7C),  # lwz object
        h.EFFECT_TEXT_END-4:ins(32,3,4,0x78), # boundary hit
    }


class EffectHandleSourceTests(unittest.TestCase):
    def test_source_typed_pair_and_float_not_promoted(self):
        words=fixture()
        out=h.analyze(lambda pc:words.get(pc,0))
        self.assertTrue(out["source_header_RPSysEffect_mHandle_field_verified"])
        self.assertTrue(out["source_header_HandleBase_members_verified"])
        self.assertEqual(out["expected_effect_handle_members"],[
            {"offset":"+0x078","type":"u32","member":"mHandle.mObjectID"},
            {"offset":"+0x07C","type":"LinkedObject*","member":"mHandle.mObject"}])
        self.assertEqual(out["RPSysEffectBase_write_count"],2)
        self.assertEqual(out["RPSysEffectBase_opcode_compatible_handle_store_candidates"],2)
        self.assertEqual(out["RPSysEffectBase_float_store_offset_07c_collision_count"],0)
        self.assertFalse(out["RPSysEffectBase_literal_offset_search_exhausts_handle_mutations"])
        self.assertEqual(out["RPSysEffectBase_read_count"],2)
        self.assertEqual(
            out["field_manager_r31_candidate_defs"][0]["type"],
            "or_or_mr_to_r31")
        self.assertTrue(out["field_manager_r31_from_r3_at_80290dd0_static_pattern_verified"])
        self.assertTrue(out["field_manager_r31_to_r29_child_pointer_cursor_static_verified"])
        self.assertTrue(out["field_manager_r31_no_recognized_intervening_redefinition"])
        self.assertFalse(out["field_manager_method_boundary_cfg_verified"])
        self.assertFalse(out["field_manager_r3_at_80290dd0_is_method_incoming_this_verified"])
        self.assertEqual(out["field_manager_function_from_rev1_symbols"]["symbol"],
                         "fn_80290DB0")
        self.assertFalse(out["field_manager_r31_origin_proven"])
        self.assertFalse(out["RPSysEffect_base_receiver_proven"])
        self.assertFalse(out["actual_four_minimap_effect_object_identity_verified"])
        self.assertFalse(out["ball_motion_verified"])
        self.assertFalse(out["training_allowed"])
        self.assertFalse(out["RPSysEffect_size_or_allocator_stride_verified"])

    def test_fail_closed_if_known_r31_29_signature_absent(self):
        words=fixture()
        words[h.FIELD_END]^=1
        with self.assertRaisesRegex(ValueError,"r31->r29"):
            h.analyze(lambda pc:words.get(pc,0))

    def test_no_offset_matches_valid_negative_result(self):
        words={h.FIELD_END:0x7FFDFB78}
        out=h.analyze(lambda pc:words.get(pc,0))
        self.assertEqual(out["RPSysEffectBase_literal_handle_hits"],[])
        self.assertEqual(out["field_manager_r31_candidate_defs"],[])

    def test_opcode_displacement_and_boundaries(self):
        words=fixture()
        words[h.EFFECT_TEXT_START]=ins(36,2,30,0x78)
        words[h.EFFECT_TEXT_END]=ins(36,2,30,0x78) # outside code
        words[h.EFFECT_TEXT_START+0x20]=ins(36,2,30,0xFF78)
        words[h.EFFECT_TEXT_START+0x24]=ins(14,2,30,0x78)
        out=h.analyze(lambda pc:words.get(pc,0))
        self.assertEqual(out["RPSysEffectBase_write_count"],3)
        self.assertTrue(all(
            h.EFFECT_TEXT_START<=int(hit["pc"],16)<h.EFFECT_TEXT_END
            for hit in out["RPSysEffectBase_literal_handle_hits"]))
        self.assertFalse(any(
            x["pc"]==f"0x{h.EFFECT_TEXT_END:08X}"
            for x in out["RPSysEffectBase_literal_handle_hits"]))

    def test_register_assigment_consistency_and_invalid_data(self):
        pc=0x80290DD0
        mr31=0x7C7F1B78
        x=h.r31_assignment_candidate(mr31,pc)
        self.assertEqual(x["source_registers"],["r3","r3"])
        self.assertIsNone(h.r31_assignment_candidate(ins(32,4,31,0x78),pc))
        self.assertEqual(
            h.r31_assignment_candidate(ins(32,31,4,0x10),pc)["type"],
            "known_dform_r31_destination")
        for invalid in (None,-1,2**32,"PPC"):
            with self.assertRaises(ValueError):
                h.r31_assignment_candidate(invalid,pc)

    def test_actual_two_float_store_offsets_do_not_claim_pointer_writes(self):
        words=fixture()
        words[h.EFFECT_TEXT_START+0x40]=0
        words[h.EFFECT_TEXT_START+0x44]=0
        words[h.EFFECT_TEXT_START+0x50]=0
        words[h.EFFECT_TEXT_END-4]=0
        words[0x80194FCC]=0xD003007C  # observed stfs f0,+0x7C(r3)
        words[0x80195064]=0xD3E3007C  # observed stfs f31,+0x7C(r3)
        result=h.analyze(lambda pc:words.get(pc,0))
        self.assertEqual(result["RPSysEffectBase_write_count"],2)
        self.assertEqual(result["RPSysEffectBase_opcode_compatible_handle_store_candidates"],0)
        self.assertEqual(result["RPSysEffectBase_float_store_offset_07c_collision_count"],2)
        self.assertEqual(result["source_field_Emitter_direct_mVelPowerSpecDir_offset_hex"],"+0x07C")
        typed=result["RPSysEffectBase_two_float_writes_typed_as_emitter_parameter"]
        self.assertEqual([x["function"] for x in typed],
                         ["RPSysEffect::setPowerSpecDirAdd","RPSysEffect::setPowerSpecDir"])
        self.assertTrue(all(x["source_signature_verified"] for x in typed))
        self.assertTrue(all(not x["is_golf_swing_power_store"] for x in typed))
        self.assertFalse(result["RPSysEffect_base_receiver_proven"])
        self.assertTrue(all(x["float_store_incompatible_with_direct_pointer_write"]
                            for x in result["RPSysEffectBase_literal_handle_hits"]))

    def test_prologue_context_does_not_imply_r3_is_this(self):
        words=fixture()
        out=h.analyze(lambda pc:words.get(pc,0))
        code=out["field_manager_prologue_to_r31_definition_code"]
        self.assertEqual(code[0]["pc"],"0x80290DB0")
        self.assertEqual(code[-1]["pc"],"0x80290DD0")
        self.assertFalse(out["field_manager_r3_at_80290dd0_is_method_incoming_this_verified"])
        # A call between the prologue and r31 save could replace r3.
        # Source-pattern matching must still not promote method-this identity.
        words[0x80290DBC]=0x48000001
        out=h.analyze(lambda pc:words.get(pc,0))
        self.assertFalse(out["field_manager_r3_at_80290dd0_is_method_incoming_this_verified"])

    def test_broken_r31_chain_prevents_source_promotion(self):
        for pc in (h.FIELD_METHOD_SHAPED_PROLOGUE,
                   h.R31_FROM_R3_PC,h.LOOP_LOAD_CHILD_PC,h.LOOP_ADVANCE_PC):
            words=fixture()
            words[pc]=0
            result=h.analyze(lambda addr:words.get(addr,0))
            self.assertFalse(result["field_manager_r31_from_r3_at_80290dd0_static_pattern_verified"])
            self.assertFalse(result["field_manager_r31_to_r29_child_pointer_cursor_static_verified"])
        words=fixture()
        words[h.R31_FROM_R3_PC+4]=0x7C9F2378  # mr r31,r4: recognized competing assignment
        result=h.analyze(lambda addr:words.get(addr,0))
        self.assertFalse(result["field_manager_r31_from_r3_at_80290dd0_static_pattern_verified"])
        self.assertFalse(result["field_manager_r31_no_recognized_intervening_redefinition"])

    def test_excessive_hits_abort(self):
        def read(pc):
            if pc==h.FIELD_END: return 0x7FFDFB78
            if h.EFFECT_TEXT_START<=pc<h.EFFECT_TEXT_END:
                return ins(36,4,3,0x78)
            return 0
        with self.assertRaisesRegex(ValueError,"Unexpected"):
            h.analyze(read)

if __name__=="__main__":
    unittest.main()
