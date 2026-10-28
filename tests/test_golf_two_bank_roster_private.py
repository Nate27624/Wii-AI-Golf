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


class PlayerBallRosterTests(unittest.TestCase):
    def analyze(self, words, header=b"RSPE01\x00\x01"):
        def read(addr):
            if x.PLAYER_MANAGER_CODE[0] <= addr < x.PLAYER_MANAGER_CODE[1]:
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

if __name__ == "__main__":
    unittest.main()
