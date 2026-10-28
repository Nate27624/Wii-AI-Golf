"""Only synthetic tests. No Dolphin, native RAM, network or user files."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "effect_lifecycle", ROOT / "scripts" / "audit_effect_handle_lifecycle_private.py"
)
m = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(m)


def fixture(*, unstable_post=False, alias_corrupt=False):
    base = 0x80010000
    rows = []
    phases = ["pre"]*3 + ["post"]*2 + ["settled"]*3
    for idx, phase in enumerate(phases):
        data = bytearray(0x320)
        step = {"pre": 0, "post": 1, "settled": 2}[phase]
        for slot, (id_off, ptr_off) in enumerate(m.SLOTS):
            value = (10, 20, 30)[step] + slot
            if unstable_post and phase == "post" and idx == 4:
                value += 2
            ptr = 0x80020000 + 0x1000*step + slot*0x100
            struct.pack_into(">II", data, id_off, value, ptr)
        windows = {}
        for name, shift in ((m.WINDOWS[0], 0), (m.WINDOWS[1], 0x90), (m.WINDOWS[2], 0x120)):
            raw = bytearray(data[shift:shift+0x200])
            if alias_corrupt and name == m.WINDOWS[1] and idx == 3:
                raw[0x078] ^= 0x01
            windows[name] = {"address": f"0x{base+shift:08X}", "bytes_hex": raw.hex()}
        rows.append({
            "schema_version": 1,
            "source": m.SOURCE,
            "game_id": "RSPE01",
            "disc_revision": 1,
            "game_mode_raw": 4,
            "frame_start": idx*100,
            "frame_end": idx*100 + 2,
            "phase": phase,
            "windows": windows,
        })
    summary = {
        "study_id": "S002-HG-OUTCOME-TRANSITION-EXPLORATORY",
        "raw_data_created": True,
        "known_good_swing_request": {
            "a_lead_requested_frames": 45,
            "a_lead_observed_frame_delta": 46,
        },
        "swing_dispatch": {"state": "complete", "applied_frames": 89, "total_frames": 89},
        "human_observation": {
            "contact_human": "yes",
            "game_distance_verified_by_memory": False,
            "displayed_power_verified_by_memory": False,
        },
        "candidate_ranking": {
            "candidates_truncated": False,
            "all_phase_stable_change_count": 8,
            "candidates": [{"address": f"0x{base+offset:08X}"}
                           for pair in m.SLOTS for offset in pair],
        },
    }
    return rows, summary


class ExistingShotHandleLifecycleTests(unittest.TestCase):
    def test_source_handle_pairs_and_phase_changes(self):
        rows, summary = fixture()
        result = m.audit(rows, summary)
        self.assertEqual(len(result["pair_patterns"]), 4)
        self.assertEqual(result["phase_counts"], {"pre": 3, "post": 2, "settled": 3})
        self.assertTrue(result["source_windows_spaced_0x90_in_all_phases"])
        self.assertTrue(result["frame_reads_non_atomic"])
        for i, p in enumerate(result["pair_patterns"]):
            self.assertEqual(p["slot_index_hypothesis"], i)
            self.assertTrue(p["pre_pair_stable"])
            self.assertTrue(p["post_pair_stable"])
            self.assertTrue(p["settled_pair_stable"])
            self.assertTrue(p["both_changed_in_each_post"])
            self.assertTrue(p["handle_layout_plausible_each_sample"])
            self.assertFalse(p["pointer_target_identity_verified"])
        self.assertFalse(result["ball_xyz_verified"])
        self.assertFalse(result["ball_velocity_verified"])
        self.assertFalse(result["club_power_verified"])
        self.assertFalse(result["approved_for_training"])
        emitted = json.dumps(result)
        self.assertNotIn("0x800100", emitted)
        self.assertNotIn("0x800200", emitted)
        self.assertNotIn('"bytes_hex"', emitted)
        self.assertNotIn('"before"', emitted)

    def test_stable_post_is_independent_of_post_changes(self):
        rows, summary = fixture(unstable_post=True)
        result = m.audit(rows, summary)
        self.assertFalse(result["pair_patterns"][0]["post_pair_stable"])
        self.assertTrue(result["pair_patterns"][0]["both_changed_in_each_post"])

    def test_mismatched_overlapping_window_fails(self):
        rows, summary = fixture(alias_corrupt=True)
        with self.assertRaisesRegex(ValueError, "contradictory"):
            m.audit(rows, summary)

    def test_candidate_address_swap_fails(self):
        rows, summary = fixture()
        summary["candidate_ranking"]["candidates"][-1]["address"] = "0x80090000"
        with self.assertRaisesRegex(ValueError, "not the four source"):
            m.audit(rows, summary)

    def test_relocated_owners_fail(self):
        rows, summary = fixture()
        for name in m.WINDOWS:
            v = int(rows[4]["windows"][name]["address"], 16)
            rows[4]["windows"][name]["address"] = f"0x{v+0x1000:08X}"
        with self.assertRaisesRegex(ValueError, "relocated"):
            m.audit(rows, summary)

    def test_nonmatching_stride_fails(self):
        rows, summary = fixture()
        rows[5]["windows"][m.WINDOWS[1]]["address"] = "0x80010094"
        with self.assertRaisesRegex(ValueError, "alignment"):
            m.audit(rows, summary)

    def test_phases_mode_and_source_fail_closed(self):
        rows, summary = fixture()
        rows[4]["phase"] = "pre"
        with self.assertRaisesRegex(ValueError, "ordered"):
            m.audit(rows, summary)
        rows, summary = fixture()
        rows[0]["game_mode_raw"] = 3
        with self.assertRaisesRegex(ValueError, "revision/mode"):
            m.audit(rows, summary)
        rows, summary = fixture()
        rows[0]["source"] = "fabricated"
        with self.assertRaisesRegex(ValueError, "source"):
            m.audit(rows, summary)

    def test_evidence_and_trace_gates(self):
        rows, summary = fixture()
        summary["human_observation"]["contact_human"] = "no"
        with self.assertRaisesRegex(ValueError, "human-confirmed"):
            m.audit(rows, summary)
        rows, summary = fixture()
        summary["known_good_swing_request"]["a_lead_observed_frame_delta"] = 0
        with self.assertRaisesRegex(ValueError, "frozen"):
            m.audit(rows, summary)
        rows, summary = fixture()
        summary["swing_dispatch"]["applied_frames"] = 88
        with self.assertRaisesRegex(ValueError, "frozen"):
            m.audit(rows, summary)

    def test_invalid_bounds_and_bytes(self):
        rows, summary = fixture()
        rows[0]["windows"][m.WINDOWS[0]]["bytes_hex"] = "GG"*0x200
        with self.assertRaisesRegex(ValueError, "bytes"):
            m.audit(rows, summary)
        rows, summary = fixture()
        rows[2]["frame_end"] = rows[2]["frame_start"]-1
        with self.assertRaisesRegex(ValueError, "frame bracket"):
            m.audit(rows, summary)

    def test_run_id_and_guest_memory_address_guards(self):
        self.assertIsNone(m.RUN_ID.fullmatch("../escape"))
        self.assertIsNotNone(m.RUN_ID.fullmatch("outcome-20261028T033948Z-5cd47f00"))
        self.assertFalse(m._ram_range(0x81800000))
        self.assertTrue(m._ram_range(0x90000000))


if __name__ == "__main__":
    unittest.main()
