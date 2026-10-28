"""Synthetic-only source and privacy checks for candidate map translations."""
from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.audit.golf_map_transform_candidates import (
    audit_paired_map_candidates, inspect_named_map_object,
    audit_local_pair, _candidate_vec
)
from wii_ai_golf.audit.golf_cross_bank_state import _Banks


def put(b, offset, value):
    struct.pack_into(">I", b, offset, value)


def vector(b, offset, values):
    struct.pack_into(">fff", b, offset, *values)


def fixture():
    # Small synthetic banks for unit tests ONLY. Production files must be
    # exactly 24MiB/64MiB; this helper cannot bypass the CLI file-size gate.
    m1 = bytearray(0x4BF8D4)
    m2 = bytearray(0x6000)
    m1[:8] = b"RSPE01\x00\x01"
    put(m1, 0x4BF4D8, 0x80001000)
    put(m1, 0x4BF8C4, 0x90001000)
    put(m1, 0x4BF868, 0x90001100)
    put(m1, 0x4BF8D0, 0x90001200)
    put(m1, 0x1000 + 0x18, 5)
    put(m1, 0x1000 + 0x0C, 0x90000100)
    put(m2, 0x100 + 0x1C, 5)
    put(m2, 0x100 + 0x20, 0x80001000)
    put(m2, 0x100 + 0x54, 2)
    put(m2, 0x100 + 0x9C, 0x90000300)
    put(m2, 0x300, 0x803C77A8)
    put(m2, 0x304, 0x90000100)
    put(m2, 0x1000 + 0x94, 4)
    put(m2, 0x1000 + 0x98, 1)
    put(m2, 0x1100 + 0x3C, 6)
    put(m2, 0x1100 + 0x48, 31)
    for off, p in ((0x18, 0x90001800), (0x44, 0x90001880),
                   (0x50, 0x90001900), (0x54, 0x90001980),
                   (0x68, 0x90001A00), (0x70, 0x90001A80)):
        put(m2, 0x1100 + off, p)
    put(m2, 0x1200, 0x803C7DD0)
    for obj, map_obj, xyz in ((0x1880, 0x1B00, (10.0, 2.0, -20.0)),
                              (0x1900, 0x1C00, (0.0, 2.0, 4.0))):
        put(m2, obj, 0x803C7800)
        put(m2, obj + 0x08, 0x90000000 + map_obj)
        vector(m2, obj + 0x30, xyz)
        put(m2, obj + 0x48, 0x90000000 + obj + 0x0C)
        put(m2, obj + 0x4C, 0x90000000 + obj + 0x30)
        vector(m2, map_obj + 0x08, xyz)
    return m1, m2


