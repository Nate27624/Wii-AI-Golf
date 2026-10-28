"""Completely synthetic, privacy-preserving tests for label-free P0 graph."""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_seven_label_free_graph_private as graph


def state(n=1):
    start = (1, 2, 3)
    pin = (10, 20, 30)
    # 12 source words + 2 source geometry tuples, all synthetic.
    context = (0, 2, 100, 200, 300, 400, 500, 600, 700, 1, 2, 3,
               start, pin)
    return {
        "context": context,
        "vectors": {
            "ball_object_0x030": (n, 2, 3),
            "ball_cache_0x0cc": (7, 8, 9),
            "ball_cache_0x0f0": (12, 13, 14),
            "ball_cache_0x0fc": (15, 16, 17),
            "source_current_start": start,
            "source_pin": pin,
        },
    }


def cohort():
    return {n: state(n) for n in graph.CAPTURES}


class LabelFreeGraphTests(unittest.TestCase):
    def test_all_21_pairs_source_only_no_timing_claim(self):
        r = graph.summarize(cohort())
        self.assertEqual(r["capture_count"], 7)
        self.assertEqual(r["unordered_pairs_exhaustively_compared"], 21)
        self.assertEqual(r["source_context_group_count"], 1)
        self.assertEqual(len(r["pairs"]), 21)
        self.assertTrue(all(p["same_source_owner_hole_pin_tee_and_config"]
                            for p in r["pairs"]))
        self.assertTrue(all(p["current_changed_components"] == 1
                            for p in r["pairs"]))
        self.assertTrue(all(p["cache_CC_changed_components"] == 0
                            for p in r["pairs"]))
        self.assertFalse(r["human_phase_to_file_mapping_machine_verified"])
        self.assertFalse(r["source_context_match_is_not_proof_of_same_shot"] is False)

    def test_different_source_context_abstains_on_deltas(self):
        d = cohort()
        s = d[7]
        s["context"] = s["context"][:4] + (999,) + s["context"][5:]
        report = graph.summarize(d)
        self.assertEqual(report["source_context_group_count"], 2)
        excluded = [p for p in report["pairs"] if 7 in p["capture_pair_unordered"]]
        self.assertEqual(len(excluded), 6)
        self.assertTrue(all(p["current_changed_components"] is None
                            and p["cache_CC_changed_components"] is None
                            and not p["same_source_owner_hole_pin_tee_and_config"]
                            for p in excluded))
        self.assertEqual(sum(p["same_source_owner_hole_pin_tee_and_config"]
                             for p in report["pairs"]), 15)

    def test_permutation_does_not_change_label_free_relations(self):
        d = cohort()
        r1 = graph.summarize(d)
        d[1], d[7] = d[7], d[1]
        r2 = graph.summarize(d)
        self.assertEqual(r1["source_context_group_count"],
                         r2["source_context_group_count"])
        self.assertEqual(
            Counter((p["current_changed_components"],
                     p["cache_CC_changed_components"])
                    for p in r1["pairs"]),
            Counter((p["current_changed_components"],
                     p["cache_CC_changed_components"])
                    for p in r2["pairs"]))
        self.assertEqual(
            sorted(n["current_equals_own_start_components"] for n in r1["nodes"]),
            sorted(n["current_equals_own_start_components"] for n in r2["nodes"]))

    def test_changed_cache_no_impact_or_endpoint_claim(self):
        d = cohort()
        d[7]["vectors"]["ball_cache_0x0cc"] = (101, 8, 9)
        report = graph.summarize(d)
        self.assertEqual(sum(p["cache_CC_changed_components"] == 1
                             for p in report["pairs"]), 6)
        for name in ("physical_ball_xyz_verified", "velocity_or_impact_verified",
                     "power_or_score_verified", "landing_endpoint_verified",
                     "training_approved", "allowed_to_publish"):
            self.assertIs(report[name], False)

    def test_wrong_keys_numbers_words_and_geometry_abstain(self):
        bad = []
        d = cohort()
        del d[7]
        bad.append(d)
        d = cohort()
        d[7]["vectors"]["ball_object_0x030"] = (1, 2)
        bad.append(d)
        d = cohort()
        d[7]["vectors"]["ball_cache_0x0cc"] = (float("nan"), 2, 3)
        bad.append(d)
        d = cohort()
        d[7]["vectors"]["source_current_start"] = (4, 5, 6)
        bad.append(d)
        d = cohort()
        d[7]["context"] = d[7]["context"][:-1]
        bad.append(d)
        d = cohort()
        d[7]["vectors"]["unexpected"] = (0, 0, 0)
        bad.append(d)
        d = cohort()
        d[7]["vectors"]["source_pin"] = (-1, 0, 1)
        bad.append(d)
        for sample in bad:
            with self.subTest(index=bad.index(sample)):
                with self.assertRaises(ValueError):
                    graph.summarize(sample)

    def test_output_privacy_only_categorical_and_counts(self):
        d = cohort()
        d[4]["context"] = d[4]["context"][:4] + (0xFEEDC0DE,) + d[4]["context"][5:]
        out = json.dumps(graph.summarize(d))
        for private in ("4276994270", "0xFEEDC0DE", "source_pin", "context",
                        "ball_object_0x030", "ball_cache_0x0cc"):
            # \"context\" appears as allowed schema field substring; private
            # raw key/value maps must never appear in public output.
            if private == "context":
                self.assertNotIn('"context":', out)
            else:
                self.assertNotIn(private, out)
        self.assertNotIn("operator_reported_phase_note", out)

    def test_archive_verification_before_and_after_all_mmaps(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for n in graph.CAPTURES:
                for bank_index in (1, 2):
                    (folder / f"{n}.{bank_index}.raw").write_bytes(b"test")
            folders = {n: folder for n in graph.CAPTURES}
            with ExitStack() as stack:
                stack.enter_context(patch.object(graph.seven, "SIZE", (4, 4)))
                stack.enter_context(patch.object(
                    graph.seven.src, "_file",
                    side_effect=lambda p, name, size: p / name))
                stack.enter_context(patch.object(
                    graph.roster, "TwoBankReader",
                    side_effect=lambda a, b: (a, b)))
                stack.enter_context(patch.object(
                    graph, "source_state", return_value=state()))
                stack.enter_context(patch.object(
                    graph, "summarize", return_value={"synthetic": True}))
                with patch.object(graph.seven, "_check_archive",
                                  side_effect=[folders, ValueError("posthash drift")]) as check:
                    with self.assertRaisesRegex(ValueError, "posthash drift"):
                        graph.analyze(folder)
                    self.assertEqual(check.call_count, 2)
                with patch.object(graph.seven, "_check_archive",
                                  side_effect=[folders, folders]) as check:
                    self.assertEqual(graph.analyze(folder), {"synthetic": True})
                    self.assertEqual(check.call_count, 2)

    def test_isolated_python_help_runs_without_private_archive(self):
        process = subprocess.run(
            [sys.executable, "-I",
             str(ROOT / "scripts" / "audit_p0_seven_label_free_graph_private.py"),
             "--help"], capture_output=True, text=True, timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("--archive", process.stdout)


if __name__ == "__main__":
    unittest.main()
