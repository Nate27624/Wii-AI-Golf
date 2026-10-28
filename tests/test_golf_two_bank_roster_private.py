"""Only fabricated memory addresses/values: no real Wii Sports dumps needed."""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_golf_two_bank_roster_private as x


def synthetic():
    manager = 0x80500000
    scene = 0x91001000
    config = 0x91002000
    field = 0x91003000
    main = 0x91004000
    pm = 0x91005000
    mapping = {
        x.SCENE_MANAGER_STATIC: manager,
        x.SCENE_MANAGER_STATIC + 4: 0,
        manager + 0x18: 5,
        manager + 0x0C: scene,
        scene: x.SCENE_DATA[0],
        scene + 0x1C: 5,
        scene + 0x20: manager,
        scene + 0x54: 2,
        scene + 0x9C: main,
        x.GOLF_CONFIG_STATIC: config,
        config + 0x94: 4,
        x.GOLF_FIELD_STATIC: field,
        main: x.MAIN_DATA[0] + 4,
        main + x.MAIN_DIRECT_PLAYERLIKE_MEMBER: 0x91006000,
        0x91006000: x.PLAYER_DATA[0] + 8,
        x.PLAYER_MANAGER_STATIC_CANDIDATE: pm,
        pm: x.PLAYER_MANAGER_DATA[0],
        pm + 0x334: pm + 4,
        pm + 0x338: 1,
    }
    for index in range(4):
        mapping[x.PLAYER_MANAGER_CODE[0] + index * 4] = (7 << 26) | 0xCC
    for index in range(7):
        mapping[x.PLAYER_MANAGER_CODE[0] + 0x40 + index * 4] = (14 << 26) | 0xCC
    for slot in range(x.ROSTER_SLOTS):
        ball = 0x91010000 + slot * 0x100
        player = 0x91020000 + slot * 0x100
        mapping[pm + x.BALL_CANDIDATE_MEMBER + slot*x.ROSTER_STRIDE] = ball
        mapping[pm + x.PLAYER_CANDIDATE_MEMBER + slot*x.ROSTER_STRIDE] = player
        mapping[ball] = x.BALL_DATA[1] - 4
        mapping[player] = x.PLAYER_DATA[0] + 16
    return mapping, {"scene": scene, "pm": pm, "config": config, "manager": manager}



def dform(op, rd, ra, imm):
    return ((op << 26) | (rd << 21) | (ra << 16) | (imm & 0xFFFF))


def mr(dest, source):
    return ((31 << 26) | (source << 21) | (dest << 16)
            | (source << 11) | (444 << 1))


def bl(pc, target):
    return ((18 << 26) | ((target - pc) & 0x03FFFFFC) | 1)


def add(dest, lhs, rhs):
    return ((31 << 26) | (dest << 21) | (lhs << 16)
            | (rhs << 11) | (266 << 1))


def bc(pc, target):
    return (16 << 26) | ((target - pc) & 0xFFFC)


