"""Synthetic adversarial tests only: no Dolphin, private RAM, networking or write to repo."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_p0_shot_transients_private.py"
SPEC = importlib.util.spec_from_file_location("shot_transients", SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

BASES = {"golf_config": 0x90001000, "golf_field": 0x90008000,
         "sports_sequence": 0x90009000,
         "minimap_player_effect": 0x90010000,
         "minimap_shot_line_effect": 0x90010090,
         "minimap_ball_effect": 0x90010120}


def fixture(*, overlap=True):
    rows = []
    phases = ["pre"]*3 + ["post"]*2 + ["settled"]*3
    for index, phase in enumerate(phases):
        memories = {}
        for name, size in m.WINDOWS.items():
            if name.startswith("minimap_") and not overlap:
                continue
            memories[name] = bytearray(size)
        # An exact address can be represented by overlapping effect windows.
        absolute_values = {}
        if phase == "post":
            absolute_values[BASES["golf_config"]+0x100] = 0x3F800000
            absolute_values[BASES["golf_field"]+0x80] = 0x40000000
            absolute_values[BASES["minimap_player_effect"]+0x108] = 0x40400000
            # In one POST only: not a robust both-POST candidate.
            if index == 3:
                absolute_values[BASES["sports_sequence"]+0x40] = 0x11111111
        # The existing S002 ranker detects this PERSISTENT, not transient.
        if phase != "pre":
            absolute_values[BASES["golf_config"]+0x104] = 1
        windows = {}
        for name, raw in memories.items():
            base = BASES[name]
            for addr, bits in absolute_values.items():
                if base <= addr <= base + len(raw) - 4:
                    struct.pack_into(">I", raw, addr-base, bits)
            windows[name] = {"address": f"0x{base:08X}", "bytes_hex": raw.hex()}
        rows.append({
            "schema_version": 1,
            "source": "Felk-read-only-US-Rev1-unverified-golf-windows",
            "phase": phase, "game_id": "RSPE01",
            "disc_revision": 1, "game_mode_raw": 4,
            "frame_start": 200+index*40, "frame_end": 207+index*40,
            "bytes_read": sum(len(raw) for raw in memories.values()),
            "windows": windows,
        })
    summary = {
        "study_id": "S002-HG-OUTCOME-TRANSITION-EXPLORATORY",
        "raw_data_created": True,
        "known_good_swing_request": {
            "generated_trace_frames": 89, "a_lead_requested_frames": 45,
            "a_lead_observed_frame_delta": 45,
            "a_button_only_prime_requests": 1,
        },
        "human_observation": {"contact_human": "yes"},
        "candidate_ranking": {
            "pre_samples": 3, "post_samples": 2, "settled_samples": 3,
            "sample_count": 8, "all_phase_stable_change_count": 1,
            "candidates_truncated": False,
        }
    }
    return summary, rows


class TransientTests(unittest.TestCase):
    def test_finds_transients_and_crosschecks_existing_persistent(self):
        summ, rows = fixture()
        report = m.audit(summ, rows)
        self.assertEqual(report["persistent_unique_word_count_crosscheck"], 1)
        self.assertEqual(report["transient_unique_word_count"], 4)
        self.assertEqual(report["post_changed_in_only_subset_count"], 1)
        self.assertEqual(report["max_snapshot_frame_span"], 7)
        self.assertFalse(report["training_allowed"])

    def test_same_address_overlap_is_one_candidate(self):
        summ, rows = fixture()
        report = m.audit(summ, rows)
        target = [x for x in report["candidates"]
                  if any(loc["window"] == "minimap_player_effect" and
                         loc["offset"] == "+0x108"
                         for loc in x["source_relative_locations"])]
        self.assertEqual(len(target), 1)
        self.assertTrue(target[0]["visual_effect_only"])
        self.assertEqual({x["window"] for x in target[0]["source_relative_locations"]},
                         {"minimap_player_effect", "minimap_shot_line_effect"})

    def test_non_effect_sources_rank_before_effects(self):
        summ, rows = fixture()
        report = m.audit(summ, rows)
        locations = [x["source_relative_locations"][0]["window"]
                     for x in report["candidates"]]
        self.assertEqual(locations[:3], ["golf_config", "golf_field", "sports_sequence"])
        self.assertEqual(locations[3], "minimap_player_effect")

    def test_only_one_post_is_marked_weak(self):
        summ, rows = fixture()
        candidates = m.audit(summ, rows)["candidates"]
        one = [c for c in candidates if c["source_relative_locations"][0]["window"]
               == "sports_sequence"][0]
        self.assertEqual(one["post_differing_count"], 1)
        self.assertIn("some_POST", one["type"])

    def test_private_values_addresses_and_paths_not_in_report(self):
        summ, rows = fixture()
        report = m.audit(summ, rows)
        text = json.dumps(report)
        for prohibited in ("0x90001100", "0x900100", "0x3F800000",
                           "0x40400000", "bytes_hex", "D:\\Projects",
                           "human_observation", "capture.raw"):
            self.assertNotIn(prohibited, text)
        self.assertFalse(report["private_guest_addresses_present"])

    def test_changed_pre_must_not_be_promoted(self):
        summ, rows = fixture()
        raw = bytearray.fromhex(rows[1]["windows"]["golf_config"]["bytes_hex"])
        struct.pack_into(">I", raw, 0x100, 0x50000000)
        rows[1]["windows"]["golf_config"]["bytes_hex"] = raw.hex()
        report = m.audit(summ, rows)
        self.assertEqual(report["transient_unique_word_count"], 3)
        self.assertGreater(report["unstable_PRE_absolute_word_count_excluded"], 0)

    def test_changed_settled_must_not_be_promoted(self):
        summ, rows = fixture()
        raw = bytearray.fromhex(rows[-1]["windows"]["golf_field"]["bytes_hex"])
        struct.pack_into(">I", raw, 0x80, 0xABCD0000)
        rows[-1]["windows"]["golf_field"]["bytes_hex"] = raw.hex()
        report = m.audit(summ, rows)
        self.assertEqual(report["transient_unique_word_count"], 3)
        self.assertGreater(report["unstable_SETTLED_absolute_word_count_excluded"], 0)

    def test_wrong_human_or_trace_must_fail_closed(self):
        summ, rows = fixture()
        summ["human_observation"]["contact_human"] = "unknown"
        with self.assertRaises(ValueError):
            m.audit(summ, rows)
        summ, rows = fixture()
        summ["known_good_swing_request"]["a_lead_requested_frames"] = 0
        with self.assertRaises(ValueError):
            m.audit(summ, rows)

    def test_source_collector_and_guest_frame_order_fail_closed(self):
        summ, rows = fixture()
        rows[3]["source"] = "unknown-unverified-dump"
        with self.assertRaises(ValueError):
            m.audit(summ, rows)
        summ, rows = fixture()
        rows[4]["frame_start"] = 100
        with self.assertRaises(ValueError):
            m.audit(summ, rows)

    def test_wrong_game_or_phase_must_fail_closed(self):
        summ, rows = fixture()
        rows[3]["game_mode_raw"] = 3
        with self.assertRaises(ValueError):
            m.audit(summ, rows)
        summ, rows = fixture()
        rows[2]["phase"] = "settled"
        with self.assertRaises(ValueError):
            m.audit(summ, rows)

    def test_moved_window_or_truncation_fails_closed(self):
        summ, rows = fixture()
        rows[7]["windows"]["golf_config"]["address"] = "0x90001004"
        with self.assertRaises(ValueError):
            m.audit(summ, rows)
        summ, rows = fixture()
        rows[7]["windows"]["golf_config"]["bytes_hex"] = "00"
        with self.assertRaises(ValueError):
            m.audit(summ, rows)

    def test_ranker_count_tampering_blocks_wrong_shot(self):
        summ, rows = fixture()
        summ["candidate_ranking"]["all_phase_stable_change_count"] = 8
        with self.assertRaises(ValueError):
            m.audit(summ, rows)

    def test_duplicate_nonatomic_alias_is_excluded(self):
        summ, rows = fixture()
        # Same absolute address in two overlapping effects, but one
        # non-atomic window contradicts the other during one POST.
        data = bytearray.fromhex(rows[3]["windows"]["minimap_shot_line_effect"]["bytes_hex"])
        struct.pack_into(">I", data, 0x78, 0xDEADBEEF)
        rows[3]["windows"]["minimap_shot_line_effect"]["bytes_hex"] = data.hex()
        report = m.audit(summ, rows)
        self.assertEqual(report["transient_unique_word_count"], 3)

    def test_output_exclusive_private_path_and_input_pair(self):
        summ, rows = fixture()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = "outcome-20261028T033948Z-5cd47f00"
            summary = root / (name + m.SUMMARY_SUFFIX)
            raw = root / (name + m.RAW_SUFFIX)
            out = root / (name + "-POST-TRANSIENTS-SANITIZED.json")
            summary.write_text(json.dumps(summ), encoding="utf-8")
            raw.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
            with patch.object(m, "PRIVATE_ROOT", root):
                self.assertEqual(m.main(["--summary", str(summary), "--raw",
                                         str(raw), "--output", str(out)]), 0)
                self.assertTrue(out.exists())
                self.assertEqual(m.main(["--summary", str(summary), "--raw",
                                         str(raw), "--output", str(out)]), 2)
                self.assertEqual(len(list(root.glob("*TRANSIENTS*"))), 1)

    def test_no_input_symlink_and_cross_pair(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "same-candidates.json"
            source.write_text("{}", encoding="utf-8")
            linked = root / "linked-candidates.json"
            try:
                linked.symlink_to(source)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink privilege unavailable")
            with patch.object(m, "PRIVATE_ROOT", root):
                with self.assertRaises(ValueError):
                    m._private_file(str(linked), m.SUMMARY_SUFFIX)


if __name__ == "__main__":
    unittest.main()
