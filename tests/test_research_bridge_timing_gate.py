"""Synthetic S001/S002 timing gates, never connects to Dolphin."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.research_bridge_timing_gate import audit_bridge_timing_fixture

PHASES = ("pre_a", "a_hold", "backswing", "forward", "follow_through", "release", "post")


def example():
    times = (100, 120, 150, 170, 190, 210, 230)
    return {
        "schema_version": 1, "kind": "proposed-bridge-timing-fixture",
        "game_id": "RSPE01", "revision": 1, "game_mode": 4,
        "boot_id": "freshboot_01", "shot_id": "same_shot_01",
        "bridge_sha256": "a" * 64, "trace_sha256": "b" * 64,
        "event_provenance": "bridge_callback_emulated_frame",
        "events": [
            {"phase": p, "emulated_frame": frame,
             "a_requested": p in ("a_hold", "backswing", "forward", "follow_through")}
            for p, frame in zip(PHASES, times)
        ],
        "reads": [
            {"phase": p, "frame_start": times[i] + 1, "frame_end": times[i] + 2}
            for i, p in enumerate(PHASES)
        ],
    }


class BridgeTimingFixtureTests(unittest.TestCase):
    def test_small_watchlist_is_timing_only(self):
        r = audit_bridge_timing_fixture(example())
        self.assertTrue(r["timing_fixture_passes"])
        self.assertEqual((r["read_span_max"], r["read_span_p95"]), (1, 1))
        for key in ("game_applied_input_verified", "game_power_verified",
                    "club_object_verified", "physical_contact_verified",
                    "ready_for_power_regression", "same_shot_link_verified",
                    "observer_noninterference_verified"):
            self.assertFalse(r[key])
        self.assertNotIn("same_shot_01", str(r))
        self.assertNotIn("a" * 64, str(r))

    def test_old_six_ten_eighteen_frame_reads_fail(self):
        for frames in (6, 10, 18):
            r = example()
            r["reads"] = [{"phase": p, "frame_start": e["emulated_frame"] + 1,
                            "frame_end": e["emulated_frame"] + 1 + frames}
                           for p, e in zip(PHASES, r["events"])]
            result = audit_bridge_timing_fixture(r)
            self.assertFalse(result["timing_fixture_passes"])
            self.assertEqual(result["reason"], "non_atomic_reads_too_slow")

    def test_client_rpc_status_is_never_frame_provenance(self):
        for value in ("client_rpc_request", "trace_status_ack", "frame.get_count_rpc"):
            r = example()
            r["event_provenance"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Client RPC"):
                audit_bridge_timing_fixture(r)

    def test_no_forged_power_or_private_fields(self):
        for key in ("runtime_player_address", "raw_bytes", "power_percent",
                    "game_contact", "local_path", "controller_applied"):
            r = example()
            r[key] = "secret"
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit_bridge_timing_fixture(r)
        r = example()
        r["reads"][0]["bytes_hex"] = "abcdef"
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            audit_bridge_timing_fixture(r)

    def test_reject_wrong_game_revision_mode(self):
        for key, value in (("schema_version", True), ("game_id", "RSPP01"), ("revision", 0), ("revision", True),
                           ("game_mode", 3), ("game_mode", False)):
            r = example()
            r[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit_bridge_timing_fixture(r)

    def test_reject_invalid_ids_or_hashes(self):
        for key, value in (("boot_id", "../private"), ("shot_id", "x"),
                           ("trace_sha256", "f" * 63), ("bridge_sha256", "Z" * 64)):
            r = example()
            r[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit_bridge_timing_fixture(r)

    def test_reject_missing_or_duplicate_phase_event(self):
        r = example()
        r["events"][3]["phase"] = "backswing"
        with self.assertRaisesRegex(ValueError, "Phase order"):
            audit_bridge_timing_fixture(r)
        r = example()
        r["events"].pop()
        with self.assertRaisesRegex(ValueError, "seven"):
            audit_bridge_timing_fixture(r)

    def test_reject_rpc_issued_A_continuity_inconsistency(self):
        r = example()
        r["events"][3]["a_requested"] = False
        with self.assertRaisesRegex(ValueError, "continuity"):
            audit_bridge_timing_fixture(r)

    def test_reject_unordered_frames_and_boolean_frames(self):
        for value in (100, True, -1):
            r = example()
            r["events"][1]["emulated_frame"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit_bridge_timing_fixture(r)

    def test_reject_read_crossing_phase(self):
        r = example()
        r["reads"][2]["frame_end"] = 171  # next 'forward' starts 170
        with self.assertRaisesRegex(ValueError, "crosses"):
            audit_bridge_timing_fixture(r)

    def test_reject_overlapping_or_backwards_reads(self):
        r = example()
        r["reads"][1]["frame_start"] = 90
        with self.assertRaises(ValueError):
            audit_bridge_timing_fixture(r)
        r = example()
        r["reads"][1]["frame_end"] = 119
        with self.assertRaises(ValueError):
            audit_bridge_timing_fixture(r)
        r = example()
        r["reads"][0]["frame_start"] = True
        with self.assertRaises(ValueError):
            audit_bridge_timing_fixture(r)

    def test_missing_essential_phase_read_blocks_fit(self):
        r = example()
        r["reads"] = [x for x in r["reads"] if x["phase"] != "forward"]
        v = audit_bridge_timing_fixture(r)
        self.assertFalse(v["timing_fixture_passes"])
        self.assertEqual(v["reason"], "missing_essential_phase_reads")
        self.assertEqual(v["missing_essential_phases"], ["forward"])

    def test_p95_is_measured_not_inferred_from_previous_runs(self):
        r = example()
        r["reads"][0]["frame_end"] += 2  # 3 frames for one of seven samples
        v = audit_bridge_timing_fixture(r)
        self.assertEqual(v["read_span_p95"], 3)
        self.assertFalse(v["timing_fixture_passes"])


if __name__ == "__main__":
    unittest.main()
