"""Offline tests for the source-constrained golf outcome RAM snapshot/ranker."""
import itertools
import struct
import unittest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from wii_ai_golf.audit.outcome_transition import (
    capture_outcome_windows, rank_outcome_candidates)


_FAKE_FRAMES = itertools.count(100, 3)


def snapshot(phase, words, base=0x91000000, *, frame=None, end=None, mode=4):
    # Entirely fabricated ordered RPC brackets. No live Dolphin or game evidence.
    start = next(_FAKE_FRAMES) if frame is None else frame
    stop = start + 1 if end is None and type(start) is int else end
    payload = b"".join(struct.pack(">I", w) for w in words)
    return {"phase": phase, "game_id": "RSPE01", "disc_revision": 1,
            "game_mode_raw": mode, "frame_start": start, "frame_end": stop,
            "non_atomic_frame_span": (
                stop - start if type(start) is int and type(stop) is int else 1),
            "windows": {"golf_config": {
                "address": f"0x{base:08X}", "bytes_hex": payload.hex()}}}


class MockRPC:
    def __init__(self, *, header=b"RSPE01\x00\x01", mode=4):
        self.header, self.mode = header, mode
        self.calls, self.frame = [], 11
        self.pointers = {0x804BF8C4: 0x90010000,
                         0x804BF868: 0x90020000,
                         0x804BF708: 0x90030000}

    def call(self, name, args):
        self.calls.append((name, args))
        if name == "frame.get_count":
            self.frame += 1
            return self.frame
        if name == "memory.read_u32":
            addr = args[0]
            if addr in self.pointers:
                return self.pointers[addr]
            if addr == 0x90010094:
                return self.mode
            return 0
        if name == "memory.read_bytes":
            addr, size = args
            if addr == 0x80000000:
                return self.header.hex()
            return (b"\x00" * size).hex()
        raise AssertionError(name)


