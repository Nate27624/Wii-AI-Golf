"""Fabricated addresses and word data: never opens a Dolphin emulator."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.integration import ball_watch_preflight as w


def fake_memory():
    manager, scene, config = 0x80500000, 0x91001000, 0x91002000
    field, start, pm, ball = 0x91003000, 0x91004000, 0x91005000, 0x91010000
    record = pm + 4
    vals = {
        0x80000000: 0x52535045, 0x80000004: 0x30310001,
        w.MANAGER_SLOT: manager, manager + 0x18: 5, manager + 0xC: scene,
        scene: w.SCENE_DATA[0], scene + 0x1C: 5,
        scene + 0x20: manager, scene + 0x54: 2,
        w.CONFIG_SLOT: config, config + 0x94: 4, config + 0x98: 1,
        w.FIELD_SLOT: field, field + 0x50: start,
        start + 0x4C: start + 0x30,
        w.PM_SLOT: pm, pm: w.PM_DATA[0], pm + 0x334: record,
        record + 0x88: ball, ball: w.BALL_DATA[0],
        ball + 0x4C: ball + 0x30,
    }
    for i, val in enumerate((0x3F800000, 0x40100000, 0x3F000000)):
        vals[start + 0x30 + 4*i] = val
        vals[ball + 0x30 + 4*i] = val
        vals[record + 0x54 + 4*i] = val
        vals[record + 0x60 + 4*i] = val
    return vals, {"manager":manager, "scene":scene, "pm":pm, "ball":ball,
                  "start":start, "record":record, "field":field}


def run(words, *, stage="idle_before", tick=None, source=True):
    calls = []
    def read(a):
        calls.append(a)
        return words[a]
    result = w.sample_pre_dispatch(
        read_u32=read, bridge_tick=(tick or (lambda: 100)),
        stage=stage, source_contract_reviewed=source)
    return result, calls


class FrameReadContractTests(unittest.TestCase):
    def test_four_vectors_and_budget_are_private_and_bounded(self):
        mem, p = fake_memory()
        out, reads = run(mem)
        self.assertEqual(out["stage"], "idle_before")
        self.assertEqual(out["selected_record_index"], 0)
        self.assertTrue(out["source_path_gates_passed"])
        self.assertEqual(out["private_words"]["selected_ball_vec"],
                         out["private_words"]["current_start_vec"])
        self.assertEqual(out["private_words"]["record_pos_054_vec"],
                         out["private_words"]["record_pos_060_vec"])
        self.assertLessEqual(len(reads), w.MAX_WORD_READS)
        self.assertEqual(len(reads), out["read_u32_call_count"])
        self.assertEqual(out["bridge_tick_start"], out["bridge_tick_end"])
        self.assertFalse(out["bridge_tick_verified_as_emulated_game_frame"])
        self.assertFalse(out["ball_world_xyz_verified"])

    def test_synthetic_controller_and_trace_not_touched(self):
        mem, _ = fake_memory()
        calls = ["A held", "swing requested", "A released"]
        before = list(calls)
        run(mem, stage="event_before")
        self.assertEqual(calls, before)

    def test_no_contract_or_unapproved_phase_fails_before_any_read(self):
        mem, _ = fake_memory()
        calls = []
        with self.assertRaises(w.UnverifiedSample):
            w.sample_pre_dispatch(read_u32=lambda a: calls.append(a),
                                  bridge_tick=lambda: 10, stage="idle_before")
        with self.assertRaises(w.UnverifiedSample):
            w.sample_pre_dispatch(read_u32=lambda a: calls.append(a),
                                  bridge_tick=lambda: 10, stage="unknown",
                                  source_contract_reviewed=True)
        self.assertEqual(calls, [])

    def test_invalid_game_and_training_mode_fail(self):
        for key, value in ((0x80000004, 0), (w.CONFIG_SLOT, 0)):
            mem, _ = fake_memory()
            mem[key] = value
            with self.assertRaises(w.UnverifiedSample):
                run(mem)
        mem, _ = fake_memory()
        mem[mem[w.CONFIG_SLOT] + 0x94] = 2
        with self.assertRaises(w.UnverifiedSample):
            run(mem)

    def test_scene_sport_and_backlink_are_hard_gates(self):
        mem, p = fake_memory()
        for addr, wrong in ((p["scene"]+0x54, 1),
                            (p["scene"]+0x20, p["manager"]+4),
                            (p["manager"]+0x18, 4)):
            altered = dict(mem)
            altered[addr] = wrong
            with self.subTest(addr=addr), self.assertRaises(w.UnverifiedSample):
                run(altered)

    def test_selected_record_must_be_one_of_four_source_records(self):
        mem, p = fake_memory()
        mem[p["pm"] + 0x334] = p["pm"] + 8
        with self.assertRaises(w.UnverifiedSample):
            run(mem)

    def test_wrong_vtable_region_or_relocated_start_is_rejected(self):
        mem, p = fake_memory()
        mem[p["ball"]] = w.PM_DATA[0]
        with self.assertRaises(w.UnverifiedSample):
            run(mem)
        mem, p = fake_memory()
        mem[p["start"] + 0x4C] = p["start"] + 0x38
        with self.assertRaises(w.UnverifiedSample):
            run(mem)

    def test_midread_selector_change_fails_closed(self):
        mem, p = fake_memory()
        seen = {}
        def moving(addr):
            seen[addr] = seen.get(addr, 0) + 1
            if addr == p["pm"] + 0x334 and seen[addr] > 1:
                return p["pm"] + 4 + 0xCC
            return mem[addr]
        with self.assertRaises(w.UnverifiedSample):
            w.sample_pre_dispatch(read_u32=moving, bridge_tick=lambda: 30,
                                  stage="event_after",
                                  source_contract_reviewed=True)

    def test_midread_ball_pointer_change_fails_closed(self):
        mem, p = fake_memory()
        seen = {}
        def moving(addr):
            seen[addr] = seen.get(addr, 0) + 1
            if addr == p["ball"] + 0x4C and seen[addr] > 1:
                return p["ball"] + 0x34
            return mem[addr]
        with self.assertRaises(w.UnverifiedSample):
            w.sample_pre_dispatch(read_u32=moving, bridge_tick=lambda: 30,
                                  stage="event_after",
                                  source_contract_reviewed=True)

    def test_tick_changes_during_callback_are_not_valid_frames(self):
        mem, _ = fake_memory()
        ticks = iter((300, 301))
        with self.assertRaises(w.UnverifiedSample):
            run(mem, tick=lambda: next(ticks))

    def test_bad_read_does_not_leak_address_or_contents(self):
        mem, p = fake_memory()
        def bad_read(addr):
            if addr == p["ball"]:
                raise RuntimeError("PRIVATE ADDR 0x91010000")
            return mem[addr]
        with self.assertRaises(w.UnverifiedSample) as err:
            w.sample_pre_dispatch(read_u32=bad_read,
                                  bridge_tick=lambda: 50,
                                  stage="idle_after",
                                  source_contract_reviewed=True)
        self.assertNotIn("91010000", str(err.exception))
        self.assertNotIn("PRIVATE", str(err.exception))

    def test_private_payload_must_not_be_published(self):
        mem, _ = fake_memory()
        out, _ = run(mem)
        self.assertIn("PRIVATE_DO_NOT_PUBLISH", out["kind"])
        self.assertIn("selected_record_pointer", out)
        self.assertIn("private_words", out)
        self.assertFalse(out["physical_motion_verified"])

    def test_wrong_source_return_type_fails(self):
        mem, p = fake_memory()
        mem[p["ball"]] = True
        with self.assertRaises(w.UnverifiedSample):
            run(mem)

    def test_other_approved_phases_have_no_control_effect(self):
        mem, _ = fake_memory()
        for stage in w.STAGES:
            with self.subTest(stage=stage):
                out, _ = run(mem, stage=stage)
                self.assertEqual(out["stage"], stage)
                self.assertFalse(out["physical_motion_verified"])

    def test_boundaries_reject_unmapped_or_unaligned(self):
        for x in (0x90000001, 0x94000000, 0x80000000):
            self.assertFalse(w.mapped(x))
        self.assertTrue(w.mapped(0x93FFFFF4, 12))
        self.assertFalse(w.mapped(0x93FFFFF8, 12))


if __name__ == "__main__":
    unittest.main()
