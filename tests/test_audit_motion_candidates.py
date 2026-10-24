"""No Dolphin interaction: unique-address and span-overlap audit tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.motion_candidates import audit_motion_report


def candidate(address, window="a", offset="+0x0", window_address=None,
              first=None, last=None, changed=10, within=8):
    return {
        "candidate_address": f"0x{address:X}",
        "window_address": f"0x{address:X}" if window_address is None else window_address,
        "offset_hex": offset, "window": window,
        "changed_steps": changed, "within_same_scene_changed_steps": within,
        "observed_samples": 50,
        "first_xyz": [1, 0, 0] if first is None else first,
        "last_xyz": [0, 1, 0] if last is None else last,
    }


def report(rows, reported=None, run="moving"):
    return {"schema_version": 1, "run_id": run,
            "position_candidates": {"candidate_count": len(rows) if reported is None else reported,
                                    "candidates": rows,
                                    "candidates_truncated": reported is not None and reported > len(rows)}}


class CandidateAuditTests(unittest.TestCase):
    def test_duplicates_overlaps_and_truncation_are_not_independent_balls(self):
        rows = [candidate(0x100, "ball"),
                candidate(0x100, "other"),
                candidate(0x104, "ball", "+0x4", "0x100"),
                candidate(0x120, "unrelated")]
        result = audit_motion_report(report(rows, reported=111))
        self.assertEqual(result["reported_candidate_count"], 111)
        self.assertEqual(result["published_vector_rows"], 4)
        self.assertEqual(result["unique_start_addresses_in_published_list"], 3)
        self.assertEqual(result["duplicate_rows_in_published_list"], 1)
        self.assertEqual(result["repeated_start_addresses"], 1)
        self.assertEqual(result["overlapping_span_groups_in_published_list"], 2)
        self.assertTrue(result["published_list_incomplete"])
        self.assertFalse(result["ball_position_verified"])
        self.assertFalse(result["score_verified"])
        self.assertEqual(result["overlap_groups"][0]["candidate_addresses"],
                         ["0x00000100", "0x00000104"])

    def test_unit_vector_hint_is_not_certification(self):
        rows = [candidate(0x100),
                candidate(0x200, first=[2, 0, 0], last=[2, 0, 0]),
                candidate(0x300, first=[0, 0, 0], last=[1, 0, 0])]
        result = audit_motion_report(report(rows))
        self.assertEqual(result["potential_unit_vector_start_addresses"], 1)
        self.assertFalse(result["ball_position_verified"])

    def test_conflicting_window_observations_flagged(self):
        rows = [candidate(0x100, "first", within=8),
                candidate(0x100, "second", within=9)]
        result = audit_motion_report(report(rows))
        self.assertTrue(result["aliases"][0]["alias_statistics_disagree"])
        self.assertEqual(result["aliases"][0]["within_same_scene_changed_steps_max"], 9)

    def test_offset_mismatch_reports_untrusted_locator(self):
        result = audit_motion_report(report([candidate(0x104, window_address="0x100", offset="+0x8")]))
        self.assertEqual(result["offset_mismatch_addresses"], ["0x00000104"])

    def test_baseline_comparison_is_only_for_published_subset(self):
        baseline = report([candidate(0x100)], run="idle")
        latest = report([candidate(0x100), candidate(0x200)], reported=50)
        result = audit_motion_report(latest, baseline)
        comp = result["published_subset_comparison"]
        self.assertEqual(comp["shared_start_addresses"], 1)
        self.assertEqual(comp["only_in_current_published_subset"], 1)
        self.assertIn("truncated ranked lists", comp["warning"])

    def test_validation_rejects_wrong_schema_and_inconsistent_count(self):
        with self.assertRaises(ValueError):
            audit_motion_report({"schema_version": 2, "position_candidates": {"candidate_count": 0, "candidates": []}})
        with self.assertRaises(ValueError):
            audit_motion_report(report([candidate(0x100)], reported=0))
        with self.assertRaises(ValueError):
            audit_motion_report(report([candidate(0x100, offset="bad")]))

    def test_does_not_modify_report(self):
        value = report([candidate(0x100)], reported=2)
        prior = json.dumps(value, sort_keys=True)
        audit_motion_report(value)
        self.assertEqual(json.dumps(value, sort_keys=True), prior)

    def test_offline_cli_isolated_no_existing_file_overwrite(self):
        with TemporaryDirectory() as d:
            folder = Path(d)
            inp = folder / "report.json"
            out = folder / "audit.json"
            inp.write_text(json.dumps(report([candidate(0x100)])))
            script = ROOT / "scripts" / "audit_motion_candidates.py"
            cmd = [sys.executable, "-I", str(script), "--input", str(inp), "--out", str(out)]
            first = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue(out.is_file())
            result = json.loads(out.read_text())
            self.assertEqual(result["unique_start_addresses_in_published_list"], 1)
            second = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(json.loads(out.read_text()), result)


if __name__ == "__main__":
    unittest.main()
