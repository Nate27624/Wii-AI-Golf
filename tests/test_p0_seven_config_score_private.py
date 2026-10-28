"""Synthetic P0 source-defined score transition tests. No Dolphin or private RAM."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_seven_config_score_private as audit


def state():
    return {
        "slot": 0, "hole": 1,
        "owner": (1, 2, 3, 4, 5, 6, 7),
        "selectors": (11, 12, 13),
        "pin": (1, 2, 3), "tee": (4, 5, 6),
        "ball": (7, 8, 9),
        "scores": tuple([0] * 36),
        "field_counts": (0, 1, 4), "tree_timer": 50,
    }


def cohort():
    d = {n: state() for n in audit.PHASES}
    d[2]["ball"] = (9, 8, 7)
    d[6]["ball"] = (11, 12, 13)
    d[7]["ball"] = (14, 15, 16)
    return d


class ScoreTransitionTests(unittest.TestCase):
    def test_stable_scores_all_shot_edges_are_negative_only(self):
        report = audit.summarize(cohort())
        self.assertEqual([r["transition"] for r in report["comparisons"]],
                         ["1_to_2", "5_to_6", "6_to_7", "5_to_7"])
        self.assertEqual([r["player_score_table_changed_words_of_36"]
                          for r in report["comparisons"]], [0, 0, 0, 0])
        self.assertFalse(report["golf_training_mode_score_table_is_verified_outcome"])
        self.assertFalse(report["training_approved"])

    def test_selected_hole_cell_change_is_only_candidate(self):
        d = cohort()
        x = list(d[7]["scores"])
        x[4] = 1234
        d[7]["scores"] = tuple(x)
        r = audit.summarize(d)["comparisons"]
        self.assertEqual([row["player_score_table_changed_words_of_36"] for row in r],
                         [0, 0, 1, 1])
        self.assertEqual(r[2]["score_changed_cells_per_hole_row_IF_hole_major"], [0, 1, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(r[2]["score_changed_cells_per_player_row_IF_player_major"], [1, 0, 0, 0])
        self.assertTrue(r[2]["selected_cell_changed_IF_hole_major"])
        self.assertFalse(r[2]["selected_cell_changed_IF_player_major"])
        self.assertIsNone(r[2]["selected_player_source_hole_score_cell_changed"])
        self.assertFalse(audit.summarize(d)["game_reported_15p2ft_decoded_from_memory"])

    def test_other_player_changed_without_active_cell(self):
        d = cohort()
        x = list(d[2]["scores"])
        x[7 * 4 + 3] = 543
        d[2]["scores"] = tuple(x)
        row = audit.summarize(d)["comparisons"][0]
        self.assertEqual(row["score_changed_cells_per_hole_row_IF_hole_major"], [0, 0, 0, 0, 0, 0, 0, 1, 0])
        self.assertEqual(row["score_changed_cells_per_player_row_IF_player_major"], [0, 0, 0, 1])
        self.assertFalse(row["selected_cell_changed_IF_hole_major"])
        self.assertFalse(row["selected_cell_changed_IF_player_major"])
        self.assertIsNone(row["other_score_cells_changed"])

    def test_transposed_index_is_not_active_stroke_cell(self):
        # Two contradictory Rev1 public layout annotations:
        # Kokeshi hole-major index=2*4+1=9 vs ogws_info player-major=1*9+2=11.
        d = cohort()
        for s in d.values():
            s["hole"] = 2
            s["slot"] = 1
        x = list(d[7]["scores"])
        x[11] = 777
        d[7]["scores"] = tuple(x)
        r = audit.summarize(d)["comparisons"][2]
        self.assertFalse(r["selected_cell_changed_IF_hole_major"])
        self.assertTrue(r["selected_cell_changed_IF_player_major"])
        self.assertIsNone(r["selected_player_source_hole_score_cell_changed"])
        self.assertEqual(r["score_changed_cells_per_hole_row_IF_hole_major"][2], 1)
        x[9] = 888
        d[7]["scores"] = tuple(x)
        r = audit.summarize(d)["comparisons"][2]
        self.assertTrue(r["selected_cell_changed_IF_hole_major"])
        self.assertTrue(r["selected_cell_changed_IF_player_major"])
        self.assertIsNone(r["selected_player_source_hole_score_cell_changed"])
        self.assertEqual(r["score_changed_cells_per_hole_row_IF_hole_major"][2], 2)

    def test_player_and_hole_bounds_independent(self):
        for key, invalid in (("slot", 4), ("hole", 9), ("slot", -1), ("hole", -1)):
            d = cohort()
            d[5][key] = invalid
            with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                audit.summarize(d)

    def test_frozen_readout_schema_identifies_hole_major_rows(self):
        report = audit.summarize(cohort())
        self.assertEqual(
            report["score_table_source_layout"],
            "GolfConfig+0x04 u32[36] layout disputed [4][9] vs [9][4]"
        )
        self.assertTrue(report["source_annotations_disagree_on_index_order"])
        self.assertFalse(report["PPC_score_index_orientation_verified"])
        self.assertEqual(len(report["comparisons"][0]["score_changed_cells_per_hole_row_IF_hole_major"]), 9)
        self.assertEqual(len(report["comparisons"][0]["score_changed_cells_per_player_row_IF_player_major"]), 4)
        self.assertIsNone(report["comparisons"][0]["selected_player_source_hole_score_cell_changed"])

    def test_field_timer_distinguished_from_score(self):
        d = cohort()
        d[6]["tree_timer"] = 51
        r = audit.summarize(d)["comparisons"][1]
        self.assertTrue(r["field_tree_shadow_timer_changed"])
        self.assertEqual(r["player_score_table_changed_words_of_36"], 0)

    def test_field_count_changes_reported_without_score(self):
        d = cohort()
        d[7]["field_counts"] = (0, 2, 4)
        r = audit.summarize(d)["comparisons"][2]
        self.assertEqual(r["field_source_count_words_changed_of_3"], 1)
        self.assertEqual(r["player_score_table_changed_words_of_36"], 0)

    def test_mismatched_owner_pin_tee_selector_refused(self):
        for key, value in (
            ("owner", (1, 2, 3, 4, 5, 6, 8)),
            ("hole", 2), ("slot", 1),
            ("selectors", (11, 12, 14)),
            ("pin", (9, 2, 3)), ("tee", (4, 5, 7))
        ):
            d = cohort()
            d[6][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit.summarize(d)

    def test_malformed_score_shapes_and_values_refused(self):
        for scores in ((0,)*35, (0,)*37, (-1,)*36,
                       (float("nan"),)*36, (2**32,)*36):
            d = cohort()
            d[5]["scores"] = scores
            with self.subTest(length=len(scores)), self.assertRaises(ValueError):
                audit.summarize(d)

    def test_missing_phase_and_cross_shot_extra_refused(self):
        d = cohort()
        del d[6]
        with self.assertRaises(ValueError):
            audit.summarize(d)
        d = cohort()
        d[3] = state()
        with self.assertRaises(ValueError):
            audit.summarize(d)

    def test_output_privacy_no_raw_values_or_owner(self):
        s = json.dumps(audit.summarize(cohort()))
        for secret in ('"owner"', '"scores"', '"pin"', '"ball"',
                       '"tree_timer"', 'sha256', 'private_path', '0x9000'):
            self.assertNotIn(secret, s)

    def test_source_reader_uses_36_config_words_and_source_hole(self):
        cfg, field, pm = 0x90001000, 0x90002000, 0x90003000
        ball, pin, start = 0x90004000, 0x90005000, 0x90006000
        record = pm + 4
        u = {
            audit.roster.GOLF_CONFIG_STATIC: cfg,
            audit.roster.GOLF_FIELD_STATIC: field,
            audit.roster.PLAYER_MANAGER_STATIC_CANDIDATE: pm,
            cfg + 0x94: 4, cfg + 0x98: 1,
            record + 0x88: ball, ball + 0x4C: ball + 0x30,
            field + 0x44: pin, field + 0x50: start,
            field + 0x30: 0, field + 0x3C: 1,
            field + 0x48: 4, field + 0x10: 555,
        }
        for i in range(36):
            u[cfg + 4 + 4*i] = 300 + i

        class Reader:
            def u32(self, addr):
                if addr not in u:
                    raise ValueError("Unexpected source address")
                return u[addr]

        ss = {
            "selected_index": 0, "hole": 1,
            "pin_obj": pin, "start_obj": start,
            "cfg_bc": 1, "cfg_c0": 2, "cfg_c4": 3,
            "pin": (9, 8, 7),
            "triplets": {
                "source_current_start": (6, 5, 4),
                "ball_object_0x030": (3, 2, 1),
            }
        }
        with patch.object(audit.seven, "_get", return_value=ss):
            result = audit._sample(Reader())
        self.assertEqual(len(result["scores"]), 36)
        self.assertEqual(result["scores"][0], 300)
        self.assertEqual(result["scores"][-1], 335)
        self.assertEqual(result["field_counts"], (0, 1, 4))
        self.assertEqual(result["owner"][0], cfg)

    def test_source_reader_rejects_wrong_mode_or_hole(self):
        class Reader:
            def u32(self, addr):
                return 0
        with patch.object(audit.seven, "_get", return_value={
            "selected_index": 0, "hole": 1,
        }), self.assertRaises(ValueError):
            audit._sample(Reader())

    def test_archive_error_abstains_before_sampling(self):
        with patch.object(audit.seven, "_check_archive",
                          side_effect=ValueError("bad hash")):
            with self.assertRaises(ValueError):
                audit.analyze(Path("no-native-bank"))

    def test_python_isolated_import_help(self):
        script = ROOT / "scripts" / "audit_p0_seven_config_score_private.py"
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable, "-I", str(script), "--help"],
                               cwd=td, capture_output=True, text=True,
                               timeout=20, check=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--archive", p.stdout)


if __name__ == "__main__":
    unittest.main()
