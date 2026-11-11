"""Synthetic live game-angle evidence and fail-closed direct inspector ray tests."""
import inspect
import math
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.inspector.replay import AIM, Sample
from wii_ai_golf.inspector.world_heading_candidate import (
    TEE, PIN, candidate_heading_degrees, direct_aim_ray,
    candidate_flag_error_degrees)


def bits(value):
    return int.from_bytes(struct.pack(">f", value), "big")


def sample(deg, *, qualified=True, digest="a"*64, words=None):
    return Sample(0, "LIVE", 0, 1, 2,
                  {AIM: (bits(math.radians(deg)),)} if words is None else words,
                  digest, qualified, "", "complete", (1, 2))


def landmarks(deg=-22.38945, length=100):
    a = math.radians(deg)
    return {TEE: (0., 3., 0.),
            PIN: (length*math.cos(a), 4., length*math.sin(a))}


class DirectAimTests(unittest.TestCase):
    def test_real_operator_baseline_matches_pin_to_under_one_degree(self):
        s = sample(112.20093)
        h = candidate_heading_degrees(s)
        self.assertAlmostEqual(h, -22.20093, places=4)
        self.assertAlmostEqual(candidate_flag_error_degrees(s, landmarks()),
                               0.18852, delta=0.002)
        start, tip = direct_aim_ray(s, landmarks())
        self.assertEqual(start, (0., 3., 0.))
        self.assertAlmostEqual(math.hypot(tip[0], tip[2]), 23.0, places=4)
        self.assertAlmostEqual(math.degrees(math.atan2(tip[2], tip[0])),
                               h, places=4)

    def test_left_increases_record_but_decreases_world_candidate(self):
        s = sample(124.13273)
        self.assertAlmostEqual(candidate_heading_degrees(s), -34.13273,
                               places=4)

    def test_right_decreases_record_but_increases_world_candidate(self):
        s = sample(97.54178)
        self.assertAlmostEqual(candidate_heading_degrees(s), -7.54178,
                               places=4)

    def test_return_near_baseline_but_not_identical(self):
        self.assertAlmostEqual(candidate_heading_degrees(sample(112.30111)),
                               -22.30111, places=4)
        self.assertNotEqual(candidate_heading_degrees(sample(112.20093)),
                            candidate_heading_degrees(sample(112.30111)))

    def test_pin_bearing_affects_only_ray_length_not_heading(self):
        s = sample(112.20093)
        a = direct_aim_ray(s, landmarks(deg=-30))
        b = direct_aim_ray(s, landmarks(deg=75))
        self.assertAlmostEqual(a[1][0], b[1][0], places=6)
        self.assertAlmostEqual(a[1][2], b[1][2], places=6)
        self.assertEqual(a[1][1], b[1][1])

    def test_ray_does_not_use_ball_coordinate(self):
        s1 = sample(120, words={AIM: (bits(math.radians(120)),),
                                "selected_ball_plus_0x30": (bits(1),bits(2),bits(3))})
        s2 = sample(120, words={AIM: (bits(math.radians(120)),),
                                "selected_ball_plus_0x30": (bits(100),bits(200),bits(300))})
        self.assertEqual(direct_aim_ray(s1, landmarks()),
                         direct_aim_ray(s2, landmarks()))

    def test_zero_length_and_missing_landmark_fail_closed(self):
        s = sample(112.2)
        self.assertIsNone(direct_aim_ray(s, {TEE: (0.,0.,0.)}))
        self.assertIsNone(direct_aim_ray(s, {TEE: (0.,0.,0.),PIN:(0.,0.,0.)}))

    def test_nonfinite_tee_or_pin_fails_closed(self):
        s = sample(112.2)
        for name in (TEE,PIN):
            l = landmarks()
            l[name] = (float("nan"), 0., 1.)
            self.assertIsNone(direct_aim_ray(s, l))

    def test_oversized_distance_fails_closed(self):
        self.assertIsNone(direct_aim_ray(sample(112.2),
                          {TEE:(0.,0.,0.),PIN:(1e9,0.,0.)}))

    def test_invalid_source_and_digest_fail_closed(self):
        self.assertIsNone(direct_aim_ray(sample(112.2, qualified=False), landmarks()))
        self.assertIsNone(direct_aim_ray(sample(112.2, digest=None), landmarks()))

    def test_invalid_angle_fails_closed(self):
        for word in (0x7FC00000, bits(100.0)):
            self.assertIsNone(direct_aim_ray(sample(0, words={AIM:(word,)}), landmarks()))
            self.assertIsNone(candidate_heading_degrees(sample(0, words={AIM:(word,)})))

    def test_missing_and_multiword_angle_fail_closed(self):
        for words in ({}, {AIM:(bits(1),bits(1))}):
            self.assertIsNone(direct_aim_ray(sample(0, words=words), landmarks()))

    def test_wrap_does_not_have_discontinuity_in_ray_direction(self):
        a = direct_aim_ray(sample(-179.99), landmarks())
        b = direct_aim_ray(sample(180.01), landmarks())
        self.assertAlmostEqual(a[1][0], b[1][0], delta=0.0001)
        self.assertAlmostEqual(a[1][2], b[1][2], delta=0.0001)

    def test_onscreen_label_shows_signed_flag_offset_in_degrees(self):
        from wii_ai_golf.inspector.gui import Inspector
        gui_src = inspect.getsource(Inspector.draw_path)
        self.assertIn('text=f"Flag offset: {flag_error:+.2f}°"', gui_src)
        self.assertNotIn('AIM? (90° − record+0x3C)', gui_src)
        for angle, expected in ((112.20093, "Flag offset: +0.19°"),
                                (124.13273, "Flag offset: -11.74°"),
                                (97.54178, "Flag offset: +14.85°")):
            with self.subTest(angle=angle):
                diff = candidate_flag_error_degrees(sample(angle), landmarks())
                self.assertEqual(f"Flag offset: {diff:+.2f}°", expected)

    def test_actual_gui_default_uses_direct_ray_not_reference(self):
        from wii_ai_golf.inspector.gui import Inspector
        src = inspect.getsource(Inspector.draw_path)
        self.assertIn("aim_ray = direct_aim_ray(current, landmarks)", src)
        self.assertNotIn("aim_ray = aim_ray_hypothesis", src)
        self.assertNotIn("self.baseline if self.aim_baseline_source", src)
        self.assertIn("no player coords", src)
        self.assertIn("HYPOTHESIS", src)


if __name__ == "__main__":
    unittest.main()