def source_flow_fixture(mapping):
    """Fabricate isolated PPC instructions from mnemonic/operand parameters."""
    patterns = {
        0x802A3194: mr(29, 3),
        0x802A3200: dform(14, 31, 29, 4),
        0x802A3214: mr(3, 31),
        0x802A3218: mr(4, 30),
        0x802A321C: bl(0x802A321C, 0x802A08A0),
        0x802A3224: dform(14, 31, 31, 0xCC),
        0x802A3228: dform(11, 0, 30, 4),
        0x802A322C: bc(0x802A322C, 0x802A3214),
        0x802A08B4: mr(30, 3),
        0x802A08F0: dform(36, 0, 30, 0x88),
        0x8029F0E4: dform(32, 3, 3, 0x88),
        0x8029F0E8: bl(0x8029F0E8, 0x80297124),
        0x802A03A0: dform(32, 4, 3, 0x88),
        0x802A03B4: dform(32, 4, 4, 0x4C),
        0x802A03B8: dform(52, 2, 4, 0),
        0x802A03C0: dform(52, 0, 4, 4),
        0x802A03C8: dform(52, 0, 4, 8),
        0x802A0D74: dform(15, 3, 0, -32708),
        0x802A0D7C: dform(14, 3, 3, 32040),
        0x802A0D88: dform(36, 3, 31, 0),
        0x802A0D94: dform(36, 31, 30, 0xC4),
        0x802A31E8: dform(32, 0, 29, 0x34C),
        0x802A31EC: dform(7, 0, 0, 0xCC),
        0x802A31F0: add(3, 29, 0),
        0x802A31F4: dform(14, 0, 3, 4),
        0x802A31F8: dform(36, 0, 29, 0x334),
    }
    mapping.update(patterns)
    manager_ptr = mapping[x.PLAYER_MANAGER_STATIC_CANDIDATE]
    for idx in range(x.ROSTER_SLOTS):
        record = manager_ptr + 4 + idx * x.ROSTER_STRIDE
        ball = mapping[record + 0x88]
        nested = 0x91030000 + idx * 0x100
        mapping[ball + 0x4C] = nested
        for component in range(3):
            word = 0x3F800000 + idx * 16 + component
            mapping[nested + component * 4] = word
            mapping[record + 0x54 + component * 4] = (
                word if idx == 0 else 0
            )
    return patterns


