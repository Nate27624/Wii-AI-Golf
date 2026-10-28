"""Synthetic tests for field +0x9C, 0x90 overlap, and five tail words.

Fixture is generated in memory from the already tested settled study.
Never reads user captures, starts Dolphin, performs network calls or writes Git.
"""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
TEST = BASE / "tests" / "test_p0_settled_variability_private.py"
S = importlib.util.spec_from_file_location("settled_test_fixture", TEST)
fixture_module = importlib.util.module_from_spec(S)
S.loader.exec_module(fixture_module)

P = BASE / "scripts" / "audit_p0_effect_tail_ownership_private.py"
S = importlib.util.spec_from_file_location("effect_tail_ownership", P)
m = importlib.util.module_from_spec(S)
S.loader.exec_module(m)


def _write(row, addr: int, value: int):
    for window, item in row["windows"].items():
        base = int(item["address"], 16)
        length = len(item["bytes_hex"]) // 2
        if base <= addr <= base + length - 4:
            raw = bytearray.fromhex(item["bytes_hex"])
            struct.pack_into(">I", raw, addr - base, value)
            item["bytes_hex"] = raw.hex()


def positive_shot():
    summary, rows = fixture_module.fixture()
    config = fixture_module.base_tests.BASES["golf_config"]
    field = fixture_module.base_tests.BASES["golf_field"]
    seq = fixture_module.base_tests.BASES["sports_sequence"]
    player = fixture_module.base_tests.BASES["minimap_player_effect"]
    line = fixture_module.base_tests.BASES["minimap_shot_line_effect"]
    ball = fixture_module.base_tests.BASES["minimap_ball_effect"]
    for row in rows:
        # The collector's golf_field pointers must reference the actual
        # recorded effect-window starts, not merely matched labels.
        for off, base in ((0x94, player), (0x98, line), (0x9C, ball)):
            _write(row, field + off, base)
        # Remove fixture-only 4 transient candidates and 1 persistent.
        for addr in (config + 0x100, config + 0x104,
                     field + 0x80, seq + 0x40, player + 0x108):
            _write(row, addr, 0)
        if row["phase"] != "pre":
            # Eight actual persistent *positions* as four adjacent pairs;
            # fixture values are invented synthetic integers, not RAM evidence.
            for slot in range(4):
                for j in (0, 4):
                    _write(row, player + 0x78 + slot * 0x90 + j,
                           (0x12340000 + 16 * slot + j))
    summary["candidate_ranking"]["all_phase_stable_change_count"] = 8
    return summary, rows


