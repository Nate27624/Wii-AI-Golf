"""Synthetic-only PRE/POST native-bank contrast contract, no Wii RAM data."""
from __future__ import annotations

from contextlib import redirect_stderr
import copy
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import audit_selected_ball_prepost_shot_private as audit
import audit_golf_two_bank_roster_private as roster
from test_selected_ball_start_link_private import fixture


def candidate(*, ball_change=False, start_change=False, wrong_owner=False):
    words, refs = fixture()
    pm = refs["pm"]
    ball = words[pm + 4 + 0x88]
    ballvec = words[ball + 0x4C]
    startobj = words[words[roster.GOLF_FIELD_STATIC] + 0x50]
    startvec = words[startobj + 0x4C]
    if ball_change:
        words[ballvec] = 0x41000000
        words[pm + 4 + 0x54] = 0x41000000
    if start_change:
        words[startvec] = 0x40000000
    if wrong_owner:
        words[roster.GOLF_FIELD_STATIC] = 0x9000DEAD
    def rd(pc):
        if pc in words:
            return words[pc]
        if (roster.PLAYER_MANAGER_CODE[0] <= pc < roster.PLAYER_MANAGER_CODE[1]
                or 0x8029E62C <= pc < 0x802A2210):
            return 0
        raise ValueError("undefined synthetic source word")
    return audit.snapshot_candidate(rd, b"RSPE01\x00\x01")


def manifest():
    one = "0" * 64
    two = "1" * 64
    return {
        "kind": audit.MANIFEST_KIND,
        "schema_version": 1,
        "operator_reports_same_dolphin_process": True,
        "operator_reports_exactly_one_shot": True,
        "operator_reports_visible_ball_displacement": True,
        "operator_reports_no_hole_reset_or_transition": True,
        "checkpoints": {
            "PRE": {"phase_operator_label": "pre_shot_still",
                    "operator_reports_gui_paused": True,
                    "operator_reports_mem1_mem2_export_same_pause": True,
                    "sha256": {"MEM1": one, "MEM2": two}},
            "POST": {"phase_operator_label": "post_shot_visible_displacement",
                     "operator_reports_gui_paused": True,
                     "operator_reports_mem1_mem2_export_same_pause": True,
                     "operator_reports_game_was_running_between_phases": True,
                     "sha256": {"MEM1": two, "MEM2": one}},
        },
    }