class PlayerBallRosterTests(unittest.TestCase):
    def analyze(self, words, header=b"RSPE01\x00\x01"):
        def read(addr):
            if (x.PLAYER_MANAGER_CODE[0] <= addr < x.PLAYER_MANAGER_CODE[1]
                    or 0x8029E62C <= addr < 0x802A2210):
                return words.get(addr, 0)
            if addr not in words:
                raise ValueError("unmapped synthetic word")
            return words[addr]
        return x.triage(read, header)

    def test_four_source_interval_paired_slots(self):
        m, _ = synthetic()
        out = self.analyze(m)
        self.assertTrue(out["scene_source_identity_gates_passed"])
        self.assertEqual(out["ball_data_region_firstword_match_count"], 4)
        self.assertEqual(out["player_data_region_firstword_match_count"], 4)
        self.assertEqual(out["slots_with_both_data_region_hints"], 4)
        self.assertTrue(out["all_candidate_slots_pairwise_distinct"])
        self.assertTrue(out["main_direct_child_firstword_in_player_data"])
        self.assertTrue(out["candidate_stride_has_bounded_source_code_corroboration"])
        self.assertEqual(
            out["player_manager_source_code_stride_checks"]["ppc_mulli_immediate_matching_stride"], 4)
        self.assertEqual(
            out["player_manager_source_code_stride_checks"]["ppc_addi_immediate_matching_stride"], 7)
        self.assertFalse(out["actual_player_or_ball_identity_verified"])
        self.assertFalse(out["club_pose_power_ball_xyz_verified"])

    def test_report_redacts_runtime_pointer_values(self):
        m, refs = synthetic()
        out = self.analyze(m)
        encoded = json.dumps(out)
        for raw_pointer in refs.values():
            self.assertNotIn(f"{raw_pointer:08x}", encoded.lower())
        self.assertNotIn("0x9100", encoded)
        self.assertNotIn("0x8050", encoded)
        self.assertNotIn("private_object_address", encoded)
        self.assertFalse(out["allowed_to_publish"])

    def test_wrong_game_revision_and_title_fail_closed(self):
        m, _ = synthetic()
        for header in (b"RSPE01\x00\x00", b"RSPE00\x00\x01", b"BAD"):
            with self.assertRaises(ValueError):
                self.analyze(m, header)

    def test_scene_manager_backlink_mismatch_fails_closed(self):
        m, refs = synthetic()
        m[refs["scene"] + 0x20] = 0x80500020
        with self.assertRaisesRegex(ValueError, "scene structural"):
            self.analyze(m)

    def test_config_mode_cannot_be_assumed_from_mem1_only(self):
        m, refs = synthetic()
        m[refs["config"] + 0x94] = 1
        with self.assertRaisesRegex(ValueError, "training-mode"):
            self.analyze(m)

    def test_one_bad_ball_slot_does_not_get_promoted(self):
        m, refs = synthetic()
        last_ball = m[refs["pm"] + x.BALL_CANDIDATE_MEMBER + 3*x.ROSTER_STRIDE]
        m[last_ball] = 0x00000001
        out = self.analyze(m)
        self.assertEqual(out["ball_data_region_firstword_match_count"], 3)
        self.assertEqual(out["slots_with_both_data_region_hints"], 3)
        self.assertFalse(out["all_candidate_slots_pairwise_distinct"])

    def test_duplicate_player_addresses_not_independent_slots(self):
        m, refs = synthetic()
        p0 = m[refs["pm"] + x.PLAYER_CANDIDATE_MEMBER]
        m[refs["pm"] + x.PLAYER_CANDIDATE_MEMBER + x.ROSTER_STRIDE] = p0
        out = self.analyze(m)
        self.assertEqual(out["slots_with_both_data_region_hints"], 4)
        self.assertFalse(out["all_candidate_slots_pairwise_distinct"])

    def test_wrong_player_manager_source_data_interval_is_error(self):
        m, refs = synthetic()
        m[refs["pm"]] = x.MAIN_DATA[0]
        with self.assertRaisesRegex(ValueError, "candidate identity"):
            self.analyze(m)

    def test_source_offsets_dont_prove_runtime_type(self):
        m, _ = synthetic()
        out = self.analyze(m)
        for key in ("runtime_type_or_vtable_start_verified",
                    "roster_member_offsets_source_verified",
                    "actual_player_or_ball_identity_verified",
                    "same_boot_or_same_frame_pair_independently_verified"):
            self.assertFalse(out[key])

    def test_cli_missing_private_files_never_echoes_user_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            name = Path(temp) / "DO-NOT-SHARE-PRIVATE.raw"
            err = StringIO()
            with redirect_stderr(err):
                self.assertEqual(x.main(["--mem1", str(name),
                                         "--mem2", str(name)]), 1)
            self.assertNotIn("DO-NOT-SHARE", err.getvalue())

    def test_bank_and_source_bounds(self):
        self.assertEqual(x._bank(0x80000000), "MEM1")
        self.assertEqual(x._bank(0x90000000), "MEM2")
        self.assertIsNone(x._bank(0x94000000))
        self.assertIsNone(x._bank(0x90000001))
        self.assertFalse(x._in_data(x.PLAYER_DATA[1], x.PLAYER_DATA))
        self.assertTrue(x._in_data(x.PLAYER_DATA[0], x.PLAYER_DATA))


    def test_matching_layout_without_code_stride_does_not_claim_corroboration(self):
        m, _ = synthetic()
        for addr in list(m):
            if x.PLAYER_MANAGER_CODE[0] <= addr < x.PLAYER_MANAGER_CODE[1]:
                m[addr] = 0
        result = self.analyze(m)
        self.assertEqual(result["slots_with_both_data_region_hints"], 4)
        self.assertFalse(result["candidate_stride_has_bounded_source_code_corroboration"])
        self.assertFalse(result["roster_member_offsets_source_verified"])

    def test_ppc_code_window_is_bounded_and_no_instruction_bytes_exported(self):
        m, _ = synthetic()
        result = self.analyze(m)
        info = result["player_manager_source_code_stride_checks"]
        self.assertEqual(info["ppc_manager_code_instructions_checked"], 1236)
        self.assertFalse(info["ppc_member_register_dataflow_proven"])
        self.assertNotIn("instruction_words", json.dumps(result))

    def test_source_flow_and_exact_constructor_firstword_positive(self):
        words, refs = synthetic()
        patterns = source_flow_fixture(words)
        for slot in range(x.ROSTER_SLOTS):
            obj = words[refs["pm"] + x.PLAYER_CANDIDATE_MEMBER + slot*x.ROSTER_STRIDE]
            words[obj] = 0x803C7D28  # fake constructor vtable value
        report = self.analyze(words)
        flow = report["bounded_source_register_flow_evidence"]
        self.assertEqual(len(patterns), 26)
        self.assertTrue(flow["four_inline_0xcc_record_loop_source_supported"])
        self.assertTrue(flow["record_plus_0x88_ball_code_path_source_supported"])
        self.assertTrue(flow["ball_child_plus_0x4c_three_float_writer_source_supported"])
        self.assertTrue(flow["record_plus_0xc4_allocated_subobject_source_supported"])
        self.assertEqual(report["exact_constructor_firstword_matches_for_plus_0xc4_subobjects"], 4)
        self.assertTrue(report["source_supported_record_layout_not_gameplay_semantics"])
        self.assertEqual(report["source_gated_selected_record_index_hypothesis"], 0)
        self.assertFalse(report["source_selected_record_identity_confirmed"])
        self.assertEqual(report["ball_related_child_plus_0x4c_mapped_triplet_count"], 4)
        self.assertEqual(report["nested_triplets_equal_record_triplet_count"], 1)
        self.assertFalse(report["nested_three_word_destination_is_world_ball_xyz_verified"])
        self.assertFalse(flow["world_space_ball_xyz_or_units_verified"])

    def test_source_flow_rejects_corrupted_four_slot_indexing(self):
        words, _ = synthetic()
        source_flow_fixture(words)
        words[0x802A3224] = dform(14, 31, 31, 0xD0)
        report = self.analyze(words)
        self.assertFalse(
            report["bounded_source_register_flow_evidence"]
                  ["four_inline_0xcc_record_loop_source_supported"])
        self.assertFalse(report["source_supported_record_layout_not_gameplay_semantics"])

    def test_source_flow_rejects_wrong_ball_writer_pointer_base(self):
        words, _ = synthetic()
        source_flow_fixture(words)
        words[0x802A03B4] = dform(32, 4, 3, 0x4C)
        out = self.analyze(words)
        self.assertFalse(
            out["bounded_source_register_flow_evidence"]
               ["ball_child_plus_0x4c_three_float_writer_source_supported"])
        self.assertTrue(
            out["bounded_source_register_flow_evidence"]
               ["record_plus_0x88_ball_code_path_source_supported"])

    def test_wrong_constructor_store_does_not_prove_subobject_vtable(self):
        words, refs = synthetic()
        source_flow_fixture(words)
        words[0x802A0D94] = dform(36, 31, 30, 0xC8)
        for slot in range(x.ROSTER_SLOTS):
            obj = words[refs["pm"] + x.PLAYER_CANDIDATE_MEMBER + slot*x.ROSTER_STRIDE]
            words[obj] = 0x803C7D28
        result = self.analyze(words)
        self.assertFalse(result["bounded_source_register_flow_evidence"]
                         ["record_plus_0xc4_allocated_subobject_source_supported"])
        self.assertEqual(result["exact_constructor_firstword_matches_for_plus_0xc4_subobjects"], 0)

    def test_source_validated_nested_pointer_missing_is_not_inferred(self):
        words, refs = synthetic()
        source_flow_fixture(words)
        ball = words[refs["pm"] + x.BALL_CANDIDATE_MEMBER]
        words[ball + 0x4C] = 0
        result = self.analyze(words)
        self.assertEqual(result["ball_related_child_plus_0x4c_mapped_triplet_count"], 3)
        self.assertEqual(result["nested_triplets_equal_record_triplet_count"], 0)
        self.assertFalse(result["nested_three_word_destination_is_world_ball_xyz_verified"])

    def test_selected_record_pointer_outside_inline_array_fails_hypothesis(self):
        words, refs = synthetic()
        source_flow_fixture(words)
        words[refs["pm"] + 0x334] = 0x91070000
        result = self.analyze(words)
        self.assertIsNone(result["source_gated_selected_record_index_hypothesis"])
        self.assertFalse(result["source_selected_record_identity_confirmed"])

    def test_selector_code_changed_does_not_promote_index(self):
        words, _ = synthetic()
        source_flow_fixture(words)
        words[0x802A31F0] = add(3, 30, 0)
        result = self.analyze(words)
        self.assertIsNone(result["source_gated_selected_record_index_hypothesis"])
        self.assertFalse(result["bounded_source_register_flow_evidence"]
                         ["manager_selected_record_pointer_offset_source_supported"])

if __name__ == "__main__":
    unittest.main()
