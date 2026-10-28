"""Fabricated-data tests only for B0 vs real-human-airborne pin confound."""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_flight_pin_control_private as pin


def word(value):
    return struct.unpack(">I", struct.pack(">f", value))[0]


def v(x, y, z):
    return tuple(word(n) for n in (x, y, z))


def sample(*, ball=(0., 0., 0.), pin_xyz=(20., 3., 5.),
           tee=(0., 0., 0.), caches=None, pinptr=0x90002400,
           pinclass=0x803C0010, slot=0, hole=1):
    if caches is None:
        caches = (ball, ball, ball)
    roots = {key: 0x90002000 + i * 0x400 for i, key in
             enumerate(pin.OBJECT_KEYS)}
    roots["selected_pin"] = pinptr
    triple = {
        "selected_ball": v(*ball),
        "pin": v(*pin_xyz), "start": v(*tee),
        "cache_cc": v(*caches[0]),
        "cache_f0": v(*caches[1]),
        "cache_fc": v(*caches[2]),
    }
    return {
        "selected_index": slot, "hole": hole,
        "roots": roots, "triplets": triple,
        "pin_firstword": pinclass,
        "pin_selfrefs_verified": True,
    }


class PinControlTests(unittest.TestCase):
    def test_genuine_pin_control_stationary_ball_changes(self):
        a = sample()
        b = sample(ball=(1., 2., 4.))
        report = pin.compare(a, b)
        self.assertTrue(report["pin_control_passed"])
        self.assertFalse(report["pin_control_confounded"])
        self.assertEqual(report["pin_changed_bitwise_components_out_of_three"], 0)
        self.assertTrue(report["pin_tee_horizontal_distance_stable_within_tolerance"])
        self.assertEqual(report["ball_position_candidate_change_component_count"], 3)
        self.assertFalse(report["actual_ball_world_xyz_verified"])
        self.assertFalse(report["training_approved"])

    def test_real_like_pin_and_ball_both_change_all_three_while_tee_stable(self):
        a = sample()
        b = sample(ball=(5., 7., 9.), pin_xyz=(25., 10., 14.))
        r = pin.compare(a, b)
        self.assertEqual(r["pin_changed_bitwise_components_out_of_three"], 3)
        self.assertTrue(r["pin_control_confounded"])
        self.assertFalse(r["pin_control_passed"])
        self.assertTrue(r["ball_and_pin_displacement_agree_all_axes"])
        self.assertFalse(r["pin_tee_horizontal_distance_stable_within_tolerance"])
        self.assertEqual(r["start_changed_beyond_float_roundoff_by_axis"],
                         {"x": False, "y": False, "z": False})
        self.assertFalse(r["independent_same_boot_proven"])

    def test_pin_change_is_not_a_shared_ball_displacement(self):
        a = sample()
        b = sample(ball=(5., 7., 9.), pin_xyz=(21., 3., 5.))
        r = pin.compare(a,b)
        self.assertFalse(r["ball_and_pin_displacement_agree_all_axes"])
        self.assertFalse(r["ball_and_pin_displacement_agree_by_axis"]["x"])
        self.assertTrue(r["pin_control_confounded"])

    def test_one_bit_float_jitter_reports_bitwise_vs_numeric_change_separately(self):
        a = sample()
        b = sample(pin_xyz=(20.000001, 3., 5.))
        r=pin.compare(a,b)
        self.assertEqual(r["pin_changed_bitwise_components_out_of_three"],1)
        self.assertEqual(r["pin_changed_beyond_float_roundoff_by_axis"],
                         {"x": False, "y": False, "z": False})
        self.assertTrue(r["pin_control_confounded"])

    def test_pointer_identity_does_not_promote_same_boot(self):
        a=sample()
        b=sample(pinptr=0x9000A000)
        r=pin.compare(a,b)
        self.assertFalse(r["same_dynamic_pointer_values_across_captures"]["selected_pin"])
        self.assertTrue(r["same_dynamic_pointer_values_across_captures"]["selected_start"])
        self.assertFalse(r["independent_same_boot_proven"])
        self.assertFalse(r["same_guest_frame_verified"])

    def test_pin_firstword_change_does_not_promote_class_or_physic_semantics(self):
        a=sample()
        b=sample(pinclass=0x803C0014)
        r=pin.compare(a,b)
        self.assertFalse(r["pin_object_first_word_equal_across_captures"])
        self.assertFalse(r["actual_ball_world_xyz_verified"])

    def test_cached_ball_positions_can_lag_without_being_independent_xyz(self):
        a=sample()
        b=sample(ball=(5., 6., 7.), caches=((5.,6.,7.),(0.,0.,0.),(0.,0.,0.)))
        r=pin.compare(a,b)
        self.assertEqual(r["ball_current_vs_cache_word_equality"]["cache_cc"]["flight_cache_vs_ball_words_equal"],3)
        self.assertEqual(r["ball_current_vs_cache_word_equality"]["cache_f0"]["flight_cache_vs_ball_words_equal"],0)
        self.assertEqual(r["ball_current_vs_cache_word_equality"]["cache_fc"]["flight_cache_vs_ball_words_equal"],0)
        self.assertFalse(r["ball_velocity_verified"])

    def test_missing_phase_identity_fails_closed(self):
        a=sample()
        for other in (sample(slot=1),sample(hole=2)):
            with self.assertRaises(ValueError):
                pin.compare(a,other)

    def test_invalid_owner_object_and_selfref_flags_fail_closed(self):
        a=sample()
        b=sample()
        b["pin_selfrefs_verified"]=False
        with self.assertRaises(ValueError):
            pin.compare(a,b)
        c=sample()
        del c["roots"]["selected_pin"]
        with self.assertRaises(ValueError):
            pin.compare(a,c)

    def test_nonfinite_float_and_malformed_triple_fail_closed(self):
        a=sample()
        b=sample()
        b["triplets"]["pin"]=(0x7fc00000,word(1.),word(2.))
        with self.assertRaises(ValueError):
            pin.compare(a,b)
        c=sample()
        c["triplets"]["cache_cc"]=(0,0)
        with self.assertRaises(ValueError):
            pin.compare(a,c)

    def test_public_report_is_privacy_bounded(self):
        a=sample()
        b=sample(pinptr=0x91007770, ball=(6.,2.,3.))
        r=pin.compare(a,b)
        s=json.dumps(r, sort_keys=True)
        for forbidden in ("0x91007770", "0x90002400", "dynamic_address",
                          "sha256", "private_path", "mem1.raw", "source_raw_words"):
            self.assertNotIn(forbidden,s)
        self.assertFalse(r["allowed_to_publish"])
        self.assertFalse(r["training_approved"])
        self.assertFalse(r["same_guest_frame_verified"])

    def test_missing_private_folders_fail_without_exposing_path(self):
        stream=StringIO()
        with redirect_stderr(stream):
            rc=pin.main(["--baseline","SECRET-BASE","--flight","SECRET-FLIGHT"])
        self.assertEqual(rc,2)
        self.assertNotIn("SECRET",stream.getvalue())

    def test_mandatory_existing_hash_gate_before_additional_read(self):
        with patch.object(pin.audit,"run_local",side_effect=ValueError("no original SHA")):
            with self.assertRaisesRegex(ValueError, "original SHA"):
                pin.run_local(Path("unknown"),Path("unknown2"))


if __name__=="__main__":
    unittest.main()
