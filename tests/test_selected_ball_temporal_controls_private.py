"""No private Wii binaries, emulator or network: synthetic temporal controls."""
from __future__ import annotations

from copy import deepcopy
from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_selected_ball_temporal_controls_private as gate


def fixture():
    # Deliberately fabricated big-endian u32 and HEAP addresses.
    start = [0x3F800000, 0x00000000, 0x40A00000]
    motion = [0x40000000, 0x3E800000, 0x40C00000]
    vals = [start, start, start, motion]
    stages = gate.EXPECTED_STAGES
    samples = []
    for i in range(4):
        samples.append({
            "stage": stages[i],
            "boot_token": "SYNTH-BOOT-TEST-123456789",
            "game_id": "RSPE01",
            "revision": 1,
            "scene_id": 5,
            "sport_id": 2,
            "game_mode": 4,
            "hole_index": 1,
            "selected_record_index": 0,
            "frame_start": 100 + i*120,
            "frame_end": 101 + i*120,
            "acquisition_source": gate.EXPECTED_SOURCE,
            "source_path_gates_passed": True,
            "selected_record_pointer": 0x91001234,
            "ball_owner_pointer": 0x91002234,
            "start_object_pointer": 0x91003234,
            "selected_ball_vec": list(vals[i]),
            "current_start_vec": list(start),
            "record_pos_054_vec": list(vals[i]),
            "record_pos_060_vec": list(vals[i]),
        })
    return {
        "kind": gate.KIND,
        "schema_version": 1,
        "samples": samples,
        "idle_no_action_observed": True,
        "human_ball_motion_observed": True,
        "human_contact_observed": True,
        "event_between_before_after_observed": True,
        "source_contract_id": gate.EXPECTED_CONTRACT,
        "waveform_unmodified_attested": True,
    }


