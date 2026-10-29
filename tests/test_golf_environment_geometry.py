"""Entirely synthetic paired source-object transforms; no Wii Sports binary."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.audit.golf_environment_geometry import audit_environment_geometry


def put(buf, off, kind, value):
    struct.pack_into(">"+kind, buf, off, value)


def synthetic_pair():
    m1 = bytearray(0x4BF8D4)
    m2 = bytearray(0x7000)
    m1[:8] = b"RSPE01\x00\x01"
    def u1(off, v): put(m1, off, "I", v)
    def u2(off, v): put(m2, off, "I", v)
    u1(0x4BF4D8, 0x80001000)
    u1(0x4BF8C4, 0x90001000)
    u1(0x4BF868, 0x90001100)
    u1(0x4BF8D0, 0x90001200)
    u1(0x1000 + 0x18, 5)
    u1(0x1000 + 0x0C, 0x90000100)
    u2(0x100 + 0x1C, 5)
    u2(0x100 + 0x20, 0x80001000)
    u2(0x100 + 0x54, 2)
    u2(0x100 + 0x9C, 0x90000300)
    u2(0x300, 0x803C77A8)
    u2(0x304, 0x90000100)
    u2(0x1000 + 0x94, 4)
    u2(0x1000 + 0x98, 1)
    u2(0x1100 + 0x3C, 6)
    u2(0x1100 + 0x48, 31)
    u2(0x1200, 0x803C7DD0)
    offsets = {"current_start": 0x50, "current_pin": 0x44,
               "cup": 0x54, "course": 0x70, "tee_marker": 0x2C}
    coords = {"current_start": (2.2, -5.5, -318.0),
              "current_pin": (174.1, -2.5, -449.7),
              "cup": (174.1, -2.59, -449.7),
              "course": (0, 0, 0), "tee_marker": (-280, 36, 765)}
    for i,(name,ptr_offset) in enumerate(offsets.items()):
        at=0x2000+i*0x100
        u2(0x1100+ptr_offset,0x90000000+at)
        u2(at,0x803C7800+i*4)
        for j in range(9):
            put(m2, at+0x0c+4*j, "f", 1.0 if j in (0,4,8) else 0.0)
        for j,v in enumerate(coords[name]):
            put(m2, at+0x30+4*j,"f",float(v))
        for j in range(3):
            put(m2, at+0x3c+4*j,"f",1.0)
    return m1, m2


class EnvironmentGeometryTests(unittest.TestCase):
    def test_source_geometry_pin_cup_and_distance(self):
        m1, m2 = synthetic_pair()
        r = audit_environment_geometry(m1, m2, strict_size=False)
        self.assertEqual(r["source_declared_current_transform_count"],5)
        self.assertAlmostEqual(
            r["current_start_to_pin_horizontal_game_units"],216.551,places=3)
        self.assertTrue(r["pin_cup_horizontal_coincident_within_0_01_units"])
        self.assertEqual(r["score_array_source_slots_checked"],36)
        self.assertEqual(r["score_slots_zero"],36)
        self.assertFalse(r["golf_ball_xyz_verified"])
        self.assertFalse(r["swing_power_verified"])

    def test_writes_no_raw_memory_and_no_user_paths(self):
        m1,m2 = synthetic_pair()
        a=json.dumps(audit_environment_geometry(m1,m2,strict_size=False))
        for forbidden in ("0x90002000", "0x80001000", "bytes_hex",
                          "mem1.raw", "mem2.raw", "0x803C7800"):
            self.assertNotIn(forbidden,a)

    def test_fails_on_invalid_source_object_scale(self):
        m1,m2=synthetic_pair()
        put(m2,0x2000+0x3c,"f",0)
        with self.assertRaises(ValueError):
            audit_environment_geometry(m1,m2,strict_size=False)

    def test_fails_on_nonorthonormal_rotation(self):
        m1,m2=synthetic_pair()
        put(m2,0x2000+0x0c,"f",9.5)
        with self.assertRaises(ValueError):
            audit_environment_geometry(m1,m2,strict_size=False)

    def test_fails_on_nonfinite_source_translation(self):
        m1,m2=synthetic_pair()
        put(m2,0x2000+0x30,"f",float("nan"))
        with self.assertRaises(ValueError):
            audit_environment_geometry(m1,m2,strict_size=False)

    def test_fails_if_scene_is_not_golf(self):
        m1,m2=synthetic_pair()
        put(m2,0x100+0x54,"I",3)
        with self.assertRaises(ValueError):
            audit_environment_geometry(m1,m2,strict_size=False)

    def test_requires_real_native_sizes_by_default(self):
        m1,m2=synthetic_pair()
        with self.assertRaises(ValueError):
            audit_environment_geometry(m1,m2)

    def test_not_called_club_or_golfer_transform(self):
        m1,m2=synthetic_pair()
        r=audit_environment_geometry(m1,m2,strict_size=False)
        self.assertFalse(r["club_head_pose_verified"])
        self.assertFalse(r["golfer_body_pose_verified"])
        self.assertFalse(r["output_yards_or_meters_calibrated"])
        self.assertFalse(r["allowed_to_publish"])

if __name__=="__main__":
    unittest.main()
