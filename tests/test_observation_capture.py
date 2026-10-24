"""Offline-only mock tests; do not assert real Wii Sports scoring."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

from wii_ai_golf.observation_capture import capture, compare, parse_range, write_snapshot


class FakeReader:
    def __init__(self):
        self.mem = bytearray(8192)
        self.frame = 10
        self.calls = []

    def call(self, method, params=None):
        self.calls.append((method, params))
        self.frame += 1
        if method == "bridge.ping":
            return {"bridge_version": "mock-0"}
        if method == "frame.get_count":
            return self.frame
        if method == "controller.get_wiimote_buttons":
            return {"A": False, "Plus": False}
        if method == "controller.get_wiimote_pointer":
            return [0.0, 0.0]
        if method in ("controller.get_wiimote_acceleration", "controller.get_wiimote_angular_velocity"):
            return [0.0, 1.0, 0.0]
        if method == "memory.read_bytes":
            address, length = params
            i = address - 0x80000000
            return bytes(self.mem[i:i + length]).hex()
        raise AssertionError(method)


class CaptureTests(unittest.TestCase):
    def test_parse_limits(self):
        self.assertEqual(parse_range("0x80000000:0x100"), (0x80000000, 256))
        for bad in ("abc", "0x80000000:-10", "0xFFFFFFFF:2", "0x80000000:65537"):
            with self.assertRaises(ValueError):
                parse_range(bad)

    def test_capture_has_no_write_commands_and_chunked(self):
        rpc = FakeReader()
        snap = capture(rpc, "green_01", [(0x80000000, 5000)])
        self.assertEqual(len(bytes.fromhex(snap["memory"][0]["hex"])), 5000)
        self.assertEqual(snap["controller"]["buttons"]["A"], False)
        self.assertTrue(snap["multi_frame_non_atomic"])
        calls = [c for c in rpc.calls if c[0] == "memory.read_bytes"]
        self.assertEqual([c[1][1] for c in calls], [2048, 2048, 904])
        self.assertFalse(any("write" in c[0] or "set" in c[0] or "savestate" in c[0]
                             for c in rpc.calls))

    def test_no_address_safe_preflight(self):
        self.assertEqual(capture(FakeReader(), "preflight")["memory"], [])

    def test_reject_oversized_scan_before_rpc(self):
        rpc = FakeReader()
        with self.assertRaises(ValueError):
            capture(rpc, "too_big", [(0x80000000, 65536), (0x80010000, 1)])
        self.assertEqual(rpc.calls, [])

    def test_write_no_overwrite_and_screenshot_hash(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            frame = p / "frame.png"
            frame.write_bytes(b"synthetic fake image bytes")
            snap = capture(FakeReader(), "shot", screenshot_path=frame)
            self.assertEqual(len(snap["screenshot"]["sha256"]), 64)
            output = p / "snap.json"
            write_snapshot(snap, output)
            self.assertEqual(json.loads(output.read_text())["label"], "shot")
            with self.assertRaises(FileExistsError):
                write_snapshot(snap, output)

    def test_diff_f32_big_endian_candidate(self):
        rpc = FakeReader()
        before = capture(rpc, "before", [(0x80000000, 32)])
        rpc.mem[8:12] = struct.pack(">f", 7.25)
        after = capture(rpc, "after", [(0x80000000, 32)])
        report = compare(before, after, target=7.25, tolerance=0.001)
        self.assertEqual(report["changed_bytes"], 2)
        self.assertTrue(any(c["address"] == "0x80000008" and c["type"] == "f32_be"
                            for c in report["candidate_matches"]))
        self.assertIn("unverified", report["source"])

    def test_diff_rejects_mismatch_and_nonfinite(self):
        rpc = FakeReader()
        a = capture(rpc, "a", [(0x80000000, 20)])
        b = capture(rpc, "b", [(0x80000014, 20)])
        with self.assertRaises(ValueError):
            compare(a, b)
        with self.assertRaises(ValueError):
            compare(a, a, target=float("nan"))


if __name__ == "__main__":
    unittest.main()
