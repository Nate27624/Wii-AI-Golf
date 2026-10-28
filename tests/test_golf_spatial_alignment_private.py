"""All-fabricated source-backed pin/cup/start/ball spatial relationship tests."""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import audit_golf_two_bank_roster_private as roster
import audit_golf_spatial_alignment_private as geometry
from test_selected_ball_start_link_private import fixture


def fabricated():
    words, refs = fixture()
    field = words[roster.GOLF_FIELD_STATIC]
    pm = refs["pm"]
    # Deliberately fake, finite float-shaped u32. No source game data.
    pin_xz = (0x41200000, 0xC0A00000, 0x41A00000)
    cup_xz = (pin_xz[0], 0xC0800000, pin_xz[2])
    tee = (0x42000000, 0x3F800000, 0xC1A00000)
    objs = [(0x44, 0x91050000, pin_xz),
            (0x54, 0x91050100, cup_xz),
            (0x2C, 0x91050200, tee)]
    for offset, obj, vals in objs:
        words[field + offset] = obj
        words[obj + 0x4C] = obj + 0x30
        for i, val in enumerate(vals):
            words[obj + 0x30 + 4*i] = val
    # Upstream synthetic selected-link fixture deliberately uses an EXTERNAL
    # allocated vec3 pointer. This SPATIAL test requires the independently
    # constructor-supported *self-reference* seen in real MEM2 (child+0x30).
    selected = words[pm + 4 + 0x88]
    old_dest = words[selected + 0x4C]
    words[selected + 0x4C] = selected + 0x30
    for j in range(3):
        words[selected + 0x30 + 4*j] = words[old_dest + 4*j]
    shared = (0xC1B00000, 0x40000000, 0x41000000)
    for i in (1, 2, 3):
        rec = pm + 4 + i*roster.ROSTER_STRIDE
        obj = words[rec + 0x88]
        words[obj + 0x4C] = obj + 0x30
        dest = obj + 0x30
        for j, val in enumerate(shared):
            words[dest + j*4] = val
    return words, dict(refs, field=field, pin=objs[0][1],
                       cup=objs[1][1], tee=objs[2][1])


def inspect(words, header=b"RSPE01\x00\x01"):
    def r(addr):
        if (roster.PLAYER_MANAGER_CODE[0] <= addr < roster.PLAYER_MANAGER_CODE[1]
                or 0x8029E62C <= addr < 0x802A2210
                or 0x80290B44 <= addr < 0x80294184):
            return words.get(addr, 0)
        if addr not in words:
            raise ValueError("fake memory missing word")
        return words[addr]
    return geometry.analyze_one(r, header)


class IntraMem2SpatialAlignmentTests(unittest.TestCase):
    def test_pin_cup_xz_relationship_and_selected_ball_start(self):
        words, _ = fabricated()
        result = inspect(words)
        self.assertEqual(result["pin_vs_cup_component_equal_mask"], [True, False, True])
        self.assertTrue(result["pin_cup_first_and_third_components_bitwise_equal"])
        self.assertTrue(result["pin_cup_middle_component_bitwise_different"])
        self.assertEqual(result["selected_ball_vs_start_equal_component_count"], 3)
        self.assertTrue(result["selected_ball_and_start_all_three_words_equal"])
        self.assertTrue(result["three_nonselected_ball_objects_all_triplets_equal"])
        self.assertEqual(result["nonselected_ball_objects_matching_current_start_full_triplet"], 0)
        self.assertTrue(result["same_MEM2_bank_comparison_only"])

    def test_map_object_missing_or_wrong_translation_selfref_rejected(self):
        for key in ("pin", "cup", "tee"):
            words, refs = fabricated()
            words[refs[key] + 0x4C] = 0x91090000
            with self.subTest(key=key), self.assertRaises(ValueError):
                inspect(words)

    def test_missing_source_pin_or_tee_pointer_is_not_ignored(self):
        for offset in (0x44, 0x2C):
            words, refs = fabricated()
            words[refs["field"] + offset] = 0
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                inspect(words)

    def test_nonfinite_nan_and_infinite_map_vectors_rejected(self):
        for raw in (0x7F800000, 0x7FC00000, 0xFF800000):
            words, refs = fabricated()
            words[refs["cup"] + 0x34] = raw
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                inspect(words)

    def test_out_of_bound_finite_float_refused(self):
        words, refs = fabricated()
        words[refs["pin"] + 0x30] = 0x4A000000
        with self.assertRaises(ValueError):
            inspect(words)

    def test_pin_cup_nonmatching_component_is_not_forced(self):
        words, refs = fabricated()
        words[refs["cup"] + 0x38] += 1
        out = inspect(words)
        self.assertEqual(out["pin_vs_cup_component_equal_mask"], [True, False, False])
        self.assertFalse(out["pin_cup_first_and_third_components_bitwise_equal"])
        self.assertFalse(out["coordinate_axis_convention_verified"])

    def test_nonselected_child_change_reduces_equality_without_motion_label(self):
        words, refs = fabricated()
        rec = refs["pm"] + 4 + roster.ROSTER_STRIDE
        child = words[rec + 0x88]
        vec = words[child + 0x4C]
        words[vec + 8] += 1
        out = inspect(words)
        self.assertFalse(out["three_nonselected_ball_objects_all_triplets_equal"])
        self.assertFalse(out["ball_world_xyz_or_motion_verified"])

    def test_selected_object_mismatch_never_promotes_motion(self):
        words, refs = fabricated()
        selected = refs["pm"] + 4
        child = words[selected + 0x88]
        vec = words[child + 0x4C]
        words[vec + 4] += 1
        out = inspect(words)
        self.assertEqual(out["selected_ball_vs_start_equal_component_count"], 2)
        self.assertFalse(out["selected_ball_and_start_all_three_words_equal"])
        self.assertFalse(out["ball_world_xyz_or_motion_verified"])

    def test_wrong_game_or_selected_source_identity_rejected(self):
        words, refs = fabricated()
        with self.assertRaises(ValueError):
            inspect(words, header=b"RSPE01\x00\x00")
        words[refs["pm"] + 0x334] = 0
        with self.assertRaises(ValueError):
            inspect(words)

    def test_report_has_no_raw_float_words_pointers_or_gameplay_promotions(self):
        words, _ = fabricated()
        report = inspect(words)
        body = json.dumps(report, sort_keys=True)
        for forbidden in ("0x910", "0x41200000", "0xC0A00000",
                          "runtime_address", "world_coordinate_values",
                          "private_file", "memory_bytes", "device_id"):
            self.assertNotIn(forbidden, body)
        for name in ("same_emulated_frame_MEM1_MEM2_verified",
                     "pin_cup_are_true_physical_landmarks_verified",
                     "coordinate_axis_convention_verified", "distance_units_verified",
                     "ball_world_xyz_or_motion_verified",
                     "approved_for_training", "allowed_to_publish"):
            self.assertFalse(report[name])

    def test_cli_wrong_private_path_redacted(self):
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = geometry.main(["--first-dir", "DO-NOT-REVEAL-PRIVATE"])
        self.assertEqual(code, 1)
        self.assertNotIn("DO-NOT-REVEAL", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
