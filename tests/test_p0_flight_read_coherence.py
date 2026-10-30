"""Synthetic-only regressions for the S000 source-aliased flight evidence gate."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "src/wii_ai_golf/audit/p0_flight_read_coherence.py"
spec = importlib.util.spec_from_file_location("p0_flight_coherence", SCRIPT)
coherence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coherence)


def sample(index, *, selected, nested=None, cc=None, **changes):
    def words(values):
        return [f"{w:08x}" for w in values]
    packet = {
        "sample_index": index, "run_token": "runA", "shot_token": "shotA",
        "scene_token": "scene5", "hole_token": "hole1",
        "source_epoch_digest": "ownerA", "alias_attested": True,
        "start_ns": index * 800_000_000,
        "end_ns": index * 800_000_000 + 625_000_000,
        "selected_be32": words(selected),
        "nested_be32": words(nested if nested is not None else selected),
        "cc_be32": words(cc if cc is not None else selected),
    }
    packet.update(changes)
    return packet


def flight():
    start, middle, future, final = (1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)
    return [
        sample(0, selected=start),
        sample(1, selected=middle, nested=start),
        sample(2, selected=future, nested=middle, cc=final),
        sample(3, selected=final, nested=future),
        sample(4, selected=final),
        sample(5, selected=final),
    ]


class FlightReadCoherenceTests(unittest.TestCase):
    def test_same_alias_different_sequential_reads_do_not_imply_two_balls(self):
        report = coherence.audit_sequential_flight_reads(flight())
        self.assertEqual(report["same_address_disagreement_packet_indices"], [1, 2, 3])
        self.assertTrue(report["non_atomic_mismatch_possible"])
        self.assertFalse(report["different_ball_objects_inferred"])
        self.assertEqual(report["selected_current_adjacent_packet_transitions"], 3)
        self.assertEqual(report["host_packet_duration_max_ms"], 625.0)
        self.assertFalse(report["training_approved"])

    def test_cache_matches_later_current_only_as_single_shot_hypothesis(self):
        report = coherence.audit_sequential_flight_reads(flight())
        self.assertEqual(report["cc_forward_exact_matches"], [
            {"cc_packet_index": 2, "later_current_packet_index": 3}])
        self.assertFalse(report["single_shot_cache_prediction_verified"])
        self.assertFalse(report["guest_physics_step_verified"])
        self.assertFalse(report["physical_velocity_or_units_verified"])

    def test_stationary_cache_not_prediction(self):
        packets = [sample(0, selected=(1, 1, 1)), sample(1, selected=(1, 1, 1))]
        report = coherence.audit_sequential_flight_reads(packets)
        self.assertEqual(report["cc_forward_match_count"], 0)
        self.assertEqual(report["selected_current_adjacent_packet_transitions"], 0)

    def test_identical_alias_words_still_not_atomicity(self):
        packets = [sample(0, selected=(1, 2, 3)), sample(1, selected=(2, 3, 4))]
        report = coherence.audit_sequential_flight_reads(packets)
        self.assertEqual(report["same_address_disagreement_packet_indices"], [])
        self.assertFalse(report["alias_independently_verified_here"])
        self.assertFalse(report["guest_physics_step_verified"])

    def test_missing_source_alias_abstains(self):
        packets = flight()
        packets[2]["alias_attested"] = False
        with self.assertRaisesRegex(coherence.EvidenceAbstain, "alias_not_attested"):
            coherence.audit_sequential_flight_reads(packets)

    def test_cross_shot_scene_hole_run_or_epoch_abstains(self):
        for field in ("shot_token", "run_token", "scene_token",
                      "hole_token", "source_epoch_digest"):
            packets = flight()
            packets[2][field] = "different"
            with self.subTest(field=field), self.assertRaisesRegex(
                    coherence.EvidenceAbstain, "epoch_changed"):
                coherence.audit_sequential_flight_reads(packets)

    def test_nonmonotonic_or_overlapping_host_packets_abstain(self):
        for changes in ({"start_ns": 1}, {"end_ns": 0}, {"start_ns": True}):
            packets = flight()
            packets[2].update(changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(
                    coherence.EvidenceAbstain, "host_brackets"):
                coherence.audit_sequential_flight_reads(packets)

    def test_reordered_dropped_duplicate_and_unbounded_abstain(self):
        for packets in (flight()[:1], flight() + [flight()[-1]],
                        [flight()[1], flight()[0]], [flight()[0]] * 81):
            with self.subTest(length=len(packets)), self.assertRaises(
                    coherence.EvidenceAbstain):
                coherence.audit_sequential_flight_reads(packets)

    def test_extra_fields_malformed_words_and_bool_timestamps_abstain(self):
        for field, value in (
            ("raw_ram", "do-not-accept"),
            ("selected_be32", ["40000000", "oops", "00000000"]),
            ("nested_be32", ["00000000"]),
            ("start_ns", False),
        ):
            packets = flight()
            packets[2][field] = value
            with self.subTest(field=field), self.assertRaises(
                    coherence.EvidenceAbstain):
                coherence.audit_sequential_flight_reads(packets)

    def test_output_excludes_raw_words_and_identity_tokens(self):
        report = str(coherence.audit_sequential_flight_reads(flight()))
        for secret in ("ownerA", "runA", "shotA", "scene5", "hole1", "0000000a"):
            self.assertNotIn(secret, report)


if __name__ == "__main__":
    unittest.main()
