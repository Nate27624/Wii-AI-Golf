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
        rows[4]["frame_end"] = 7
        with self.assertRaisesRegex(ValueError, "rollback"):
            audit.analyze_records(rows)
        rows = rows_for()
        rows[4]["frame_end"] = rows[4]["frame_start"] + 241
        with self.assertRaisesRegex(ValueError, "span"):
            audit.analyze_records(rows)

    def test_s002_long_snapshot_within_240_is_accepted_but_timing_limited(self):
        rows = rows_for()
        # Use 30-frame non-atomic read windows, with 45 frames between
        # snapshot starts, as permitted by S002's source-gated collector.
        for i, row in enumerate(rows):
            row["frame_start"] = 1000 + 45 * i
            row["frame_end"] = row["frame_start"] + 30
        report = audit.analyze_records(rows)
        self.assertEqual(report["max_non_atomic_frame_span"], 30)
        self.assertTrue(report["timing_limited"])
        self.assertTrue(report["within_idle_changed_pairs"])
        self.assertFalse(report["game_power_field_verified"])
        self.assertTrue(report["frame_delta_relation_is_exploratory"])

    def test_high_resolution_frames_are_not_marked_timing_limited(self):
        report = audit.analyze_records(rows_for())
        self.assertEqual(report["max_non_atomic_frame_span"], 2)
        self.assertFalse(report["timing_limited"])

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
            allowed.write_text("".join(json.dumps(r) + "\n" for r in rows_for()),
                               encoding="utf-8")
            result = audit.read_private_capture(allowed, private_dir=directory)
            self.assertEqual(len(result), 20)
            self.assertEqual(audit.find_latest_private(directory), allowed)
            unauthorized = directory / "uploaded_savestate.jsonl"
            unauthorized.write_text(allowed.read_text(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical private"):
                audit.read_private_capture(unauthorized, private_dir=directory)

    def test_missing_private_capture_reports_specific_safe_reason(self):
        with tempfile.TemporaryDirectory() as td:
            output = StringIO()
            with patch.object(audit, "PRIVATE_CAPTURES", Path(td)):
                with redirect_stderr(output):
                    status = audit.main(["--latest"])
            self.assertEqual(status, 1)
            self.assertIn("no private S002 golfer capture found", output.getvalue())
            self.assertNotIn(td, output.getvalue())

    def test_incomplete_private_capture_reports_safe_row_count_gate(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            partial = directory / "golfer-20261025T031834Z-85d5b836-RAW-PRIVATE.jsonl"
            partial.write_text(json.dumps(rows_for()[0]) + "\n", encoding="utf-8")
            output = StringIO()
            with patch.object(audit, "PRIVATE_CAPTURES", directory):
                with redirect_stderr(output):
                    status = audit.main(["--latest"])
            self.assertEqual(status, 1)
            self.assertIn("need between 4 and 60 captured snapshots", output.getvalue())
            self.assertNotIn(td, output.getvalue())
            self.assertNotIn("0x80160000", output.getvalue())

    def test_unknown_value_error_is_never_echoed(self):
        output = StringIO()
        with patch.object(audit, "find_latest_private",
                          side_effect=ValueError("SECRET_PRIVATE_0x81234567")):
            with redirect_stderr(output):
                status = audit.main(["--latest"])
        self.assertEqual(status, 1)
        self.assertNotIn("SECRET_PRIVATE", output.getvalue())
        self.assertIn("did not match the reviewed input schema", output.getvalue())

    def test_cli_does_not_print_private_paths_or_values(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            allowed = directory / "golfer-20261025T031834Z-85d5b836-RAW-PRIVATE.jsonl"
            allowed.write_text("".join(json.dumps(r) + "\n" for r in rows_for()),
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


def four_rows(*, varied=True, count_per_stage=(6, 8, 6)):
    rows = rows_for(counts=count_per_stage)
    frame = 1000
    offsets = {"+0x008": (0x50, 100),
               "+0x020": (0x38, 300),
               "+0x044": (0x60, 600)}
    increments = (7, 23, 11, 29, 17, 31)
    for i, row in enumerate(rows):
        if i:
            frame += increments[(i - 1) % len(increments)] if varied else 15
        row["frame_start"] = frame
        row["frame_end"] = frame + 3
        main = bytearray.fromhex(row["bytes_hex"])
        struct.pack_into(">I", main, 0x74, (frame + 9000) & 0xFFFFFFFF)
        row["bytes_hex"] = main.hex()
        row["child_windows"] = {}
        row["watched_child_addresses"] = {}
        for ix, (key, (offset, bias)) in enumerate(offsets.items()):
            child = bytearray(0x80)
            struct.pack_into(">I", child, offset, (frame + bias) & 0xFFFFFFFF)
            row["child_windows"][key] = child.hex()
            row["watched_child_addresses"][key] = f"0x{0x80170000 + ix * 0x100:08X}"
    return rows


class FourWordClockTests(unittest.TestCase):
    def test_varied_frame_intervals_produce_strong_4word_alignment(self):
        result = audit.analyze_four_word_clock(four_rows())
        self.assertTrue(result["varied_frame_cadence_observed"])
        self.assertGreater(result["distinct_observed_frame_step_values"], 2)
        self.assertEqual(result["within_stage_comparison_opportunities"], 17)
        self.assertEqual(result["all_four_fields_changed_pairs"], 17)
        self.assertEqual(result["all_four_fields_match_elapsed_frames_pairs"], 17)
        for row in result["fields"]:
            self.assertEqual(row["matches_elapsed_frames"], 17)
            self.assertFalse(row["field_identity_verified"])
            self.assertFalse(row["power_verified"])
            if row["region"] != "main":
                self.assertEqual(row["matches_main_delta"], 17)
            self.assertLess(row["matches_shifted_frame_gaps"], 14)
        self.assertFalse(result["timing_limited"])
        self.assertNotIn("0x80170000", str(result))
        self.assertNotIn("0x80140000", str(result))

    def test_constant_sampling_cadence_is_not_identifying(self):
        result = audit.analyze_four_word_clock(four_rows(varied=False))
        self.assertEqual(result["distinct_observed_frame_step_values"], 1)
        self.assertFalse(result["varied_frame_cadence_observed"])
        self.assertEqual(result["all_four_fields_match_elapsed_frames_pairs"], 17)
        for row in result["fields"]:
            self.assertEqual(row["matches_shifted_frame_gaps"], 14)
            self.assertEqual(row["shifted_control_opportunities"], 14)

    def test_nonclock_child_does_not_match_frame_steps(self):
        rows = four_rows()
        for i, row in enumerate(rows):
            child = bytearray.fromhex(row["child_windows"]["+0x020"])
            struct.pack_into(">I", child, 0x38, i)
            row["child_windows"]["+0x020"] = child.hex()
        result = audit.analyze_four_word_clock(rows)
        suspect = next(x for x in result["fields"]
                       if x["region"] == "child_at_main+0x020")
        self.assertEqual(suspect["changed_pairs"], 17)
        self.assertEqual(suspect["matches_elapsed_frames"], 0)
        self.assertEqual(suspect["matches_main_delta"], 0)
        self.assertEqual(result["all_four_fields_match_elapsed_frames_pairs"], 0)

    def test_missing_child_and_bad_child_bytes_fail_closed(self):
        rows = four_rows()
        del rows[5]["child_windows"]["+0x020"]
        with self.assertRaisesRegex(ValueError, "provenance"):
            audit.analyze_four_word_clock(rows)
        rows = four_rows()
        rows[2]["child_windows"]["+0x020"] = "ZZ" * 0x80
        with self.assertRaisesRegex(ValueError, "bytes"):
            audit.analyze_four_word_clock(rows)

    def test_relocated_child_pointer_is_rejected(self):
        rows = four_rows()
        rows[-1]["watched_child_addresses"]["+0x008"] = "0x80180000"
        with self.assertRaisesRegex(ValueError, "identity changed"):
            audit.analyze_four_word_clock(rows)

    def test_timing_limited_30_frame_capture_is_labeled_not_rejected(self):
        rows = four_rows()
        for i, row in enumerate(rows):
            row["frame_start"] = 1000 + 45 * i
            row["frame_end"] = row["frame_start"] + 30
        report = audit.analyze_four_word_clock(rows)
        self.assertTrue(report["timing_limited"])
        self.assertEqual(report["max_non_atomic_frame_span"], 30)
        self.assertFalse(report["game_power_field_verified"])

    def test_cli_latest_four_picks_existing_eligible_older_capture(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            old = directory / "golfer-20261025T034000Z-12345678-RAW-PRIVATE.jsonl"
            new = directory / "golfer-20261025T035000Z-12345678-RAW-PRIVATE.jsonl"
            old.write_text("".join(json.dumps(r) + "\n" for r in four_rows()),
                           encoding="utf-8")
            new.write_text("".join(json.dumps(r) + "\n" for r in rows_for()),
                           encoding="utf-8")
            stdout, stderr = StringIO(), StringIO()
            with patch.object(audit, "PRIVATE_CAPTURES", directory):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = audit.main(["--latest-four"])
            self.assertEqual(code, 0, stderr.getvalue())
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["kind"], "offline_four_golfer_words_vs_emulated_frames")
            self.assertNotIn(str(directory), stdout.getvalue())
            self.assertNotIn("0x80170000", stdout.getvalue())
            self.assertNotIn("-RAW-PRIVATE", stdout.getvalue())

    def test_cli_four_missing_capture_is_fixed_redacted_message(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            output = StringIO()
            with patch.object(audit, "PRIVATE_CAPTURES", directory):
                with redirect_stderr(output):
                    self.assertEqual(audit.main(["--latest-four"]), 1)
            self.assertIn("no compatible private four-child capture found",
                          output.getvalue())
            self.assertNotIn(td, output.getvalue())



if __name__ == "__main__":
    unittest.main()
