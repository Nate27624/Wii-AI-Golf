"""Private-capture null-control experiment: entirely synthetic fixtures."""
import importlib.util
import json
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "golfer_null_controls", ROOT / "scripts" / "audit_golfer_null_controls.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def rows_for(*, counts=(6, 8, 6), clock=True):
    rows = []
    i = 0
    for stage, count in enumerate(counts):
        for j in range(count):
            bits = (400 + 15 * i) if clock else (
                200 + 15 * j if stage == 1 else 50)
            raw = bytearray(0x100)
            struct.pack_into(">I", raw, 0x74, bits)
            rows.append({
                "stage": stage, "phase": "aim_only" if stage == 1 else "idle",
                "frame_start": 1000 + 15 * i, "frame_end": 1002 + 15 * i,
                "bytes_hex": raw.hex(),
                "runtime_scene_address": "0x80140000",
                "runtime_golf_main_address": "0x80160000",
                # Private addresses/unknown fields may be present and must
                # neither be followed nor echoed into any returned summary.
                "watched_child_addresses": {"+0x010": "0x81234568"},
                "secret_local_path": "D:/private/RAW-PRIVATE.jsonl",
            })
            i += 1
    return rows


class GolferNullControlTests(unittest.TestCase):
    def test_idle_tick_pattern_refutes_exclusive_swing_event_indicator(self):
        report = audit.analyze_records(rows_for())
        self.assertEqual(report["sample_count"], 20)
        self.assertEqual(report["within_stage_total_opportunities"], 17)
        self.assertEqual(report["within_idle_changed_pairs"], 10)
        self.assertEqual(report["within_pointer_only_changed_pairs"], 7)
        self.assertEqual(report["frame_step_equal_pairs"], 17)
        self.assertEqual(report["stage_results"]["0"]["phase"], "idle")
        self.assertEqual(report["stage_results"]["2"]["phase"], "idle")
        self.assertEqual(report["null_control_conclusion"],
                         "changes_during_idle_refutes_exclusive_swing_event_indicator")
        self.assertFalse(report["game_power_field_verified"])
        self.assertFalse(report["independent_sessions_verified"])
        self.assertNotIn("0x80140000", str(report))
        self.assertNotIn("0x81234568", str(report))
        self.assertNotIn("RAW-PRIVATE.jsonl", str(report))

    def test_pointer_only_change_does_not_prove_power(self):
        report = audit.analyze_records(rows_for(clock=False))
        self.assertEqual(report["within_idle_changed_pairs"], 0)
        self.assertEqual(report["within_pointer_only_changed_pairs"], 7)
        self.assertEqual(report["null_control_conclusion"],
                         "changes_only_during_pointer_control_not_verified_power")

    def test_all_controls_constant_is_inconclusive(self):
        rows = rows_for()
        for row in rows:
            raw = bytearray.fromhex(row["bytes_hex"])
            struct.pack_into(">I", raw, 0x74, 123)
            row["bytes_hex"] = raw.hex()
        report = audit.analyze_records(rows)
        self.assertEqual(report["within_idle_changed_pairs"], 0)
        self.assertEqual(report["within_pointer_only_changed_pairs"], 0)
        self.assertEqual(report["null_control_conclusion"],
                         "no_observed_control_change_inconclusive")

    def test_two_stage_raw_is_supported_without_pretending_baseline_replication(self):
        r = audit.analyze_records(rows_for(counts=(12, 8)))
        self.assertEqual(set(r["stage_results"]), {"0", "1"})
        self.assertFalse(r["independent_sessions_verified"])
        self.assertEqual(r["within_idle_changed_pairs"], 11)

    def test_fail_closed_on_runtime_pointer_relocation(self):
        rows = rows_for()
        rows[-1]["runtime_golf_main_address"] = "0x80170000"
        with self.assertRaisesRegex(ValueError, "object changed"):
            audit.analyze_records(rows)

    def test_fail_closed_on_phase_or_stage_label_error(self):
        rows = rows_for()
        rows[3]["phase"] = "club_motion"
        with self.assertRaisesRegex(ValueError, "control phase"):
            audit.analyze_records(rows)
        rows = rows_for()
        rows[6]["stage"] = 2
        with self.assertRaisesRegex(ValueError, "stage"):
            audit.analyze_records(rows)

    def test_fail_closed_on_rollback_or_large_non_atomic_span(self):
        rows = rows_for()
        rows[4]["frame_start"] = 5
        with self.assertRaisesRegex(ValueError, "rollback"):
            audit.analyze_records(rows)
        rows = rows_for()
        rows[4]["frame_end"] += 20
        with self.assertRaisesRegex(ValueError, "span"):
            audit.analyze_records(rows)

    def test_fail_closed_on_malformed_main_bytes(self):
        rows = rows_for()
        rows[3]["bytes_hex"] = "xx" * 0x100
        with self.assertRaisesRegex(ValueError, "bytes"):
            audit.analyze_records(rows)
        rows = rows_for()
        rows[3]["bytes_hex"] = "12"
        with self.assertRaisesRegex(ValueError, "window size"):
            audit.analyze_records(rows)

    def test_fail_closed_on_unbounded_or_unsupported_input(self):
        with self.assertRaisesRegex(ValueError, "4 and 60"):
            audit.analyze_records(rows_for(counts=(32, 30)))
        with self.assertRaisesRegex(ValueError, "need between"):
            audit.analyze_records([])

    def test_private_capture_path_and_symlink_are_restricted(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            allowed = directory / "golfer-20261025T031834Z-85d5b836-RAW-PRIVATE.jsonl"
            allowed.write_text("".join(json.dumps(r) + "\\n" for r in rows_for()),
                               encoding="utf-8")
            result = audit.read_private_capture(allowed, private_dir=directory)
            self.assertEqual(len(result), 20)
            self.assertEqual(audit.find_latest_private(directory), allowed)
            unauthorized = directory / "uploaded_savestate.jsonl"
            unauthorized.write_text(allowed.read_text(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical private"):
                audit.read_private_capture(unauthorized, private_dir=directory)

    def test_cli_does_not_print_private_paths_or_values(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            allowed = directory / "golfer-20261025T031834Z-85d5b836-RAW-PRIVATE.jsonl"
            allowed.write_text("".join(json.dumps(r) + "\\n" for r in rows_for()),
                               encoding="utf-8")
            stdout, stderr = StringIO(), StringIO()
            with patch.object(audit, "PRIVATE_CAPTURES", directory):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = audit.main(["--latest"])
            self.assertEqual(code, 0, stderr.getvalue())
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["kind"], "offline_golfer_main_0x74_null_control")
            self.assertNotIn(str(directory), stdout.getvalue())
            self.assertNotIn("0x80160000", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
