"""Mocked capture lifecycle tests: no emulator, no user files."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for item in (str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")):
    if item in sys.path:
        sys.path.remove(item)
    sys.path.insert(0, item)
from scripts.collect_outcome_transition import run_session
from scripts.probe_swing import build_probe


def row(phase, value):
    return {"game_id": "RSPE01", "disc_revision": 1, "phase": phase,
            "frame_start": 1, "frame_end": 2,
            "windows": {"golf_config": {"address": "0x90010000",
                                       "bytes_hex": struct.pack(">I", value).hex()}}}


class OutcomeCaptureCliTests(unittest.TestCase):
    def test_one_swing_between_pre_and_post(self):
        got = []
        answers = iter(["", "", "", "yes", "yes", "12.5", "yd"])
        f32_bits = struct.unpack(">I", struct.pack(">f", 12.5))[0]

        def snapshot(_rpc, phase):
            got.append(phase)
            return row(phase, {"pre": 0, "post": 1, "settled": f32_bits}[phase])

        def swing(_rpc):
            got.append("swing")
            return {"state": "complete", "applied_frames": 89}

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "RAW.jsonl"
            result = run_session(object(), raw_path=path, pre_samples=2,
                post_samples=2, settled_samples=2, interval=0,
                input_fn=lambda q: next(answers), sleep_fn=lambda s: None,
                snapshot_fn=snapshot, swing_fn=swing)
            self.assertEqual(got,
                ["pre", "pre", "swing", "post", "post", "settled", "settled"])
            self.assertEqual(result["candidate_ranking"]["all_phase_stable_change_count"], 1)
            self.assertEqual(result["human_observation"]["displayed_distance_human"], 12.5)
            self.assertEqual(result["known_good_swing_request"]["generated_trace_frames"],
                             len(build_probe("forward", follow_through_frames=30)))
            self.assertFalse(result["candidate_ranking"]["game_score_verified"])
            self.assertEqual(len(path.read_text().splitlines()), 6)

    def test_early_cancel_does_not_write_or_swing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "RAW.jsonl"
            result = run_session(object(), raw_path=path, pre_samples=2,
                post_samples=2, settled_samples=2, interval=0,
                input_fn=lambda q: "q",
                swing_fn=lambda rpc: self.fail("must not swing"))
            self.assertTrue(result["cancelled"])
            self.assertFalse(path.exists())

    def test_cancel_after_baseline_saves_partial_without_swing(self):
        replies = iter(["", "q"])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "RAW.jsonl"
            result = run_session(object(), raw_path=path, pre_samples=2,
                post_samples=2, settled_samples=2, interval=0,
                input_fn=lambda q: next(replies),
                snapshot_fn=lambda rpc, phase: row(phase, 1),
                swing_fn=lambda rpc: self.fail("must not swing"))
            self.assertTrue(result["cancelled"])
            self.assertEqual(result["partial_samples"], 2)
            self.assertEqual(len(path.read_text().splitlines()), 2)

    def test_evidence_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "RAW.jsonl"
            path.write_text("preserve me")
            with self.assertRaises(FileExistsError):
                run_session(object(), raw_path=path, pre_samples=2,
                    post_samples=2, settled_samples=2, interval=0,
                    input_fn=lambda q: "",
                    snapshot_fn=lambda rpc, phase: row(phase, 1))
            self.assertEqual(path.read_text(), "preserve me")


if __name__ == "__main__":
    unittest.main()
