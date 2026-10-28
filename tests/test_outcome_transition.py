"""Offline tests for the source-constrained golf outcome RAM snapshot/ranker."""
import struct
import unittest
from itertools import count
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from wii_ai_golf.audit.outcome_transition import (
    capture_outcome_windows, rank_outcome_candidates)


_NEXT_FRAME = count(100, 3)


def snapshot(phase, words, base=0x91000000):
    payload = b"".join(struct.pack(">I", w) for w in words)
    frame = next(_NEXT_FRAME)
    return {"phase": phase, "game_id": "RSPE01", "disc_revision": 1,
            "game_mode_raw": 4,
            "frame_start": frame, "frame_end": frame + 1,
            "non_atomic_frame_span": 1,
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

    def test_invalid_manual_label_and_counts(self):
        with self.assertRaises(ValueError):
            rank_outcome_candidates([snapshot("pre", [1]), snapshot("settled", [1])])
        rows = [snapshot("pre", [1]), snapshot("pre", [1]),
                snapshot("settled", [2]), snapshot("settled", [2])]
        with self.assertRaises(ValueError):
            rank_outcome_candidates(rows, human_distance=float("nan"))


    def test_guest_frame_brackets_monotonic_but_not_a_physics_clock(self):
        rows = [snapshot("pre", [0]), snapshot("pre", [0]),
                snapshot("post", [1]),
                snapshot("settled", [2]), snapshot("settled", [2])]
        report = rank_outcome_candidates(rows)
        self.assertEqual(report["all_phase_stable_change_count"], 1)
        self.assertTrue(report["guest_frame_brackets_monotonic"])
        self.assertFalse(report["same_boot_or_simulation_step_verified"])

    def test_reversed_guest_frames_refuse_false_terminal_match(self):
        rows = [snapshot("pre", [0]), snapshot("pre", [0]),
                snapshot("settled", [100]), snapshot("settled", [100])]
        # Phase names remain sorted, but the 'settled' frame is older.
        rows[2]["frame_start"] = rows[0]["frame_start"] - 12
        rows[2]["frame_end"] = rows[2]["frame_start"] + 1
        rows[3]["frame_start"] = rows[2]["frame_end"] + 1
        rows[3]["frame_end"] = rows[3]["frame_start"] + 1
        with self.assertRaisesRegex(ValueError, "reversed or overlapping"):
            rank_outcome_candidates(rows, human_distance=100.0)

    def test_overlapping_snapshots_refused_even_with_ordered_phase_names(self):
        rows = [snapshot("pre", [0]), snapshot("pre", [0]),
                snapshot("settled", [100]), snapshot("settled", [100])]
        rows[2]["frame_start"] = rows[1]["frame_end"] - 1
        rows[2]["frame_end"] = rows[2]["frame_start"] + 1
        with self.assertRaisesRegex(ValueError, "overlapping"):
            rank_outcome_candidates(rows)

    def test_invalid_or_missing_frame_metadata_fail_closed(self):
        for key, value in (("frame_start", None), ("frame_end", True),
                           ("frame_start", -1), ("frame_end", 0x100000000),
                           ("non_atomic_frame_span", "1"),
                           ("non_atomic_frame_span", 12)):
            with self.subTest(key=key, value=value):
                rows = [snapshot("pre", [1]), snapshot("pre", [1]),
                        snapshot("settled", [2]), snapshot("settled", [2])]
                rows[2][key] = value
                with self.assertRaisesRegex(ValueError, "frame bracket or span"):
                    rank_outcome_candidates(rows)

    def test_mismatched_mode_and_revision_are_rejected(self):
        for field, invalid in (("game_mode_raw", 3), ("game_mode_raw", None),
                               ("game_mode_raw", True), ("disc_revision", 0),
                               ("disc_revision", True), ("game_id", "RSPE02")):
            with self.subTest(field=field, invalid=invalid):
                rows = [snapshot("pre", [1]), snapshot("pre", [1]),
                        snapshot("settled", [2]), snapshot("settled", [2])]
                rows[3][field] = invalid
                with self.assertRaisesRegex(ValueError, "game/revision/mode-4"):
                    rank_outcome_candidates(rows)


if __name__ == "__main__":
    unittest.main()
