"""Synthetic checks for the 5-word unsettled SETTLED follow-up. No Dolphin/RAM."""
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
TESTS = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location("test_p0_shot_transients_private", TESTS / "test_p0_shot_transients_private.py")
base_tests = importlib.util.module_from_spec(s)
s.loader.exec_module(base_tests)
m_spec = importlib.util.spec_from_file_location("p0_settled_variability", SCRIPTS / "audit_p0_settled_variability_private.py")
m = importlib.util.module_from_spec(m_spec)
m_spec.loader.exec_module(m)


def fixture():
    summary, rows = base_tests.fixture()
    offsets = [
        ("golf_config", 0x108),
        ("golf_config", 0x10C),
        ("golf_field", 0x84),
        ("sports_sequence", 0x44),
        ("minimap_player_effect", 0x110),
    ]
    # Update all overlapping effect windows by absolute address.
    for i, row in enumerate(rows):
        for name, offset in offsets:
            if row["phase"] != "settled":
                continue
            absolute = base_tests.BASES[name] + offset
            bits = (0x3F000000, 0x40000000, 0x40400000)[i-5]
            for window, record in row["windows"].items():
                start = base_tests.BASES[window]
                size = m.p0.WINDOWS[window]
                if start <= absolute <= start + size - 4:
                    raw = bytearray.fromhex(record["bytes_hex"])
                    struct.pack_into(">I", raw, absolute - start, bits)
                    record["bytes_hex"] = raw.hex()
    return summary, rows


class SettledVariabilityTests(unittest.TestCase):
    def test_five_unstable_settled_candidates_and_prior_rankers(self):
        summary, rows = fixture()
        result = m.audit_settled(summary, rows)
        self.assertEqual(result["unstable_settled_unique_word_count"], 5)
        self.assertEqual(result["non_effect_count"], 4)
        self.assertEqual(result["effect_only_count"], 1)
        self.assertEqual(result["original_persistent_crosscheck"], 1)
        self.assertEqual(result["original_transients_crosscheck"], 4)
        self.assertFalse(result["training_allowed"])

    def test_effect_alias_deduped_to_one_word(self):
        summary, rows = fixture()
        result = m.audit_settled(summary, rows)
        effect = [c for c in result["candidates"] if c["effect_only_confound"]]
        self.assertEqual(len(effect), 1)
        self.assertEqual(len(effect[0]["source_relative_locations"]), 2)
        self.assertEqual({e["window"] for e in effect[0]["source_relative_locations"]},
                         {"minimap_player_effect", "minimap_shot_line_effect"})

    def test_only_relative_addresses_and_safe_flags_are_emitted(self):
        summary, rows = fixture()
        result = m.audit_settled(summary, rows)
        text = json.dumps(result)
        for private in ("0x90001108", "0x900100", "bytes_hex", "0x3F000000",
                        "0x40400000", "D:\\Projects", "raw_path"):
            self.assertNotIn(private, text)
        self.assertIn("+0x108", text)
        self.assertFalse(result["raw_word_values_present"])
        self.assertFalse(result["private_guest_addresses_present"])

    def test_no_unstable_word_yields_zero(self):
        summary, rows = base_tests.fixture()
        result = m.audit_settled(summary, rows)
        self.assertEqual(result["unstable_settled_unique_word_count"], 0)

    def test_short_stale_or_corrupt_capture_refused(self):
        summary, rows = fixture()
        rows[4]["frame_start"] = 10
        with self.assertRaises(ValueError):
            m.audit_settled(summary, rows)
        summary, rows = fixture()
        summary["candidate_ranking"]["all_phase_stable_change_count"] = 999
        with self.assertRaises(ValueError):
            m.audit_settled(summary, rows)

    def test_unstable_pre_is_not_included(self):
        summary, rows = fixture()
        data = bytearray.fromhex(rows[0]["windows"]["golf_config"]["bytes_hex"])
        struct.pack_into(">I", data, 0x108, 0xFF000000)
        rows[0]["windows"]["golf_config"]["bytes_hex"] = data.hex()
        result = m.audit_settled(summary, rows)
        self.assertEqual(result["unstable_settled_unique_word_count"], 4)

    def test_exclusive_private_file_and_paired_id(self):
        summary, rows = fixture()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            stem = "outcome-20261028T033948Z-5cd47f00"
            p_summary = folder / (stem + m.p0.SUMMARY_SUFFIX)
            p_raw = folder / (stem + m.p0.RAW_SUFFIX)
            target = folder / (stem + m.REPORT_SUFFIX)
            p_summary.write_text(json.dumps(summary), encoding="utf-8")
            p_raw.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            with patch.object(m.p0, "PRIVATE_ROOT", folder):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(m.main(["--summary", str(p_summary),
                                             "--raw", str(p_raw), "--output", str(target)]), 0)
                self.assertTrue(target.exists())
                self.assertEqual(json.loads(target.read_text())["unstable_settled_unique_word_count"], 5)
                with redirect_stderr(io.StringIO()):
                    self.assertEqual(m.main(["--summary", str(p_summary),
                                             "--raw", str(p_raw), "--output", str(target)]), 2)

    def test_private_outside_dest_refused(self):
        summary, rows = fixture()
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as other:
            folder = Path(temp)
            stem = "outcome-20261028T033948Z-5cd47f00"
            p_summary = folder / (stem + m.p0.SUMMARY_SUFFIX)
            p_raw = folder / (stem + m.p0.RAW_SUFFIX)
            p_summary.write_text(json.dumps(summary), encoding="utf-8")
            p_raw.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            with patch.object(m.p0, "PRIVATE_ROOT", folder), redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(["--summary", str(p_summary),
                                         "--raw", str(p_raw),
                                         "--output", str(Path(other) / (stem+m.REPORT_SUFFIX))]), 2)


if __name__ == "__main__":
    unittest.main()