class GolfMapCandidateTests(unittest.TestCase):
    def test_candidate_vectors_are_not_world_position_claims(self):
        one, two = fixture()
        safe, private = audit_paired_map_candidates(one, two, strict_size=False)
        self.assertTrue(safe["selected_objects"]["pin"]["base_plus_0x30_triplet_finite_and_bounded"])
        self.assertTrue(safe["selected_objects"]["pin"]["constructor_layout_consistent_candidate"])
        self.assertTrue(safe["selected_objects"]["start"]["constructor_layout_consistent_candidate"])
        self.assertTrue(safe["selected_objects"]["pin"]["two_unverified_triplets_agree_within_tolerance"])
        self.assertEqual(safe["selected_objects"]["pin"]["hypothetical_map_entry_axis_agreement"],
                         {"x": True, "y": True, "z": True})
        self.assertTrue(safe["selected_objects"]["pin"]["hypothetical_map_entry_horizontal_xz_agree"])
        self.assertTrue(safe["selected_objects"]["pin"]["hypothetical_map_entry_vertical_y_agrees"])
        self.assertTrue(safe["candidate_vectors_separated_by_nonzero_distance"])
        self.assertTrue(safe["mapobj_base_documented_offset_overlap"])
        for key in ("pin_world_xyz_verified", "start_world_xyz_verified",
                    "live_ball_xyz_verified", "wind_vector_verified",
                    "approved_for_model_training", "same_emulated_frame_proven"):
            self.assertFalse(safe[key])
        self.assertEqual(private["selected_objects"]["pin"]["base_plus_0x30_candidate_floats"],
                         [10.0, 2.0, -20.0])
        self.assertTrue(private["not_for_publication"])
        output = json.dumps(safe)
        for not_allowed in ("0x90001880", "0x90001900", "bytes_hex",
                            "base_plus_0x30_candidate_floats", "private_path"):
            self.assertNotIn(not_allowed, output)

    def test_no_fictitious_pointer_fields_from_source_overlap(self):
        one, two = fixture()
        # Deliberately plant misleading pointer-looking data at +0x40/+0x44,
        # overlapping the documented scale area. Probe may NOT follow it.
        put(two, 0x1880 + 0x40, 0x90002000)
        put(two, 0x1880 + 0x44, 0x90002040)
        safe, _private = audit_paired_map_candidates(one, two, strict_size=False)
        self.assertTrue(safe["mapobj_base_documented_offset_overlap"])
        self.assertEqual(set(safe["selected_objects"]["pin"]), {
            "selected_object_in_mem2",
            "base_constructor_rotation_selfref_matches",
            "base_constructor_translation_selfref_matches",
            "constructor_layout_consistent_candidate",
            "first_word_in_map_object_module_data_range",
            "base_plus_0x30_triplet_finite_and_bounded",
            "base_plus_0x30_triplet_nonzero",
            "base_mMapObj_plus_0x08_pointer_readable",
            "hypothetical_pmp_plus_0x08_triplet_finite_and_bounded",
            "hypothetical_pmp_plus_0x08_triplet_nonzero",
            "two_unverified_triplets_agree_within_tolerance",
            "hypothetical_map_entry_axis_agreement",
            "hypothetical_map_entry_horizontal_xz_agree",
            "hypothetical_map_entry_vertical_y_agrees",
        })

    def test_false_self_reference_does_not_promote_float_to_world_xyz(self):
        one, two = fixture()
        # Finite numbers may exist in a non-MapObjBase object. The new
        # constructor selfrefs at +0x48/+0x4C distinguish that possibility.
        put(two, 0x1880 + 0x48, 0x90001F00)
        put(two, 0x1880 + 0x4C, 0x90001F30)
        safe, _ = audit_paired_map_candidates(one, two, strict_size=False)
        pin = safe["selected_objects"]["pin"]
        self.assertTrue(pin["base_plus_0x30_triplet_finite_and_bounded"])
        self.assertFalse(pin["base_constructor_rotation_selfref_matches"])
        self.assertFalse(pin["base_constructor_translation_selfref_matches"])
        self.assertFalse(pin["constructor_layout_consistent_candidate"])
        self.assertFalse(safe["pin_world_xyz_verified"])

    def test_one_self_reference_is_not_enough(self):
        one, two = fixture()
        put(two, 0x1880 + 0x4C, 0)
        safe, _ = audit_paired_map_candidates(one, two, strict_size=False)
        pin = safe["selected_objects"]["pin"]
        self.assertTrue(pin["base_constructor_rotation_selfref_matches"])
        self.assertFalse(pin["base_constructor_translation_selfref_matches"])
        self.assertFalse(pin["constructor_layout_consistent_candidate"])

    def test_nan_and_out_of_range_are_rejected_without_leaking(self):
        one, two = fixture()
        vector(two, 0x1880 + 0x30, (math.nan, 1.0, 2.0))
        safe, private = audit_paired_map_candidates(one, two, strict_size=False)
        self.assertFalse(safe["selected_objects"]["pin"]["base_plus_0x30_triplet_finite_and_bounded"])
        self.assertIsNone(private["selected_objects"]["pin"]["base_plus_0x30_candidate_floats"])
        one, two = fixture()
        vector(two, 0x1880 + 0x30, (1e7, 0, 0))
        safe, _ = audit_paired_map_candidates(one, two, strict_size=False)
        self.assertFalse(safe["selected_objects"]["pin"]["base_plus_0x30_triplet_finite_and_bounded"])

    def test_map_entry_cannot_be_assumed_to_match(self):
        one, two = fixture()
        vector(two, 0x1B00 + 0x08, (-500.0, 0.0, 10.0))
        safe, _ = audit_paired_map_candidates(one, two, strict_size=False)
        self.assertFalse(safe["selected_objects"]["pin"]["two_unverified_triplets_agree_within_tolerance"])
        self.assertFalse(safe["runtime_pmp_layout_verified"])

    def test_vertical_only_disagreement_is_not_assumed_world_height(self):
        one, two = fixture()
        vector(two, 0x1C00 + 0x08, (0.0, 250.0, 4.0))
        safe, _ = audit_paired_map_candidates(one, two, strict_size=False)
        start = safe["selected_objects"]["start"]
        self.assertEqual(start["hypothetical_map_entry_axis_agreement"],
                         {"x": True, "y": False, "z": True})
        self.assertTrue(start["hypothetical_map_entry_horizontal_xz_agree"])
        self.assertFalse(start["hypothetical_map_entry_vertical_y_agrees"])
        self.assertFalse(safe["start_world_xyz_verified"])

    def test_horizontal_only_disagreement_is_not_actual_pin_shift(self):
        one, two = fixture()
        vector(two, 0x1B00 + 0x08, (500.0, 2.0, -20.0))
        safe, _ = audit_paired_map_candidates(one, two, strict_size=False)
        pin = safe["selected_objects"]["pin"]
        self.assertEqual(pin["hypothetical_map_entry_axis_agreement"],
                         {"x": False, "y": True, "z": True})
        self.assertFalse(pin["hypothetical_map_entry_horizontal_xz_agree"])
        self.assertTrue(pin["hypothetical_map_entry_vertical_y_agrees"])
        self.assertFalse(safe["pin_world_xyz_verified"])

    def test_null_or_unmapped_inner_reference_is_not_dereferenced(self):
        one, two = fixture()
        put(two, 0x1880 + 0x08, 0)
        safe, _ = audit_paired_map_candidates(one, two, strict_size=False)
        self.assertFalse(safe["selected_objects"]["pin"]["base_mMapObj_plus_0x08_pointer_readable"])
        self.assertFalse(safe["selected_objects"]["pin"]["hypothetical_pmp_plus_0x08_triplet_finite_and_bounded"])
        self.assertIsNone(safe["selected_objects"]["pin"]["hypothetical_map_entry_axis_agreement"])
        self.assertIsNone(safe["selected_objects"]["pin"]["hypothetical_map_entry_horizontal_xz_agree"])
        self.assertIsNone(safe["selected_objects"]["pin"]["hypothetical_map_entry_vertical_y_agrees"])

    def test_invalid_selected_object_fails_closed(self):
        one, two = fixture()
        put(two, 0x1100 + 0x44, 0xDEADBEEF)
        with self.assertRaises(ValueError):
            audit_paired_map_candidates(one, two, strict_size=False)

    def test_game_revision_and_mode_must_pass_prior_source_gate(self):
        one, two = fixture()
        one[7] = 0
        with self.assertRaises(ValueError):
            audit_paired_map_candidates(one, two, strict_size=False)
        one, two = fixture()
        put(two, 0x1000 + 0x94, 3)
        with self.assertRaises(ValueError):
            audit_paired_map_candidates(one, two, strict_size=False)

    def test_real_mem_bank_lengths_required_by_default(self):
        one, two = fixture()
        with self.assertRaises(ValueError):
            audit_paired_map_candidates(one, two)

    def test_false_vtable_hint_does_not_prevent_candidate_exploration(self):
        one, two = fixture()
        put(two, 0x1880, 0x803C9999)
        safe, _ = audit_paired_map_candidates(one, two, strict_size=False)
        self.assertFalse(safe["selected_objects"]["pin"]["first_word_in_map_object_module_data_range"])
        self.assertFalse(safe["source_known_derived_class_inheritance"])

    def test_no_user_files_or_rom_for_local_size_reject(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f1, f2 = root / "b1.raw", root / "b2.raw"
            f1.write_bytes(b"RSPE01")
            f2.write_bytes(b"not a raw memory bank")
            with self.assertRaises(ValueError):
                audit_local_pair(f1, f2, private_root=root,
                                 private_output=root / "study-PRIVATE.json")
            self.assertFalse((root / "study-PRIVATE.json").exists())


if __name__ == "__main__":
    unittest.main()
