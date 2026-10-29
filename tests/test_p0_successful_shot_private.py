"""Synthetic offline tests; no actual game capture, Dolphin or private RAM."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_p0_successful_shot_private.py"
SPEC = importlib.util.spec_from_file_location("audit_p0_successful_shot_private", SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
BASE = 0x90001000


def fixture():
    rows = []
    for phase in ("pre",)*3 + ("post",)*2 + ("settled",)*3:
        raw = bytearray(0xA8)
        if phase != "pre":
            raw[0x57] = 1
        rows.append({
            "phase": phase, "game_id": "RSPE01", "disc_revision": 1,
            "game_mode_raw": 4, "frame_start": 100, "frame_end": 122,
            "windows": {"golf_field": {"address": f"0x{BASE:08X}", "bytes_hex": raw.hex()}}
        })
    summary = {
        "candidate_ranking": {
            "pre_samples": 3, "post_samples": 2, "settled_samples": 3,
            "sample_count": 8, "all_phase_stable_change_count": 1,
            "candidates_truncated": False,
            "candidates": [{
                "address": f"0x{BASE + 0x54:08X}", "windows": ["golf_field"],
                "before": {"u32": 0}, "settled": {"u32": 1},
                "post_samples_differing_from_pre": 2,
                "post_distinct_values": 1,
                "matches_displayed_numeric_label_as": ["u32"]
            }]
        },
        "human_observation": {"contact_human": "yes", "finished_on_green_human": "no"}
    }
    return summary, rows


class PositiveHitAuditTests(unittest.TestCase):
    def test_redaction_and_source_relative_offsets(self):
        summary, rows = fixture()
        report = m.audit(summary, rows)
        self.assertEqual(report["stored_persistent_candidate_count"], 1)
        candidate = report["candidates"][0]
        self.assertEqual(candidate["candidate_id"], "C01")
        self.assertEqual(candidate["source_relative_locations"][0]["relative_word_offset"], "+0x054")
        self.assertEqual(candidate["source_relative_locations"][0]["source_field_hint"], "cup_reference_not_distance")
        self.assertNotIn(f"0x{BASE + 0x54:08X}", str(report))
        self.assertNotIn('"u32":', str(report))
        self.assertFalse(report["model_training_allowed"])

    def test_reject_summary_count(self):
        summary, rows = fixture()
        summary["candidate_ranking"]["sample_count"] = 9
        with self.assertRaises(ValueError):
            m.audit(summary, rows)

    def test_reject_phase_order(self):
        summary, rows = fixture()
        rows[0]["phase"] = "settled"
        with self.assertRaises(ValueError):
            m.audit(summary, rows)

    def test_reject_unknown_phase(self):
        summary, rows = fixture()
        rows[0]["phase"] = "flight"
        with self.assertRaises(ValueError):
            m.audit(summary, rows)

    def test_reject_window_relocation(self):
        summary, rows = fixture()
        rows[-1]["windows"]["golf_field"]["address"] = f"0x{BASE + 4:08X}"
        with self.assertRaises(ValueError):
            m.audit(summary, rows)

    def test_reject_wrong_mode(self):
        summary, rows = fixture()
        rows[0]["game_mode_raw"] = 3
        with self.assertRaises(ValueError):
            m.audit(summary, rows)

    def test_reject_unknown_window(self):
        summary, rows = fixture()
        summary["candidate_ranking"]["candidates"][0]["windows"] = ["arbitrary_heap"]
        with self.assertRaises(ValueError):
            m.audit(summary, rows)

    def test_pointer_shape_is_not_promotion(self):
        summary, rows = fixture()
        summary["candidate_ranking"]["candidates"][0]["settled"]["u32"] = 0x90123400
        for row in rows:
            if row["phase"] != "pre":
                raw = bytearray.fromhex(row["windows"]["golf_field"]["bytes_hex"])
                raw[0x54:0x58] = (0x90123400).to_bytes(4, "big")
                row["windows"]["golf_field"]["bytes_hex"] = raw.hex()
        report = m.audit(summary, rows)
        self.assertTrue(report["candidates"][0]["before_or_after_pointer_shaped"])
        self.assertFalse(report["candidates"][0]["training_eligible"])

    def test_reject_corrupt_raw_vs_summary(self):
        summary, rows = fixture()
        raw = bytearray.fromhex(rows[-1]["windows"]["golf_field"]["bytes_hex"])
        raw[0x57] = 7
        rows[-1]["windows"]["golf_field"]["bytes_hex"] = raw.hex()
        with self.assertRaises(ValueError):
            m.audit(summary, rows)

    def test_no_absolute_guest_address_output(self):
        summary, rows = fixture()
        self.assertNotIn("0x90001054", str(m.audit(summary, rows)))

    def test_reject_truncated_ranking(self):
        summary, rows = fixture()
        summary["candidate_ranking"]["candidates_truncated"] = True
        with self.assertRaises(ValueError):
            m.audit(summary, rows)

    def test_reject_missing_window_phase(self):
        summary, rows = fixture()
        rows[-1]["windows"] = {}
        with self.assertRaises(ValueError):
            m.audit(summary, rows)


if __name__ == "__main__":
    unittest.main()