class PrePostShotContractTests(unittest.TestCase):
    def test_selected_record_ball_and_start_only(self):
        x = candidate()
        self.assertTrue(x["source_gates"])
        self.assertEqual(len(x["ball_words"]), 3)
        self.assertEqual(x["ball_words"], x["start_words"])
        self.assertEqual(x["record_words"], x["ball_words"])

    def test_good_post_candidate_change_still_not_verified_physics(self):
        report = audit.summarize(candidate(), candidate(ball_change=True),
                                 mem1_changed=True, mem2_changed=True)
        self.assertTrue(report["candidate_change_consistent_with_operator_observed_displacement"])
        self.assertEqual(report["selected_nested_ball_changed_component_count"], 1)
        self.assertEqual(report["selected_player_record_changed_component_count"], 1)
        self.assertEqual(report["source_current_start_changed_component_count"], 0)
        self.assertFalse(report["ball_motion_world_xyz_verified"])
        self.assertFalse(report["approved_for_model_training"])
        self.assertFalse(report["native_pair_same_guest_frame_verified"])

    def test_same_post_vectors_is_inconclusive_not_disproved_motion(self):
        r = audit.summarize(candidate(), candidate(), mem1_changed=True,
                            mem2_changed=True)
        self.assertFalse(r["candidate_change_consistent_with_operator_observed_displacement"])
        self.assertFalse(r["selected_nested_ball_changed"])
        self.assertIn("INCONCLUSIVE", r["warning"])

    def test_changed_start_rejects_corroboration(self):
        r = audit.summarize(candidate(), candidate(ball_change=True,
                            start_change=True), mem1_changed=True,
                            mem2_changed=True)
        self.assertFalse(r["source_current_start_stable"])
        self.assertFalse(r["candidate_change_consistent_with_operator_observed_displacement"])

    def test_same_banks_cannot_claim_displacement(self):
        r = audit.summarize(candidate(), candidate(ball_change=True),
                            mem1_changed=False, mem2_changed=False)
        self.assertFalse(r["candidate_change_consistent_with_operator_observed_displacement"])

    def test_one_bank_unchanged_cannot_claim_displacement(self):
        r = audit.summarize(candidate(), candidate(ball_change=True),
                            mem1_changed=True, mem2_changed=False)
        self.assertFalse(r["candidate_change_consistent_with_operator_observed_displacement"])

    def test_owner_or_slot_drift_fails_closed(self):
        b = candidate()
        a = candidate(ball_change=True)
        a["owner"] = tuple(x + 4 for x in a["owner"])
        with self.assertRaisesRegex(ValueError, "source owner"):
            audit.summarize(b, a, mem1_changed=True, mem2_changed=True)
        a = candidate(ball_change=True)
        a["slot"] = 1
        with self.assertRaisesRegex(ValueError, "record or hole"):
            audit.summarize(b, a, mem1_changed=True, mem2_changed=True)

    def test_source_selected_wrong_revision_and_bad_child_rejected(self):
        words, refs = fixture()
        def rd(pc):
            if pc in words:
                return words[pc]
            if (roster.PLAYER_MANAGER_CODE[0] <= pc < roster.PLAYER_MANAGER_CODE[1]
                    or 0x8029E62C <= pc < 0x802A2210):
                return 0
            raise ValueError("undefined synthetic source word")
        with self.assertRaises(ValueError):
            audit.snapshot_candidate(rd, b"RSPE01\x00\x00")
        ball = words[refs["pm"] + 4 + 0x88]
        words[ball + 0x4C] = ball + 0x38
        with self.assertRaises(ValueError):
            audit.snapshot_candidate(rd, b"RSPE01\x00\x01")

    def test_manifest_accepted_and_attestation_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            file = root / audit.MANIFEST_NAME
            file.write_text(json.dumps(manifest()))
            self.assertEqual(set(audit._manifest(root)), set(audit.PHASES))
            m = manifest()
            m["operator_reports_same_dolphin_process"] = False
            file.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "operator"):
                audit._manifest(root)

    def test_cross_bank_gui_pause_provenance_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            file = root / audit.MANIFEST_NAME
            m = manifest()
            m["checkpoints"]["POST"]["operator_reports_mem1_mem2_export_same_pause"] = False
            file.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "pause"):
                audit._manifest(root)
            m = manifest()
            m["checkpoints"]["POST"]["operator_reports_game_was_running_between_phases"] = False
            file.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "pause"):
                audit._manifest(root)

    def test_missing_or_modified_shot_hash_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            file = root / audit.MANIFEST_NAME
            m = manifest()
            m["checkpoints"]["PRE"]["sha256"]["MEM2"] = "x"*64
            file.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "hash"):
                audit._manifest(root)

    def test_summary_contains_no_private_words_or_owner_pointers(self):
        r = audit.summarize(candidate(), candidate(ball_change=True),
                            mem1_changed=True, mem2_changed=True)
        s = json.dumps(r)
        for secret in ("0x900", "1090519040", "0x41000000",
                       "record_pointer", "ball_words", "start_words"):
            self.assertNotIn(secret, s)
        self.assertFalse(r["allowed_to_publish"])

    def test_cli_bad_private_folder_redacts_absolute_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "SECRET-0x90009999"
            err = StringIO()
            with redirect_stderr(err):
                result = audit.main(["--private-root", str(p)])
            self.assertEqual(result, 1)
            self.assertNotIn(d, err.getvalue())
            self.assertNotIn("SECRET-0x90009999", err.getvalue())


if __name__ == "__main__":
    unittest.main()
