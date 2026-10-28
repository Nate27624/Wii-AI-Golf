"""Synthetic no-ROM, no-RAM tests for source-selected angular matrix pattern."""
from __future__ import annotations

import copy
import math
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import inspect_golf_aim_rotation_private as rotation
from test_inspect_golf_aim_offsets_private import fixture


def _f32(value):
    return f"0x{struct.unpack('>I', struct.pack('>f', value))[0]:08X}"


def filled(before=math.radians(37.25), after=math.radians(12.13)):
    report = fixture()
    rows = report["windows"]["player_record_0"]["all_words_by_phase_hex"]
    for i, angle in enumerate((before, before, after, after)):
        c, s = math.cos(angle), math.sin(angle)
        rows[i][0x3C // 4] = _f32(angle + math.pi / 2)
        rows[i][0x40 // 4] = _f32(c)
        rows[i][0x44 // 4] = _f32(-s)
        rows[i][0x48 // 4] = _f32(s)
        rows[i][0x4C // 4] = _f32(c)
    return report


class RotationHypothesisTests(unittest.TestCase):
    def test_angle_matrix_quarterturn_and_aim_specificity(self):
        out = rotation.inspect(filled())
        self.assertTrue(out["all_phases_rotation_like"])
        self.assertTrue(out["before_aim_idle_stable"])
        self.assertTrue(out["after_aim_idle_stable"])
        self.assertAlmostEqual(
            out["theta_delta_degrees_during_WASD_aim"], -25.12, places=2)
        self.assertAlmostEqual(
            out["matrix_delta_degrees_during_WASD_aim"], -25.12, places=2)
        self.assertAlmostEqual(
            out["theta_matrix_delta_discrepancy_degrees"], 0, places=4)
        for obs in out["phase_observations"]:
            self.assertTrue(obs["matrix_diagonal_exact"])
            self.assertTrue(obs["matrix_offdiagonal_opposites_exact"])
            self.assertLess(abs(obs["quarter_turn_relation_residual_radians"]), 1e-5)
        for flag in ("source_field_semantics_verified",
                     "screen_aim_angle_verified", "world_axes_verified",
                     "ball_motion_verified", "swing_power_verified",
                     "approved_for_training", "allowed_to_publish"):
            self.assertFalse(out[flag])

    def test_incorrect_off_diagonal_sign_abstains(self):
        report = filled()
        rows = report["windows"]["player_record_0"]["all_words_by_phase_hex"]
        rows[2][0x44 // 4] = rows[2][0x48 // 4]
        out = rotation.inspect(report)
        self.assertFalse(out["all_phases_rotation_like"])
        self.assertFalse(out["phase_observations"][2]
                         ["matrix_offdiagonal_opposites_exact"])

    def test_bad_diagonal_abstains(self):
        report = filled()
        report["windows"]["player_record_0"]["all_words_by_phase_hex"][1][0x4C//4] = _f32(0.1)
        out = rotation.inspect(report)
        self.assertFalse(out["all_phases_rotation_like"])
        self.assertFalse(out["phase_observations"][1]["matrix_diagonal_exact"])

    def test_nonunit_or_bad_theta_does_not_prove_relation(self):
        report = filled()
        rows = report["windows"]["player_record_0"]["all_words_by_phase_hex"]
        for idx in (1, 2):
            rows[idx][0x40 // 4] = _f32(2.0)
            rows[idx][0x4C // 4] = _f32(2.0)
        out = rotation.inspect(report)
        self.assertFalse(out["all_phases_rotation_like"])
        report = filled()
        report["windows"]["player_record_0"]["all_words_by_phase_hex"][2][0x3C//4] = _f32(0)
        self.assertFalse(rotation.inspect(report)["all_phases_rotation_like"])

    def test_refuse_invalid_source_report_or_nan(self):
        report = filled()
        report["kind"] = "unknown"
        with self.assertRaises(ValueError):
            rotation.inspect(report)
        report = filled()
        report["windows"]["player_record_0"]["all_words_by_phase_hex"][2][0x3C//4] = "0x7FC00000"
        with self.assertRaises(ValueError):
            rotation.inspect(report)

    def test_wrap_is_principal_angle(self):
        self.assertAlmostEqual(rotation.signed_wrap(3 * math.pi), -math.pi)
        self.assertAlmostEqual(rotation.signed_wrap(-3 * math.pi), -math.pi)


if __name__ == "__main__":
    unittest.main()