class TemporalControlsTests(unittest.TestCase):
    def test_provisional_positive_is_never_physics_or_training_proof(self):
        out = gate.evaluate(fixture())
        self.assertEqual(out["result"], "provisional_motion_correlated_candidate")
        self.assertEqual(out["changed_selected_ball_word_components_after_event"], 3)
        self.assertTrue(out["selected_ball_post_equals_record_054"])
        self.assertTrue(out["selected_ball_post_equals_record_060"])
        self.assertTrue(all(out["control_gates"].values()))
        for flag in ("same_boot_independently_verified",
                     "human_observation_independently_verified",
                     "physical_world_xyz_verified",
                     "actual_ball_physics_object_verified",
                     "recognized_swing_power_verified",
                     "training_approved", "automatic_publication_approved"):
            self.assertFalse(out[flag])

    def test_privacy_stdout_shape_no_raw_words_pointers_or_boot_token(self):
        data = fixture()
        rendered = json.dumps(gate.evaluate(data))
        for text in ("SYNTH-BOOT-TEST", "91001234", "3F800000",
                     "40000000", "frame_start", "selected_ball_vec",
                     "record_pos_054_vec", "private-json"):
            self.assertNotIn(text, rendered)
        self.assertIn("changed_selected_ball_word_components_after_event", rendered)

    def test_idle_control_drift_abstains_even_if_event_moves(self):
        rec = fixture()
        rec["samples"][1]["selected_ball_vec"][1] = 0x12345678
        out = gate.evaluate(rec)
        self.assertFalse(out["control_gates"]["idle_control_selected_ball_static"])
        self.assertEqual(out["result"], "abstain_inadequate_controls_or_provenance")

    def test_start_reference_motion_abstains(self):
        rec = fixture()
        rec["samples"][3]["current_start_vec"][2] += 1
        out = gate.evaluate(rec)
        self.assertFalse(out["control_gates"]["source_start_translation_static"])
        self.assertIn("abstain", out["result"])

    def test_selected_slot_switch_abstains(self):
        rec = fixture()
        rec["samples"][3]["selected_record_index"] = 1
        out = gate.evaluate(rec)
        self.assertFalse(out["control_gates"]["source_selected_slot_index_stable"])
        self.assertIn("abstain", out["result"])

    def test_relocated_ball_pointer_abstains(self):
        rec = fixture()
        rec["samples"][3]["ball_owner_pointer"] = 0x91003334
        out = gate.evaluate(rec)
        self.assertFalse(out["control_gates"]
                         ["selected_record_ball_and_start_pointer_stable"])
        self.assertIn("abstain", out["result"])

    def test_no_real_ball_change_abstains(self):
        rec = fixture()
        rec["samples"][3]["selected_ball_vec"] = list(
            rec["samples"][2]["selected_ball_vec"])
        out = gate.evaluate(rec)
        self.assertEqual(out["changed_selected_ball_word_components_after_event"], 0)
        self.assertIn("abstain", out["result"])

    def test_missing_human_contact_abstains_not_false_contact(self):
        rec = fixture()
        rec["human_contact_observed"] = False
        out = gate.evaluate(rec)
        self.assertFalse(out["control_gates"]["operator_reports_ball_contact"])
        self.assertIn("abstain", out["result"])

    def test_event_not_bracketed_abstains(self):
        rec = fixture()
        rec["event_between_before_after_observed"] = False
        out = gate.evaluate(rec)
        self.assertFalse(out["control_gates"]
                         ["operator_reports_event_between_frame_brackets"])
        self.assertIn("abstain", out["result"])

    def test_modified_waveform_abstains(self):
        rec = fixture()
        rec["waveform_unmodified_attested"] = False
        self.assertIn("abstain", gate.evaluate(rec)["result"])

    def test_untrusted_boot_mismatch_abstains(self):
        rec = fixture()
        rec["samples"][2]["boot_token"] = "SYNTH-SECOND-BOOT-456789"
        out = gate.evaluate(rec)
        self.assertFalse(out["control_gates"]["operator_claims_one_boot"])
        self.assertIn("abstain", out["result"])

    def test_wrong_hole_abstains_not_cross_course_comparison(self):
        rec = fixture()
        rec["samples"][3]["hole_index"] = 2
        out = gate.evaluate(rec)
        self.assertFalse(out["control_gates"]["same_source_hole_all_phases"])
        self.assertIn("abstain", out["result"])

    def test_frame_overlap_abstains(self):
        rec = fixture()
        rec["samples"][2]["frame_start"] = rec["samples"][1]["frame_end"]
        rec["samples"][2]["frame_end"] = rec["samples"][2]["frame_start"] + 1
        out = gate.evaluate(rec)
        self.assertFalse(out["control_gates"]
                         ["strictly_ordered_emulated_frame_brackets"])
        self.assertIn("abstain", out["result"])

    def test_more_than_two_frame_read_span_rejected(self):
        rec = fixture()
        rec["samples"][1]["frame_end"] = rec["samples"][1]["frame_start"] + 3
        with self.assertRaisesRegex(ValueError, "frame bracket"):
            gate.evaluate(rec)

    def test_invalid_read_origin_and_scene_rejected(self):
        rec = fixture()
        rec["samples"][0]["acquisition_source"] = "GUI-paused-dump"
        with self.assertRaises(ValueError):
            gate.evaluate(rec)
        rec = fixture()
        rec["samples"][1]["scene_id"] = 4
        with self.assertRaises(ValueError):
            gate.evaluate(rec)

    def test_missing_source_chain_and_non_native_bool_rejected(self):
        rec = fixture()
        rec["samples"][0]["source_path_gates_passed"] = False
        with self.assertRaises(ValueError):
            gate.evaluate(rec)
        rec = fixture()
        rec["human_ball_motion_observed"] = 1  # int must not mean True
        with self.assertRaises(ValueError):
            gate.evaluate(rec)

    def test_malformed_u32_or_address_rejected(self):
        rec = fixture()
        rec["samples"][0]["selected_ball_vec"][0] = -1
        with self.assertRaises(ValueError):
            gate.evaluate(rec)
        rec = fixture()
        rec["samples"][2]["start_object_pointer"] = 0x94000000
        with self.assertRaises(ValueError):
            gate.evaluate(rec)

    def test_unapproved_schema_extras_rejected(self):
        rec = fixture()
        rec["unreviewed_public_uploader"] = True
        with self.assertRaises(ValueError):
            gate.evaluate(rec)
        rec = fixture()
        rec["samples"][1]["raw_memory_hex"] = "A0"
        with self.assertRaises(ValueError):
            gate.evaluate(rec)

    def test_future_gui_pair_cannot_fake_frame_hook(self):
        rec = fixture()
        rec["samples"][3]["frame_start"] = None
        with self.assertRaises(ValueError):
            gate.evaluate(rec)

    def test_cli_missing_private_file_redacts_path(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "SUPER-SECRET-PATH-raw-private.json"
            stderr = StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(gate.main(["--private-json", str(path)]), 1)
            self.assertNotIn("SUPER-SECRET-PATH", stderr.getvalue())
            self.assertIn("Private temporal evidence gate stopped", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
