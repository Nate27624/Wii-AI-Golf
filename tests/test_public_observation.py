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

    def test_excess_rows_rejected(self):
        row = memory_record()
        row["top_changed_relative_words"] *= 301
        with self.assertRaisesRegex(ValueError, "relative-offset ranking"):
            public_observation(row)


if __name__ == "__main__":
    unittest.main()