class TailOwnershipTests(unittest.TestCase):
    def test_original_0_8_5_cohort_and_verified_pointer_starts(self):
        summary, rows = positive_shot()
        original = m.prior.audit(summary, rows)
        variability = m.settled.audit_settled(summary, rows)
        self.assertEqual(original["transient_unique_word_count"], 0)
        self.assertEqual(original["persistent_unique_word_count_crosscheck"], 8)
        self.assertEqual(variability["unstable_settled_unique_word_count"], 5)
        result = m.audit(summary, rows)
        self.assertTrue(result["pointer_word_matches_window_start_in_all_samples"])
        self.assertTrue(result["pointer_bases_fixed_across_all_samples"])
        self.assertEqual(result["effect_pointer_start_spacing_bytes"], 0x90)
        self.assertEqual(result["collector_per_window_read_bytes"], 0x200)
        self.assertFalse(result["effect_allocation_ownership_verified"])

    def test_last_five_covered_by_ball_named_sample_only(self):
        result = m.audit(*positive_shot())
        self.assertEqual(result["last_five_ball_window_relative_offsets"],
                         ["+0x1EC", "+0x1F0", "+0x1F4", "+0x1F8", "+0x1FC"])
        self.assertEqual(result["tail_corresponds_to_hypothetical_stride_index"], 5)
        self.assertEqual(result["tail_relative_positions_in_hypothetical_stride"],
                         ["+0x3C", "+0x40", "+0x44", "+0x48", "+0x4C"])
        tail = result["six_hypothetical_slot_profiles"][5]
        self.assertEqual(tail["word_coverage_by_number_of_source_windows"],
                         {"one_window": 5, "two_windows": 0, "three_windows": 0})
        self.assertEqual(tail["words_with_unstable_SETTLED"], 5)

    def test_repeated_slot_coverage_changes_across_windows(self):
        profiles = m.audit(*positive_shot())["six_hypothetical_slot_profiles"]
        self.assertEqual(len(profiles), 6)
        self.assertEqual(profiles[0]["word_coverage_by_number_of_source_windows"]["one_window"], 5)
        self.assertEqual(profiles[2]["word_coverage_by_number_of_source_windows"]["three_windows"], 5)
        self.assertEqual(profiles[4]["word_coverage_by_number_of_source_windows"]["two_windows"], 5)
        self.assertFalse(m.audit(*positive_shot())["repeated_effect_instance_count_verified"])

    def test_falsified_pointer_mapping_refused(self):
        summary, rows = positive_shot()
        field = fixture_module.base_tests.BASES["golf_field"]
        _write(rows[0], field + 0x9C, 0)
        with self.assertRaisesRegex(ValueError, "pointer"):
            m.audit(summary, rows)

    def test_malformed_stride_or_alias_is_refused(self):
        summary, rows = positive_shot()
        rows[1]["windows"]["minimap_ball_effect"]["address"] = "0x90010124"
        with self.assertRaises(ValueError):
            m.audit(summary, rows)
        summary, rows = positive_shot()
        # Mutating only an overlapping *single window* is a contradiction,
        # not a new physics vector.
        raw = bytearray.fromhex(rows[4]["windows"]["minimap_shot_line_effect"]["bytes_hex"])
        struct.pack_into(">I", raw, 0x108, 0xAABBCCDD)
        rows[4]["windows"]["minimap_shot_line_effect"]["bytes_hex"] = raw.hex()
        with self.assertRaises(ValueError):
            m.audit(summary, rows)

    def test_private_information_is_not_in_report(self):
        text = json.dumps(m.audit(*positive_shot()))
        for forbidden in ("0x90010000", "0x90010120", "0x12340000",
                          "bytes_hex", "D:\\Projects", "raw_path", "RAW-PRIVATE"):
            self.assertNotIn(forbidden, text)
        result = m.audit(*positive_shot())
        for key in ("ball_world_xyz_verified", "ball_velocity_verified",
                    "swing_power_verified", "training_allowed",
                    "private_guest_addresses_present", "raw_word_values_present",
                    "automatic_github_publication"):
            self.assertFalse(result[key])

    def test_repeated_run_verifies_existing_file_without_overwriting(self):
        summary, rows = positive_shot()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stem = "outcome-20261028T033948Z-5cd47f00"
            a = root / (stem + m.prior.SUMMARY_SUFFIX)
            b = root / (stem + m.prior.RAW_SUFFIX)
            c = root / (stem + m.OUTPUT_SUFFIX)
            a.write_text(json.dumps(summary), encoding="utf-8")
            b.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
            with patch.object(m.prior, "PRIVATE_ROOT", root), patch.object(m.settled.prior, "PRIVATE_ROOT", root):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(m.main(["--summary", str(a), "--raw", str(b), "--output", str(c)]), 0)
                original = c.read_bytes()
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(m.main(["--summary", str(a), "--raw", str(b), "--output", str(c)]), 0)
                self.assertIn("EXISTING_RESULT_VERIFIED", stdout.getvalue())
                self.assertEqual(c.read_bytes(), original)

    def test_wrong_existing_result_is_refused_not_overwritten(self):
        summary, rows = positive_shot()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stem = "outcome-20261028T033948Z-5cd47f00"
            a = root / (stem + m.prior.SUMMARY_SUFFIX)
            b = root / (stem + m.prior.RAW_SUFFIX)
            c = root / (stem + m.OUTPUT_SUFFIX)
            a.write_text(json.dumps(summary), encoding="utf-8")
            b.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
            c.write_text('{"not": "the real report"}', encoding="utf-8")
            with patch.object(m.prior, "PRIVATE_ROOT", root), redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(["--summary", str(a), "--raw", str(b), "--output", str(c)]), 2)
            self.assertEqual(c.read_text(encoding="utf-8"), '{"not": "the real report"}')


if __name__ == "__main__":
    unittest.main()
