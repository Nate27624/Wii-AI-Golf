"""Synthetic, license-safe offline MEM1+MEM2 pointer-chain regression tests."""
import mmap
import struct
import tempfile
from pathlib import Path
import unittest

from scripts.audit_golf_mem1_mem2_pair import (
    audit, MEM1_SIZE, MEM2_SIZE, MEM1_BASE, MEM2_BASE
)


def put(m1, m2, addr, value):
    raw = m1 if addr < MEM2_BASE else m2
    base = MEM1_BASE if addr < MEM2_BASE else MEM2_BASE
    struct.pack_into(">I", raw, addr - base, value)


class PairAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        p1 = Path(cls.tmp.name) / "mem1.raw"
        p2 = Path(cls.tmp.name) / "mem2.raw"
        with p1.open("wb") as f:
            f.truncate(MEM1_SIZE)
        with p2.open("wb") as f:
            f.truncate(MEM2_SIZE)
        cls.f1 = p1.open("r+b")
        cls.f2 = p2.open("r+b")
        cls.m1 = mmap.mmap(cls.f1.fileno(), 0)
        cls.m2 = mmap.mmap(cls.f2.fileno(), 0)
        cls.m1[:8] = b"RSPE01\x00\x01"
        cls.manager, cls.scene, cls.main = 0x90001000, 0x90002000, 0x90003000
        cls.config, cls.field = 0x90004000, 0x90005000
        for addr, val in (
            (0x804BF4D8, cls.manager), (0x804BF8C4, cls.config),
            (0x804BF868, cls.field), (cls.manager + 0x18, 5),
            (cls.manager + 0x0C, cls.scene), (cls.scene + 0x54, 2),
            (cls.scene + 0x1C, 5), (cls.scene + 0x20, cls.manager),
            (cls.scene + 0x9C, cls.main), (cls.config + 0x94, 4),
            (cls.config + 0x98, 3), (cls.field + 0x3C, 6),
            (cls.field + 0x48, 31), (cls.field + 0x44, 0x90006000),
            (cls.field + 0x50, 0x90007000),
            (cls.field + 0x54, 0x90008000),
            (cls.field + 0x68, 0x90009000),
            (cls.field + 0x70, 0x9000A000),
            (cls.field + 0x18, 0x9000B000),
        ):
            put(cls.m1, cls.m2, addr, val)

    @classmethod
    def tearDownClass(cls):
        cls.m1.close()
        cls.m2.close()
        cls.f1.close()
        cls.f2.close()
        cls.tmp.cleanup()

    def test_valid_cross_bank_chain_and_privacy(self):
        r = audit(self.m1, self.m2, timestamp_gap_seconds=112)
        self.assertTrue(r["unique_source_gated_scene_chain"])
        self.assertTrue(r["candidate_training_mode_4"])
        self.assertEqual(r["source_current_hole_raw_if_bounded"], 3)
        self.assertTrue(r["cross_bank_time_mismatch_warning"])
        self.assertEqual(r["scene_chain_candidate_banks"][0]["scene_bank"], "MEM2")
        self.assertTrue(r["source_field_pointer_candidates"]["current_pin"]["pointer_mapped"])
        self.assertFalse(r["ball_xyz_verified"])
        self.assertNotIn("0x90002000", str(r))

    def test_bad_revision_rejected(self):
        old = self.m1[7]
        try:
            self.m1[7] = 0
            with self.assertRaises(ValueError):
                audit(self.m1, self.m2)
        finally:
            self.m1[7] = old

    def test_mismatched_scene_backlink_rejected(self):
        addr = self.scene + 0x20
        put(self.m1, self.m2, addr, 0)
        try:
            r = audit(self.m1, self.m2)
            self.assertFalse(r["unique_source_gated_scene_chain"])
            self.assertEqual(r["scene_chain_checks"]["scene_sport_2"], 1)
        finally:
            put(self.m1, self.m2, addr, self.manager)

    def test_bad_bank_size(self):
        with self.assertRaises(ValueError):
            audit(b"RSPE01\0\1", self.m2)

    def test_wrong_mode_is_not_power(self):
        addr = self.config + 0x94
        put(self.m1, self.m2, addr, 1)
        try:
            r = audit(self.m1, self.m2)
            self.assertFalse(r["candidate_training_mode_4"])
            self.assertFalse(r["swing_power_verified"])
        finally:
            put(self.m1, self.m2, addr, 4)

    def test_source_labeled_ui_and_vec_shapes(self):
        ui_addr = self.field + 0x6C
        course = 0x9000A000
        old_flag = self.m2[ui_addr - MEM2_BASE]
        vec_addr = course + 0x30
        old_vec = self.m2[vec_addr - MEM2_BASE:vec_addr - MEM2_BASE + 12]
        try:
            self.m2[ui_addr - MEM2_BASE] = 1
            struct.pack_into(">fff", self.m2, vec_addr - MEM2_BASE,
                             1.5, -2.25, 10.0)
            r = audit(self.m1, self.m2)
            self.assertTrue(r["source_labeled_ui_flag_candidates"]["wind_arrow"])
            self.assertTrue(r["source_course_base_mtrans_vec3_shape"]["mapped"])
            self.assertTrue(r["source_course_base_mtrans_vec3_shape"]["three_finite_components"])
            self.assertTrue(r["source_course_base_mtrans_vec3_shape"]["nonzero"])
            self.assertTrue(r["source_labeled_green_slope_opacity_in_unit_interval"])
            self.assertNotIn("1.5", str(r))
            self.assertFalse(r["ball_xyz_verified"])
        finally:
            self.m2[ui_addr - MEM2_BASE] = old_flag
            self.m2[vec_addr - MEM2_BASE:vec_addr - MEM2_BASE + 12] = old_vec

    def test_invalid_ui_bool_and_nan_vec_never_become_gameplay_fields(self):
        ui_addr = self.field + 0x88
        sun_addr = self.field + 0x5C
        old_flag = self.m2[ui_addr - MEM2_BASE]
        old_sun = self.m2[sun_addr - MEM2_BASE:sun_addr - MEM2_BASE + 12]
        try:
            self.m2[ui_addr - MEM2_BASE] = 255
            struct.pack_into(">fff", self.m2, sun_addr - MEM2_BASE,
                             float("nan"), 0.0, 2.0)
            r = audit(self.m1, self.m2)
            self.assertIsNone(r["source_labeled_ui_flag_candidates"]["minimap"])
            self.assertFalse(r["source_labeled_sun_vec3_shape"]["three_finite_components"])
            self.assertFalse(r["wind_speed_direction_verified"])
            self.assertFalse(r["terrain_verified"])
        finally:
            self.m2[ui_addr - MEM2_BASE] = old_flag
            self.m2[sun_addr - MEM2_BASE:sun_addr - MEM2_BASE + 12] = old_sun


if __name__ == "__main__":
    unittest.main()