class OutcomeTransitionTests(unittest.TestCase):
    def test_revision_gate_comes_before_struct_reads(self):
        rpc = MockRPC(header=b"RSPE01\x00\x00")
        with self.assertRaisesRegex(RuntimeError, "revision 1"):
            capture_outcome_windows(rpc, "pre")
        self.assertFalse(any(n == "memory.read_u32" for n, _ in rpc.calls))

    def test_training_mode_gate(self):
        rpc = MockRPC(mode=3)
        with self.assertRaisesRegex(RuntimeError, "training mode"):
            capture_outcome_windows(rpc, "pre")
        self.assertEqual(len([x for x in rpc.calls if x[0] == "memory.read_bytes"]), 1)

    def test_bounded_read_only_snapshot(self):
        rpc = MockRPC()
        value = capture_outcome_windows(rpc, "pre")
        self.assertEqual(value["game_id"], "RSPE01")
        self.assertEqual(value["game_mode_raw"], 4)
        self.assertLessEqual(value["bytes_read"], 12 * 1024)
        self.assertGreater(value["frame_end"], value["frame_start"])
        self.assertFalse(any("write" in n or "set_" in n or "save" in n
                             for n, _ in rpc.calls))

    def test_pre_stable_post_changed_settled_stable(self):
        good = struct.unpack(">I", struct.pack(">f", 12.5))[0]
        rows = [snapshot("pre", [1, 0, 8]), snapshot("pre", [1, 0, 9]),
                snapshot("post", [1, 5, 10]), snapshot("post", [1, 9, 11]),
                snapshot("settled", [1, good, 12]),
                snapshot("settled", [1, good, 13])]
        report = rank_outcome_candidates(rows, human_distance=12.5)
        self.assertEqual(report["all_phase_stable_change_count"], 1)
        row = report["candidates"][0]
        self.assertEqual(row["address"], "0x91000004")
        self.assertEqual(row["matches_displayed_numeric_label_as"], ["f32"])
        self.assertFalse(report["game_score_verified"])

    def test_pre_or_settled_volatility_is_filtered(self):
        rows = [snapshot("pre", [0, 1]), snapshot("pre", [1, 1]),
                snapshot("post", [2, 2]), snapshot("settled", [3, 3]),
                snapshot("settled", [4, 3])]
        result = rank_outcome_candidates(rows)
        self.assertEqual(result["all_phase_stable_change_count"], 1)
        self.assertEqual(result["candidates"][0]["address"], "0x91000004")

    def test_transient_motion_not_mistaken_for_landing(self):
        rows = [snapshot("pre", [10]), snapshot("pre", [10]),
                snapshot("post", [99]), snapshot("settled", [10]),
                snapshot("settled", [10])]
        self.assertEqual(rank_outcome_candidates(rows)["all_phase_stable_change_count"], 0)

    def test_excludes_conflicting_nonatomic_overlapping_reads(self):
        a = snapshot("pre", [10])
        a["windows"]["golf_field"] = {
            "address": "0x91000000", "bytes_hex": struct.pack(">I", 11).hex()}
        rows = [a, snapshot("pre", [10]), snapshot("settled", [20]), snapshot("settled", [20])]
        result = rank_outcome_candidates(rows)
        self.assertEqual(result["all_phase_stable_change_count"], 0)

    def test_phase_order_required(self):
        rows = [snapshot("pre", [0]), snapshot("settled", [1]),
                snapshot("pre", [0]), snapshot("settled", [1])]
        with self.assertRaises(ValueError):
            rank_outcome_candidates(rows)

    def test_reversed_frames_are_not_ranked_even_with_matching_100(self):
        rows = [snapshot("pre", [0], frame=500),
                snapshot("pre", [0], frame=503),
                snapshot("settled", [100], frame=100),
                snapshot("settled", [100], frame=103)]
        with self.assertRaisesRegex(ValueError, "overlapping or reversed"):
            rank_outcome_candidates(rows, human_distance=100)

    def test_overlapping_frame_brackets_fail_closed(self):
        rows = [snapshot("pre", [0], frame=100, end=104),
                snapshot("pre", [0], frame=103, end=105),
                snapshot("settled", [2], frame=110),
                snapshot("settled", [2], frame=113)]
        with self.assertRaisesRegex(ValueError, "overlapping or reversed"):
            rank_outcome_candidates(rows)

    def test_frame_bracket_metadata_is_strict_and_bounded(self):
        rows = [snapshot("pre", [0]), snapshot("pre", [0]),
                snapshot("settled", [2]), snapshot("settled", [2])]
        for key, value in (("frame_start", None), ("frame_end", True),
                           ("frame_start", -1), ("frame_end", 2.0)):
            with self.subTest(key=key, value=value):
                changed = [dict(x) for x in rows]
                changed[0][key] = value
                with self.assertRaisesRegex(ValueError, "frame bracket"):
                    rank_outcome_candidates(changed)
        too_long = [dict(x) for x in rows]
        too_long[0]["frame_end"] = too_long[0]["frame_start"] + 121
        with self.assertRaisesRegex(ValueError, "beyond-bound"):
            rank_outcome_candidates(too_long)
        for bad in (None, True, 1.0, 99):
            with self.subTest(span=bad):
                changed = [dict(x) for x in rows]
                changed[0]["non_atomic_frame_span"] = bad
                with self.assertRaisesRegex(ValueError, "non-atomic frame span"):
                    rank_outcome_candidates(changed)
        missing = [dict(x) for x in rows]
        del missing[0]["non_atomic_frame_span"]
        with self.assertRaisesRegex(ValueError, "missing/inconsistent"):
            rank_outcome_candidates(missing)

    def test_wrong_mode_or_boolean_revision_rejected(self):
        rows = [snapshot("pre", [0]), snapshot("pre", [0]),
                snapshot("settled", [2]), snapshot("settled", [2])]
        for key, value in (("game_mode_raw", 3), ("game_mode_raw", True),
                           ("game_mode_raw", 4.0), ("disc_revision", True)):
            with self.subTest(key=key, value=value):
                changed = [dict(x) for x in rows]
                changed[1][key] = value
                with self.assertRaisesRegex(ValueError, "game/revision/mode"):
                    rank_outcome_candidates(changed)

    def test_monotonic_brackets_do_not_prove_physics_or_score(self):
        rows = [snapshot("pre", [0], frame=10, end=11),
                snapshot("pre", [0], frame=11, end=11),
                snapshot("settled", [3], frame=20, end=20),
                snapshot("settled", [3], frame=21, end=22)]
        report = rank_outcome_candidates(rows)
        self.assertEqual(report["all_phase_stable_change_count"], 1)
        self.assertTrue(report["sample_rpc_frame_brackets_ordered"])
        self.assertTrue(report["sample_rpc_non_atomic_spans_consistent"])
        self.assertFalse(report["same_boot_or_guest_physics_frame_verified"])
        self.assertFalse(report["game_score_verified"])

    def test_invalid_manual_label_and_counts(self):
        with self.assertRaises(ValueError):
            rank_outcome_candidates([snapshot("pre", [1]), snapshot("settled", [1])])
        rows = [snapshot("pre", [1]), snapshot("pre", [1]),
                snapshot("settled", [2]), snapshot("settled", [2])]
        with self.assertRaises(ValueError):
            rank_outcome_candidates(rows, human_distance=float("nan"))


if __name__ == "__main__":
    unittest.main()
