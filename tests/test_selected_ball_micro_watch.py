"""Fabricated Rev1 source map only; NEVER a real emulator or private dump."""
from __future__ import annotations
from pathlib import Path
import json
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.integration import selected_ball_micro_watch as m


def dform(op, rt, ra, imm):
    return op << 26 | rt << 21 | ra << 16 | (imm & 0xFFFF)


def add(dst, base, other):
    return 31 << 26 | dst << 21 | base << 16 | other << 11 | 266 << 1


def fabricated():
    manager = 0x80500000
    scene = 0x91001000
    config = 0x91002000
    field = 0x91003000
    pm = 0x91004000
    main = 0x91008000
    rec = pm + 4
    ball = 0x91005000
    start = 0x91006000
    xyz = (0x41300000, 0x40000000, 0xC1900000)
    words = {
        m.MEM1_BASE: m.GAME_REV1_HEADER[0],
        m.MEM1_BASE + 4: m.GAME_REV1_HEADER[1],
        m.STATIC_SCENE: manager,
        manager + 0x0C: scene, manager + 0x18: 5,
        scene + 0x1C: 5, scene + 0x20: manager, scene + 0x54: 2,
        scene + 0x9C: main, main: 0x803C779C,
        m.STATIC_CONFIG: config, config + 0x94: 4, config + 0x98: 1,
        m.STATIC_FIELD: field, field + 0x50: start,
        m.STATIC_PLAYER_MANAGER: pm, pm: 0x803C7DD4, pm + 0x334: rec,
        rec + 0x88: ball, ball: m.BALL_DATA_START + 4,
        ball + 0x4C: ball + 0x30,
        start + 0x48: start + 0x0C,
        start + 0x4C: start + 0x30,
    }
    for pc, op, dst, base, imm in m._SOURCE_DFORMS:
        words[pc] = dform(op, dst, base, imm)
    words[0x802A31F0] = add(3, 29, 0)
    for i, value in enumerate(xyz):
        for location in (rec + 0x54, rec + 0x60,
                         ball + 0x30, start + 0x30):
            words[location + 4 * i] = value
    return words, {"manager": manager, "scene": scene,
                   "config": config, "field": field, "pm": pm,
                   "rec": rec, "ball": ball, "start": start, "main": main}


class FakeSource:
    def __init__(self, words, begin=10, end=None):
        self.words = words
        self.begin = begin
        self.end = begin if end is None else end
        self.calls = []

    def read(self, address):
        self.calls.append(address)
        return self.words[address]

    def frame(self):
        self._asked = getattr(self, "_asked", 0) + 1
        return self.begin if self._asked % 2 else self.end


