"""Offline read-only discovery tests. Moving float vectors are NOT ball proof."""
import struct
import unittest
from unittest.mock import patch

from wii_ai_golf.ball_discovery import (
    snapshot_windows, analyze_samples, MAX_TOTAL_BYTES
)


def baseline(supported=True, mode="0x00000004"):
    return {"game_id": "RSPE01" if supported else "RSPP01", "disc_revision": 1,
            "supported": supported, "fields": {
                "golf_config": {"instance_pointer": "0x91BF16B0",
                                "raw_fields": {"game_mode_raw": {"value_hex": mode}}},
                "golf_field": {"instance_pointer": "0x91BF4210"},
                "sports_sequence": {"instance_pointer": "0x91B699B0"}}}


class RPC:
    def __init__(self):
        self.calls = []

    def call(self, method, args):
        self.calls.append((method, args))
        if method == "memory.read_u32":
            return 0x91BF48BC
        if method == "memory.read_bytes":
            return ("00000000" * ((args[1] + 3) // 4))[:args[1] * 2]
        raise AssertionError(method)


class DiscoveryTests(unittest.TestCase):
    def test_version_gating_prevents_struct_reads(self):
        rpc = RPC()
        with patch("wii_ai_golf.ball_discovery.probe_rev1", return_value=baseline(False)):
            result = snapshot_windows(rpc)
        self.assertEqual(result["read_bytes"], 0)
        self.assertEqual(rpc.calls, [])

    def test_mode_gating(self):
        rpc = RPC()
        with patch("wii_ai_golf.ball_discovery.probe_rev1",
                   return_value=baseline(mode="0x00000003")):
            result = snapshot_windows(rpc)
        self.assertEqual(result["read_bytes"], 0)

    def test_read_budget_chunks_and_no_writes(self):
        rpc = RPC()
        with patch("wii_ai_golf.ball_discovery.probe_rev1", return_value=baseline()):
            result = snapshot_windows(rpc)
        self.assertGreater(result["read_bytes"], 0)
        self.assertLessEqual(result["read_bytes"], MAX_TOTAL_BYTES)
        self.assertTrue(all(method.startswith("memory.read_") for method, _ in rpc.calls))
        self.assertTrue(all(args[1] <= 1024 for method, args in rpc.calls
                            if method == "memory.read_bytes"))

    def test_synthetic_moving_vector_ranked_not_declared_ball(self):
        def snap(i):
            raw = b"\0" * 8 + struct.pack(">fff", float(i*4), float(i), float(-i*3)) + b"\0" * 20
            return {"game_id": "RSPE01", "disc_revision": 1, "windows": {
                "minimap_ball_effect": {"address": "0x91BF48BC", "bytes_hex": raw.hex()}}}
        result = analyze_samples([snap(i) for i in range(6)], min_changed=3)
        self.assertGreater(result["candidate_count"], 0)
        self.assertTrue(any(x["offset_hex"] == "+0x8" for x in result["candidates"]))
        self.assertIn("Do not treat", result["warning"])

    def test_small_changing_integers_ranked_but_not_named_scores(self):
        def sample(i):
            raw = b"\0" * 8 + struct.pack(">I", i) + b"\0" * 16
            return {"game_id": "RSPE01", "disc_revision": 1, "windows": {
                "golf_config": {"address": "0x91BF16B0", "bytes_hex": raw.hex()}}}
        result = analyze_samples([sample(i) for i in range(7)], min_changed=3)
        self.assertGreater(result["scalar_candidate_count"], 0)
        self.assertTrue(any(x["offset_hex"] == "+0x8"
                            for x in result["scalar_candidates"]))
        self.assertTrue(all("NOT_score" in x["status"]
                            for x in result["scalar_candidates"]))

    def test_constant_vectors_not_moving_candidates(self):
        fixed = {"game_id": "RSPE01", "disc_revision": 1, "windows": {
            "golf_field": {"address": "0x91BF4210", "bytes_hex": "00" * 48}}}
        self.assertEqual(analyze_samples([fixed]*6)["candidate_count"], 0)


if __name__ == "__main__":
    unittest.main()
