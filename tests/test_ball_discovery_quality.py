"""Regression tests for scene-conditioned, bounded read-only discovery."""
import struct
import unittest
from unittest.mock import patch

from wii_ai_golf.ball_discovery import WINDOWS, analyze_samples, snapshot_windows


def baseline():
    return {
        "game_id": "RSPE01", "disc_revision": 1, "supported": True,
        "fields": {
            "golf_config": {
                "instance_pointer": "0x91BF16B0",
                "raw_fields": {"game_mode_raw": {"value_hex": "0x00000004"}},
            },
            "golf_field": {
                "instance_pointer": "0x91BF4210",
                "raw_fields": {
                    "current_pin_obj_ptr": {"value_hex": "0x924B8214"},
                    "current_start_obj_ptr": {"value_hex": "0x924B7C80"},
                    "cup_obj_ptr": {"value_hex": "0x91BF45C8"},
                },
            },
            "sports_sequence": {"instance_pointer": "0x91B699B0"},
        },
    }


class FakeRPC:
    def __init__(self):
        self.calls = []
        self.frame = 900

    def call(self, method, params):
        self.calls.append((method, params))
        if method == "frame.get_count":
            self.frame += 3
            return self.frame
        if method == "memory.read_u32":
            return 0x91BF48BC
        if method == "memory.read_bytes":
            addr, n = params
            if n == 12:
                by_addr = {
                    0x924B8214 + 0x30: (210.1, -7, -350.5),
                    0x924B7C80 + 0x30: (2.2, -5.5, -318),
                    0x91BF45C8 + 0x30: (210.1, -7.04664, -350.5),
                }
                if addr in by_addr:
                    return struct.pack(">fff", *by_addr[addr]).hex()
            return bytes(n).hex()
        raise AssertionError(method)


def sample(i, tee=1):
    return {
        "game_id": "RSPE01", "disc_revision": 1,
        "scene": {"scene_status": "aligned_candidate",
                  "tee_index_observed": tee, "pin_variant_observed": 1},
        "windows": {"minimap_ball_effect": {
            "address": "0x91BF48BC",
            "bytes_hex": (
                bytes(8) + struct.pack(">fff", float(i * 2), float(i),
                                       float(i * 3)) + bytes(20)
            ).hex(),
        }},
    }


class BallDiscoveryQualityTests(unittest.TestCase):
    def test_fast_profile_is_smaller_but_has_same_window_names(self):
        rpc = FakeRPC()
        with patch("wii_ai_golf.ball_discovery.probe_rev1", return_value=baseline()):
            broad = snapshot_windows(rpc, profile="broad")
            fast = snapshot_windows(rpc, profile="fast")
        self.assertGreater(broad["read_bytes"], fast["read_bytes"])
        self.assertEqual(len(bytes.fromhex(fast["windows"]["golf_config"]["bytes_hex"])), 0xC0)
        self.assertEqual(set(fast["windows"]), set(WINDOWS))

    def test_frame_provenance_and_live_grounded_scene(self):
        rpc = FakeRPC()
        with patch("wii_ai_golf.ball_discovery.probe_rev1", return_value=baseline()):
            data = snapshot_windows(rpc, profile="fast",
                                    capture_geometry=True, record_frames=True)
        self.assertEqual(data["frame_span"], 3)
        self.assertEqual(data["scene"]["tee_index_observed"], 1)
        self.assertEqual(data["scene"]["pin_variant_observed"], 1)
        self.assertEqual(data["scene"]["scene_status"], "aligned_candidate")
        self.assertTrue(all(method.startswith("memory.read_") or method == "frame.get_count"
                            for method, _ in rpc.calls))

    def test_scene_switch_not_counted_as_within_scene_ball_motion(self):
        samples = [sample(i, 1 if i < 3 else 2) for i in range(6)]
        result = analyze_samples(samples, min_changed=3)
        candidate = next(x for x in result["candidates"] if x["offset_hex"] == "+0x8")
        self.assertEqual(candidate["changed_steps"], 5)
        self.assertEqual(candidate["within_same_scene_changed_steps"], 4)
        self.assertEqual(candidate["cross_scene_changed_steps"], 1)

    def test_missing_sample_not_falsely_counted_as_motion(self):
        samples = [sample(i) for i in range(6)]
        samples[2]["windows"] = {}
        ranked = analyze_samples(samples, min_changed=1)
        candidate = next(x for x in ranked["candidates"] if x["offset_hex"] == "+0x8")
        self.assertEqual(candidate["changed_steps"], 3)

    def test_invalid_profile_rejected_before_any_rpc(self):
        rpc = FakeRPC()
        with self.assertRaises(ValueError):
            snapshot_windows(rpc, profile="whole-console-ram")
        self.assertEqual(rpc.calls, [])


if __name__ == "__main__":
    unittest.main()
