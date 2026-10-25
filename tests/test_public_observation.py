"""Git publication hardening: safe record IDs, typed public schema, no leakage."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import research_cli
from wii_ai_golf.shared.public_observation import public_observation

ID = "20261025T024510Z-fe87c132b7"


def test_record():
    return {
        "git_commit": "fb26e50459f104822ac2e7ce6927fac92bab0efa",
        "id": ID, "kind": "test", "outcome": "pass",
        "process_exit_code": 0, "schema": 1,
        "started_utc": "2026-10-25T02:45:10.882514+00:00",
        "test_pattern": "test_*.py", "verified_game_score": False,
    }


def memory_record():
    return {
        "schema_version": 1, "kind": "golf-memory-phase-differential",
        "study_id": "S002-GOLF-MEMORY-PHASES",
        "id": "offline-20261025T024510Z-a1b2c3d4",
        "scope": "broad", "sample_count": 4,
        "phase_sample_counts": {"pre": 2, "post": 2},
        "max_non_atomic_frame_span": 12,
        "mean_non_atomic_frame_span": 6.5,
        "skipped_relocated_windows": 0,
        "changed_word_count": 1,
        "top_changed_relative_words": [{
            "region": "golf_config", "relative_offset": "+0x94",
            "documented_role": "game_mode",
            "within_phase_changes": 0, "at_phase_boundary_changes": 1,
            "pointer_like_changes": 0, "float_like_changes": 0,
        }],
        "human_observations": [
            {"stage": 0, "phase": "pre", "observation": "unknown"},
            {"stage": 1, "phase": "post", "observation": "unknown"},
        ],
        "confirmed_power_address": False,
        "confirmed_club_pose_address": False,
        "confirmed_ball_position_address": False,
        "warning": ("Exploratory non-atomic snapshots. Relative offsets are not identified "
                    "gameplay fields; human observations are not verified by RAM."
                    " Legacy pre/post labels cannot prove a hit or exact impact frame."),
        "origin": "existing_private_S002_outcome_capture",
    }


def cohort_record():
    return {
        "schema_version": 1, "kind": "golf-memory-cohort-relative-words",
        "study_id": "S002-GOLF-MEMORY-COHORT",
        "id": "cohort-20261025T025308Z-fbda2d0e",
        "valid_independent_runs": 3, "shared_changed_words_all_runs": 1,
        "recurrent_changed_words_2plus_runs": 2, "distinct_changed_words": 2,
        "excluded_invalid_or_incomplete_runs": 0,
        "regions_with_changes_by_run_count": {"minimap_ball_effect": 3},
        "recurrent_words": [
            {"region": "minimap_ball_effect", "relative_offset": "+0x78",
             "runs_changed": 3, "runs_within_phase": 1,
             "runs_at_phase_boundary": 3, "within_phase_events": 1,
             "boundary_events": 5},
            {"region": "golf_config", "relative_offset": "+0x94",
             "runs_changed": 2, "runs_within_phase": 0,
             "runs_at_phase_boundary": 2, "within_phase_events": 0,
             "boundary_events": 2},
        ],
        "no_gameplay_variable_verified": True,
        "warning": (
            "Repeated changes are not identified golf power, club pose, flight or score. "
            "Only already-recorded phase-aligned statistics are compared; "
            "frame timing and human labels may differ."
        ),
    }


class PublicObservationTests(unittest.TestCase):
    def test_matches_actual_published_test_shape(self):
        self.assertEqual(public_observation(test_record()), test_record())

    def test_rejects_path_traversal_and_unsupported_kind_without_git(self):
        for change in (
            {"id": "../secret"},
            {"id": "20261025T024510Z-fe87c132b7/secret"},
            {"kind": "../private"},
            {"kind": "unknown"},
            {"private_path": "C:/Users/private/file"},
            {"raw_ram": [1, 2, 3]},
            {"verified_game_score": True},
        ):
            with self.subTest(change=change), patch.object(research_cli, "_git") as git:
                with self.assertRaises(ValueError):
                    research_cli.publish_summary({**test_record(), **change})
                git.assert_not_called()

    def test_fail_on_unrecognized_nested_fields(self):
        v1 = {k: v for k, v in test_record().items()
              if k not in ("test_pattern", "outcome")}
        v1.update({"kind": "v1", "requested_a_lead_frames": 45,
                   "requested_motion_scale": 1.0, "requested_speed_scale": 1.0,
                   "requested_backswing_scale": 1.0,
                   "human": {"contact_human": "yes", "initial_club_pose_human": "back"},
                   "controller": {"trace_sha256": "a" * 64}})
        self.assertEqual(public_observation(v1)["human"]["contact_human"], "yes")
        for secret in (
            {**v1, "human": {"contact_human": "yes", "player_name": "private"}},
            {**v1, "controller": {"trace_sha256": "a" * 64, "memory": "private"}},
            {**v1, "human": {"contact_human": "C:/Users/private"}},
        ):
            with self.assertRaises(ValueError):
                public_observation(secret)

    def test_bad_power_numbers_fail_closed(self):
        row = {k: v for k, v in test_record().items()
               if k not in ("test_pattern", "outcome")}
        row.update({"kind": "v1", "requested_a_lead_frames": 45,
                    "requested_motion_scale": 1.0,
                    "requested_speed_scale": 1.0,
                    "requested_backswing_scale": 1.0})
        for bad in (101, -1, float("nan"), float("inf"), 10 ** 1000):
            with self.subTest(value=str(bad)[:30]), self.assertRaises(ValueError):
                public_observation({**row, "human": {
                    "displayed_power_percent_human": bad}})
        self.assertEqual(
            public_observation({**row, "human": {
                "displayed_power_percent_human": 75.0}})["human"]["displayed_power_percent_human"], 75.0)

    def test_free_text_screen_and_warning_never_publish(self):
        record = {k: v for k, v in test_record().items()
                  if k not in ("test_pattern", "outcome")}
        record.update({"kind": "v1", "requested_a_lead_frames": 45,
                       "requested_motion_scale": 1.0,
                       "requested_speed_scale": 1.0,
                       "requested_backswing_scale": 1.0,
                       "settled_screen_observation": "C:/private/file",
                       "warning": "private file name"})
        result = public_observation(record)
        self.assertNotIn("private", json.dumps(result))
        self.assertNotIn("settled_screen_observation", result)
        self.assertNotIn("warning", result)

    def test_s002_memory_summary_is_only_safe_relative_offsets(self):
        safe = public_observation(memory_record())
        self.assertEqual(safe["kind"], "golf-memory-phase-differential")
        self.assertFalse(safe["confirmed_ball_position_address"])
        self.assertNotIn("Legacy pre/post", safe["warning"])
        for change in (
            {"top_changed_relative_words": [{
                **memory_record()["top_changed_relative_words"][0],
                "absolute_address": "0x80000000"}]},
            {"human_observations": [{"phase": "post", "stage": 1,
                                     "observation": "C:/private"}]},
            {"confirmed_power_address": True},
            {"origin": "C:/Users/private"},
            {"warning": "private sensitive context"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                public_observation({**memory_record(), **change})

    def test_s002_cohort_schema_accepts_safe_existing_shape(self):
        safe = public_observation(cohort_record())
        self.assertEqual(safe["kind"], "golf-memory-cohort-relative-words")
        self.assertTrue(safe["no_gameplay_variable_verified"])

    def test_cohort_rejects_private_fields_and_invalid_recurrence(self):
        cohort = cohort_record()
        altered = (
            {**cohort, "private_path": "C:/Users/private"},
            {**cohort, "no_gameplay_variable_verified": False},
            {**cohort, "id": "cohort-../../secrets"},
            {**cohort, "warning": "C:/private"},
            {**cohort, "valid_independent_runs": 1},
            {**cohort, "shared_changed_words_all_runs": 9},
            {**cohort, "recurrent_words": [{
                **cohort["recurrent_words"][0], "raw_value": "0x80000000"}]},
            {**cohort, "recurrent_words": [{
                **cohort["recurrent_words"][0], "runs_changed": 4}]},
            {**cohort, "recurrent_words": cohort["recurrent_words"] * 2},
        )
        for row in altered:
            with self.subTest(value=list(row.keys())[-1]), self.assertRaises(ValueError):
                public_observation(row)

    def test_excess_rows_rejected(self):
        row = memory_record()
        row["top_changed_relative_words"] *= 301
        with self.assertRaisesRegex(ValueError, "relative-offset ranking"):
            public_observation(row)


if __name__ == "__main__":
    unittest.main()
