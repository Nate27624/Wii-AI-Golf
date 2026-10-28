"""Fully synthetic tests: no Wii RAM files, Dolphin, RPC, or live shots."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_existing_successful_shot_private as subject
from wii_ai_golf.audit.outcome_transition import rank_outcome_candidates


def rows_for(values, *, base=0x80010000, window="golf_config"):
    phases = ["pre", "pre", "pre", "post", "post",
              "settled", "settled", "settled"]
    assert len(values) == len(phases)
    out = []
    for stage, v in zip(phases, values):
        raw = struct.pack(">4I", 1, v, 3, 4)
        out.append({
            "schema_version": 1,
            "source": "Felk-read-only-US-Rev1-unverified-golf-windows",
            "game_id": "RSPE01",
            "disc_revision": 1,
            "game_mode_raw": 4,
            "phase": stage,
            "windows": {window: {
                "address": f"0x{base:08X}", "bytes_hex": raw.hex()}},
            "non_atomic_frame_span": 2,
        })
    return out


def summary_for(rows, distance=100.0):
    return {
        "study_id": "S002-HG-OUTCOME-TRANSITION-EXPLORATORY",
        "raw_data_created": True,
        "swing_dispatch": {
            "state": "complete", "applied_frames": 89, "total_frames": 89},
        "known_good_swing_request": {
            "a_lead_requested_frames": 45,
            "a_lead_observed_frame_delta": 46},
        "human_observation": {
            "contact_human": "yes",
            "finished_on_green_human": "no",
            "displayed_distance_human": distance,
            "displayed_unit_human": "ft",
            "displayed_power_percent_human": 75.0,
            "displayed_power_verified_by_memory": False,
            "game_distance_verified_by_memory": False},
        "candidate_ranking": rank_outcome_candidates(rows, human_distance=distance),
    }


class ExistingSuccessfulShotTests(unittest.TestCase):
    def test_one_existing_record_is_sanitized_and_timing_classified(self):
        rows = rows_for([10, 10, 10, 20, 21, 30, 30, 30])
        out = subject.audit(rows, summary_for(rows))
        self.assertEqual(out["snapshot_phase_counts"], {
            "pre": 3, "post": 2, "settled": 3})
        self.assertEqual(out["candidate_count_recomputed_and_matches_saved"], 1)
        self.assertEqual(out["lead_requested_frames"], 45)
        self.assertTrue(out["lead_observed_at_least_requested"])
        self.assertTrue(out["distance_may_be_capped_or_censored"])
        self.assertFalse(out["approved_for_training"])
        self.assertFalse(out["ball_velocity_verified"])
        c = out["candidate_temporal_classifications"][0]
        self.assertEqual(c["source_relative_owners"], [
            {"source_window": "golf_config", "relative_offset": "+0x004"}])
        self.assertEqual(c["temporal_pattern"], "post_all_changed")
        # Strong privacy: the public-facing report contains no private
        # runtime RAM address, hex word, or raw 32-bit decimal value.
        printed = json.dumps(out)
        self.assertNotIn("0x80010004", printed)
        self.assertNotIn('"before"', printed)
        self.assertNotIn('"settled": {"u32"', printed) # phase count label safe
        self.assertNotIn("PRIVATE.jsonl", printed)

    def test_settled_only_distinguished_from_post(self):
        rows = rows_for([10, 10, 10, 10, 10, 30, 30, 30])
        out = subject.audit(rows, summary_for(rows))
        c = out["candidate_temporal_classifications"][0]
        self.assertEqual(c["temporal_pattern"], "settled_only_change")
        self.assertFalse(c["physical_semantics_verified"])

    def test_pointer_like_words_not_promoted(self):
        rows = rows_for([0x80020000]*3 + [0x80020004]*2 + [0x80020008]*3)
        out = subject.audit(rows, summary_for(rows))
        self.assertTrue(
            out["candidate_temporal_classifications"][0]["pointer_like_word_any_phase"])
        self.assertFalse(out["ball_world_xyz_verified"])

    def test_private_summary_mismatch_and_missing_provenance_fail(self):
        rows = rows_for([10]*3 + [20]*2 + [30]*3)
        saved = summary_for(rows)
        saved["candidate_ranking"]["all_phase_stable_change_count"] += 1
        with self.assertRaisesRegex(ValueError, "count disagrees"):
            subject.audit(rows, saved)
        saved = summary_for(rows)
        saved["known_good_swing_request"]["a_lead_observed_frame_delta"] = 2
        with self.assertRaisesRegex(ValueError, "A-lead"):
            subject.audit(rows, saved)
        saved = summary_for(rows)
        saved["human_observation"]["contact_human"] = "no"
        with self.assertRaisesRegex(ValueError, "witnessed-contact"):
            subject.audit(rows, saved)
        saved = summary_for(rows)
        saved["swing_dispatch"]["applied_frames"] = 88
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            subject.audit(rows, saved)

    def test_invalid_phase_order_rejected(self):
        rows = rows_for([10]*3 + [20]*2 + [30]*3)
        saved = summary_for(rows)
        rows[5], rows[3] = rows[3], rows[5]
        with self.assertRaises(ValueError):
            subject.audit(rows, saved)

    def test_relative_source_owner_requires_all_phases(self):
        rows = rows_for([10]*3 + [20]*2 + [30]*3)
        addr = 0x80010004
        self.assertEqual(subject._relative_owners(rows, addr), [{
            "source_window": "golf_config", "relative_offset": "+0x004"}])
        for i in range(3, 5):
            rows[i]["windows"]["golf_config"]["address"] = "0x8000FFF0"
        self.assertEqual(subject._relative_owners(rows, addr), [])
        self.assertTrue(subject._pointer_like(0x90000000))
        self.assertFalse(subject._pointer_like(11))

    def test_bad_run_id_blocks_path_traversal(self):
        self.assertIsNone(subject.RUN_ID.fullmatch("../private"))
        self.assertIsNone(subject.RUN_ID.fullmatch("outcome-../../file"))
        self.assertIsNotNone(subject.RUN_ID.fullmatch(
            "outcome-20261028T033948Z-5cd47f00"))



def effect_alias_rows():
    """Construct three overlapping 0x200 windows with actual +0x90 bases.

    The test deliberately includes eight CHANGING words in four pairs with
    +0x90 separation, not eight independent score/ball coordinates.
    """
    phases = ["pre"] * 3 + ["post"] * 2 + ["settled"] * 3
    offsets = (
        ("minimap_player_effect", 0),
        ("minimap_shot_line_effect", 0x90),
        ("minimap_ball_effect", 0x120),
    )
    base = 0x80010000
    rows = []
    for phase in phases:
        n = {"pre": 1, "post": 2, "settled": 3}[phase]
        payload = bytearray(0x320)
        for slot in range(4):
            struct.pack_into(
                ">II", payload, 0x78 + slot * 0x90,
                n * 10 + slot, 0x80050000 + n * 0x1000 + 4 * slot)
        windows = {
            name: {
                "address": f"0x{base+off:08X}",
                "bytes_hex": payload[off:off+0x200].hex(),
            }
            for name, off in offsets
        }
        rows.append({
            "schema_version": 1,
            "source": "Felk-read-only-US-Rev1-unverified-golf-windows",
            "game_id": "RSPE01", "disc_revision": 1, "game_mode_raw": 4,
            "phase": phase, "windows": windows,
            "non_atomic_frame_span": 2,
        })
    return rows


class ExistingEffectAliasTests(unittest.TestCase):
    def test_eight_changed_words_are_four_strided_effect_pairs(self):
        rows = effect_alias_rows()
        out = subject.audit(rows, summary_for(rows))
        self.assertEqual(out["candidate_count_recomputed_and_matches_saved"], 8)
        self.assertTrue(out["effect_pointer_bases_spaced_0x90_in_all_phases"])
        self.assertTrue(out["repeating_two_word_effect_pairs_observed"])
        self.assertEqual(out["repeated_effect_pair_count_if_verified"], 4)
        patterns = out["candidate_temporal_classifications"]
        self.assertEqual(
            {(x["inferred_effect_slot_index"], x["inferred_effect_slot_field"])
             for x in patterns},
            {(slot, field) for slot in range(4)
             for field in ("+0x078", "+0x07C")})
        self.assertEqual(
            sum(x["pointer_like_word_any_phase"] for x in patterns), 4)
        self.assertTrue(all(
            x["screen_or_render_effect_window"] and
            x["temporal_pattern"] == "post_all_changed"
            for x in patterns))
        self.assertFalse(out["ball_world_xyz_verified"])
        self.assertFalse(out["approved_for_training"])
        printed = json.dumps(out)
        self.assertNotIn("0x80010000", printed)
        self.assertNotIn("0x80050000", printed)

    def test_single_phase_stride_conflict_disables_all_layout_inferences(self):
        rows = effect_alias_rows()
        rows[2]["windows"]["minimap_ball_effect"]["address"] = "0x80010124"
        self.assertFalse(subject._effect_stride_layout(rows))
        self.assertEqual(subject._effect_slot(
            rows, 0x80010078, layout=False),
            {"inferred_effect_slot_index": None,
             "inferred_effect_slot_field": None})

if __name__ == "__main__":
    unittest.main()
