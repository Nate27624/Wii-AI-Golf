import struct
import unittest
from unittest.mock import patch

from wii_ai_golf.spatial_probe import capture_spatial_rev1


def baseline(region="RSPE01", mode="0x00000004"):
    return {
        "game_id": region, "disc_revision": 1, "supported": region == "RSPE01",
        "fields": {
            "golf_config": {"raw_fields": {
                "game_mode_raw": {"value_hex": mode},
                "hole_raw": {"value_hex": "0x00000001"}}},
            "golf_field": {"plausible_mem_pointer": True, "raw_fields": {
                "current_pin_obj_ptr": {"value_hex": "0x924B8214"},
                "current_start_obj_ptr": {"value_hex": "0x924B7C80"},
                "cup_obj_ptr": {"value_hex": "0x91BF45C8"},
                "course_obj_ptr": {"value_hex": "0x00000000"},
                "minimap_course_obj_ptr": {"value_hex": "0xFFFFFFFF"},
            }},
        },
    }


class FakeRPC:
    def __init__(self):
        self.calls = []
    def call(self, method, params):
        self.calls.append((method, params))
        if method == "memory.read_bytes":
            return struct.pack(">fff", 1.25, 42.0, -10.5).hex()
        if method == "memory.read_u32":
            return 0x924B9000
        raise AssertionError(method)


class SpatialProbeTests(unittest.TestCase):
    def test_reads_expected_offsets_and_no_writes(self):
        rpc = FakeRPC()
        with patch("wii_ai_golf.spatial_probe.probe_rev1", return_value=baseline()):
            data = capture_spatial_rev1(rpc)
        self.assertEqual(data["mode_label"], "GAMEMODE_TR_NEARPIN")
        self.assertEqual(data["map_objects"]["current_pin_obj_ptr"]["inline_translation_offset_0x30"]["xyz_raw"], [1.25, 42.0, -10.5])
        self.assertIn(("memory.read_bytes", [0x924B8214 + 0x30, 12]), rpc.calls)
        self.assertIn(("memory.read_u32", [0x924B8214 + 0x44]), rpc.calls)
        self.assertEqual(data["map_objects"]["course_obj_ptr"]["status"], "null_or_invalid_map_object_pointer")
        self.assertTrue(all(x[0].startswith("memory.read_") for x in rpc.calls))

    def test_unsupported_region_does_not_read_objects(self):
        rpc = FakeRPC()
        with patch("wii_ai_golf.spatial_probe.probe_rev1", return_value=baseline(region="RSPP01")):
            data = capture_spatial_rev1(rpc)
        self.assertEqual(data["map_objects"], {})
        self.assertFalse(data["supported"])
        self.assertEqual(rpc.calls, [])

    def test_wrong_mode_no_object_reads(self):
        rpc = FakeRPC()
        with patch("wii_ai_golf.spatial_probe.probe_rev1", return_value=baseline(mode="0x00000009")):
            data = capture_spatial_rev1(rpc)
        self.assertEqual(data["mode_label"], "other_or_unknown")
        self.assertEqual(rpc.calls, [])

    def test_nonfinite_coords_marked_unverified(self):
        rpc = FakeRPC()
        def read(method, params):
            if method == "memory.read_u32":
                return 0
            return struct.pack(">fff", float("nan"), 0.0, 0.0).hex()
        rpc.call = read
        with patch("wii_ai_golf.spatial_probe.probe_rev1", return_value=baseline()):
            data = capture_spatial_rev1(rpc)
        self.assertIsNone(data["map_objects"]["cup_obj_ptr"]["inline_translation_offset_0x30"]["xyz_raw"])
        self.assertEqual(data["map_objects"]["cup_obj_ptr"]["pointed_translation"]["status"], "null_or_invalid_pointer")

    def test_invalid_byte_response_rejected(self):
        rpc = FakeRPC()
        rpc.call = lambda method, params: "bad" if method == "memory.read_bytes" else 0
        with patch("wii_ai_golf.spatial_probe.probe_rev1", return_value=baseline()):
            with self.assertRaises(ValueError):
                capture_spatial_rev1(rpc)


if __name__ == "__main__":
    unittest.main()
