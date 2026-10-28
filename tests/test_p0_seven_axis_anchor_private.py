"""Synthetic-only P0 axis anchor tests. No real RAM, game inputs or network."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_seven_axis_anchor_private as audit


def f32(*values):
    return tuple(struct.unpack(">I", struct.pack(">f", float(x)))[0]
                 for x in values)


def state(ball, pin=(9, 12, 6), tee=(0, 20, 0)):
    return {
        "slot": 0, "hole": 1,
        "owner": (1, 2, 3, 4, 5, 6, 7),
        "selectors": (8, 9, 10),
        "ball": f32(*ball),
        "pin": f32(*pin),
        "tee": f32(*tee),
    }


def cohort(pin=(9, 12, 6)):
    return {
        5: state((5, 18, 1), pin=pin),
        6: state((6, 15, 2), pin=pin),
        7: state((7, 12, 3), pin=pin),
    }


class AxisAnchorTests(unittest.TestCase):
    def test_one_component_pin_coincidence_cannot_verify_vertical(self):
        result = audit.summarize(cohort())
        self.assertEqual(result["pin_anchor_coincidence_candidate_indices"], [1])
        self.assertTrue(result["unique_pin_anchor_coincidence_candidate"])
        self.assertTrue(all(row["both_steps_same_strict_direction"]
                            for row in result["per_component"]))
        self.assertFalse(result["any_component_is_physical_vertical_axis_verified"])
        self.assertFalse(result["training_approved"])

    def test_two_equal_pin_components_remain_ambiguous(self):
        result = audit.summarize(cohort(pin=(7, 12, 6)))
        self.assertEqual(result["pin_anchor_coincidence_candidate_indices"], [0, 1])
        self.assertFalse(result["unique_pin_anchor_coincidence_candidate"])

    def test_no_anchor_coincidence_abstains_from_unique_claim(self):
        result = audit.summarize(cohort(pin=(9, 13, 6)))
        self.assertEqual(result["pin_anchor_coincidence_candidate_indices"], [])
        self.assertFalse(result["unique_pin_anchor_coincidence_candidate"])
        self.assertFalse(result["physical_axes_or_game_distance_units_verified"])

    def test_cross_capture_owner_or_geometry_change_refused(self):
        for key, value in (
            ("owner", (1, 2, 3, 4, 5, 6, 8)),
            ("slot", 2),
            ("hole", 3),
            ("selectors", (8, 9, 11)),
            ("pin", f32(10, 12, 6)),
            ("tee", f32(0, 20, 1)),
        ):
            states = cohort()
            states[6][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit.summarize(states)

    def test_no_intermediate_motion_refused(self):
        states = cohort()
        states[6]["ball"] = states[5]["ball"]
        with self.assertRaises(ValueError):
            audit.summarize(states)

    def test_missing_phase_refused(self):
        states = cohort()
        del states[6]
        with self.assertRaises(ValueError):
            audit.summarize(states)

    def test_nonfinite_or_malformed_vector_refused(self):
        for words in ((0x7FC00000, 0, 0), (0x7F800000, 0, 0),
                      (0, 0), (0, 0, -1), (1.0, 0, 0)):
            states = cohort()
            states[6]["ball"] = words
            with self.subTest(words=words), self.assertRaises((ValueError, TypeError)):
                audit.summarize(states)

    def test_static_source_vector_returns_no_numeric_or_private_ids(self):
        report = audit.summarize(cohort())
        s = json.dumps(report)
        for forbidden in ('"owner"', '"selectors"', '"ball"', '"pin"', '"tee"',
                          "sha256", "MEM1", "0x9000", "private_path", "12.0"):
            self.assertNotIn(forbidden, s)
        self.assertFalse(report["allowed_to_publish"])
        self.assertFalse(report["guest_frame_timestamps_machine_verified"])

    def test_ordinal_result_never_forces_a_vertical_axis(self):
        states = cohort()
        states[6]["ball"] = f32(6, 18, 2)
        report = audit.summarize(states)
        self.assertFalse(report["per_component"][1]["both_steps_same_strict_direction"])
        self.assertFalse(report["pin_anchor_is_ground_height_verified"])

    def test_bad_archive_stops_before_read(self):
        with patch.object(audit.seven, "_check_archive",
                          side_effect=ValueError("SHA mismatch")):
            with self.assertRaises(ValueError):
                audit.analyze(Path("ignored-private-missing"))

    def test_isolated_python_help_imports_canonical_helpers(self):
        script = ROOT / "scripts" / "audit_p0_seven_axis_anchor_private.py"
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run(
                [sys.executable, "-I", str(script), "--help"], cwd=td,
                capture_output=True, text=True, timeout=20, check=False
            )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--archive", p.stdout)
        self.assertNotIn("ModuleNotFoundError", p.stderr)


if __name__ == "__main__":
    unittest.main()