class SelectedBallMicroWatchTests(unittest.TestCase):
    def setUp(self):
        self.words, self.ref = fabricated()
        self.fake = FakeSource(self.words)
        self.watch = m.SelectedBallMicroWatch("synthetic-boot-token")

    def sample(self, stage="idle_before"):
        return self.watch.capture(stage, self.fake.read, self.fake.frame)

    def test_first_frame_has_source_gated_schema_and_no_output(self):
        out = StringIO()
        with redirect_stdout(out):
            diagnostic = self.sample()
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(diagnostic.stage, "idle_before")
        self.assertLessEqual(diagnostic.read_count, m.MAX_U32_READS_PER_CAPTURE)
        self.assertEqual(diagnostic.read_count, len(self.fake.calls))
        self.assertEqual(diagnostic.frame_span, 0)
        private = self.watch.private_samples()
        self.assertEqual(len(private), 1)
        sample = private[0]
        self.assertEqual(sample["selected_record_index"], 0)
        self.assertEqual(sample["selected_ball_vec"], sample["current_start_vec"])
        self.assertEqual(sample["selected_ball_vec"], sample["record_pos_054_vec"])
        self.assertEqual(sample["selected_ball_vec"], sample["record_pos_060_vec"])
        self.assertEqual(sample["source_path_gates_passed"], True)
        self.assertEqual(sample["acquisition_source"], "same_felk_frame_coroutine")
        self.assertEqual(set(sample), {
            "stage", "boot_token", "game_id", "revision", "scene_id",
            "sport_id", "game_mode", "hole_index", "selected_record_index",
            "frame_start", "frame_end", "acquisition_source",
            "source_path_gates_passed", "selected_record_pointer",
            "ball_owner_pointer", "start_object_pointer", "selected_ball_vec",
            "current_start_vec", "record_pos_054_vec", "record_pos_060_vec"
        })
        self.assertNotIn("selected_ball_vec", json.dumps(self.watch.safe_diagnostics()))
        self.assertNotIn("boot_token", json.dumps(self.watch.safe_diagnostics()))
        self.assertNotIn(str(self.ref["ball"]), json.dumps(self.watch.safe_diagnostics()))

    def test_four_stage_order_and_nonoverlap(self):
        for i, stage in enumerate(m.STAGES):
            self.fake = FakeSource(self.words, begin=10 + 10*i)
            self.sample(stage)
        self.assertEqual(len(self.watch.private_samples()), 4)
        self.assertEqual(len(self.watch.safe_diagnostics()), 4)
        with self.assertRaises(m.WatchRejected):
            self.sample("idle_before")

    def test_wrong_stage_or_repeated_stage_fails_without_writing(self):
        with self.assertRaises(m.WatchRejected):
            self.sample("event_after")
        self.assertEqual(self.watch.private_samples(), [])
        self.sample()
        with self.assertRaises(m.WatchRejected):
            self.sample()
        self.assertEqual(len(self.watch.private_samples()), 1)

    def test_wrong_revision_and_corrupt_code_gate_fail_closed(self):
        self.words[m.MEM1_BASE + 4] = 0
        with self.assertRaises(m.WatchRejected):
            self.sample()
        self.words[m.MEM1_BASE + 4] = m.GAME_REV1_HEADER[1]
        self.words[0x802A03B8] = 0
        with self.assertRaises(m.WatchRejected):
            self.sample()
        self.assertEqual(len(self.watch.private_samples()), 0)

    def test_scene_mode_hole_and_backlink_rejection(self):
        for address, value in [
            (self.ref["scene"] + 0x54, 0),
            (self.ref["scene"] + 0x20, 0),
            (self.ref["config"] + 0x94, 3),
            (self.ref["config"] + 0x98, 42),
        ]:
            before = self.words[address]
            self.words[address] = value
            with self.assertRaises(m.WatchRejected):
                self.sample()
            self.words[address] = before
        self.assertFalse(self.watch.private_samples())

    def test_source_manager_firstwords_required(self):
        for addr in (self.ref["pm"], self.ref["main"]):
            before = self.words[addr]
            self.words[addr] = 0
            with self.assertRaises(m.WatchRejected):
                self.sample()
            self.words[addr] = before
        self.assertEqual(self.watch.private_samples(), [])

    def test_selected_record_is_exact_inline_slot(self):
        self.words[self.ref["pm"] + 0x334] = 0x91007770
        with self.assertRaises(m.WatchRejected):
            self.sample()

    def test_ball_firstword_and_selfref_required(self):
        ball = self.ref["ball"]
        for key, wrong in ((ball, 0x803C7DD0),
                           (ball + 0x4C, 0xDEADBEEF)):
            original = self.words[key]
            self.words[key] = wrong
            with self.assertRaises(m.WatchRejected):
                self.sample()
            self.words[key] = original

    def test_start_selfrefs_required(self):
        start = self.ref["start"]
        for key in (start + 0x48, start + 0x4C):
            v = self.words[key]
            self.words[key] = 0
            with self.assertRaises(m.WatchRejected):
                self.sample()
            self.words[key] = v

    def test_no_memory_read_from_unmapped_regions(self):
        self.words[self.ref["pm"] + 0x334] = 0x94000000
        with self.assertRaises(m.WatchRejected):
            self.sample()
        self.assertTrue(all(
            m._mapped(a, 4, region="MEM1") or
            m._mapped(a, 4, region="MEM2")
            for a in self.fake.calls))

    def test_frame_bracket_can_span_at_most_two_frames(self):
        self.fake = FakeSource(self.words, begin=10, end=12)
        self.assertEqual(self.sample().frame_span, 2)
        self.assertEqual(len(self.watch.private_samples()), 1)

    def test_frame_bracket_more_than_two_frames_rejected(self):
        self.fake = FakeSource(self.words, begin=10, end=13)
        with self.assertRaises(m.WatchRejected):
            self.sample()
        self.assertEqual(self.watch.private_samples(), [])

    def test_frame_rewind_and_overlap_rejected(self):
        self.fake = FakeSource(self.words, begin=10, end=10)
        self.sample()
        self.fake = FakeSource(self.words, begin=10, end=10)
        with self.assertRaises(m.WatchRejected):
            self.sample("idle_after")
        self.assertEqual(len(self.watch.private_samples()), 1)
        self.fake = FakeSource(self.words, begin=9, end=8)
        with self.assertRaises(m.WatchRejected):
            self.sample("idle_after")

    def test_read_failure_never_exposes_raw_address_or_path(self):
        bad = lambda addr: (_ for _ in ()).throw(
            RuntimeError("SecretPath/PRIVATE.raw 0x91004000"))
        with self.assertRaises(m.WatchRejected) as ctx:
            self.watch.capture("idle_before", bad, self.fake.frame)
        self.assertNotIn("SecretPath", str(ctx.exception))
        self.assertNotIn("0x9100", str(ctx.exception))
        self.assertEqual(self.watch.private_samples(), [])

    def test_bad_u32_values_rejected_not_converted(self):
        self.words[self.ref["rec"] + 0x54] = -1
        with self.assertRaises(m.WatchRejected):
            self.sample()
        self.words[self.ref["rec"] + 0x54] = True
        with self.assertRaises(m.WatchRejected):
            self.sample()

    def test_private_sample_returns_deep_enough_copy(self):
        self.sample()
        prior = self.watch.private_samples()
        prior[0]["selected_ball_vec"][0] = 0
        self.assertNotEqual(self.watch.private_samples()[0]["selected_ball_vec"][0], 0)

    def test_disabled_by_default_and_no_bridge_or_swing_side_effects(self):
        self.assertFalse(hasattr(m, "patch_bridge"))
        self.assertFalse(hasattr(m, "launch_dolphin"))
        self.assertFalse(hasattr(m, "send_controller"))
        self.assertEqual(len(self.watch.private_samples()), 0)
        self.assertEqual(len(self.fake.calls), 0)

    def test_bad_session_token_rejected(self):
        for bad in ("short", "", None, 123, "x"*129):
            with self.assertRaises(ValueError):
                m.SelectedBallMicroWatch(bad)

    def test_source_read_limit_is_strict(self):
        self.sample()
        self.assertLessEqual(len(self.fake.calls), 48)
        self.assertLess(len(self.fake.calls), 48)  # budget slack under ideal callback


if __name__ == "__main__":
    unittest.main()
