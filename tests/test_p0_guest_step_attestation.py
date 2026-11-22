"""S002 guest-physics clock provenance: no Dolphin, no private captures."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_p0_guest_step_attestation as gate


def fixture(kind="synthetic"):
    identity = {"boot": "bootA", "shot": "shotA", "ball_epoch": "epochA"}
    return {
        "schema": gate.SCHEMA, "trace_kind": kind,
        "source_revision": "RSPE01_01",
        "clock_domain": "qualified_guest_physics_step_counter",
        "qualifiers": {k: True for k in gate._SOURCE_KEYS},
        "identity": identity,
        "events": [
            {"kind": "vi_frame", "host_frame": 9},
            *[
                {"kind": "guest_step", "host_frame": 10 + i,
                 "guest_step_index": 20 + i, "executed_guest_pc": True,
                 "receiver": "selected_ball", "phase": "post_golf_step",
                 "atomic": True, **identity}
                for i in range(3)
            ],
            {"kind": "host_callback", "host_frame": 30},
        ],
    }


class AttestationTests(unittest.TestCase):
    def assertAbstains(self, data, expected):
        out = gate.evaluate(data)
        self.assertEqual(out["status"], expected)
        self.assertIsNone(out["verified_native_guest_step_count"])
        self.assertFalse(out["guest_physics_clock_independently_verified"])
        self.assertFalse(out["native_game_parity_verified"])
        self.assertFalse(out["training_approved"])
        self.assertEqual(out["synthetic_qualified_guest_steps"], 0)
        self.assertEqual(out["sanitized_candidate_guest_steps"], 0)

    def test_synthetic_positive_contiguous_guest_witnesses(self):
        out = gate.evaluate(fixture())
        self.assertEqual(out["status"], "SYNTHETIC_CONTRACT_PASS")
        self.assertEqual(out["synthetic_qualified_guest_steps"], 3)
        self.assertEqual(out["first_candidate_guest_index"], 20)
        self.assertEqual(out["last_candidate_guest_index"], 22)
        self.assertIsNone(out["verified_native_guest_step_count"])
        self.assertFalse(out["native_game_parity_verified"])
        self.assertFalse(out["training_approved"])

    def test_sanitized_flags_never_independently_authenticate_native(self):
        out = gate.evaluate(fixture("sanitized"))
        self.assertEqual(out["status"], "CANDIDATE_REQUIRES_EXTERNAL_PROOF")
        self.assertEqual(out["sanitized_candidate_guest_steps"], 3)
        self.assertEqual(out["synthetic_qualified_guest_steps"], 0)
        self.assertIsNone(out["verified_native_guest_step_count"])

    def test_host_vi_ticks_alone_do_not_count_as_guest_steps(self):
        doc = fixture()
        doc["events"] = [
            {"kind": "host_callback", "host_frame": 1},
            {"kind": "vi_frame", "host_frame": 2},
        ]
        self.assertAbstains(doc, "ABSTAIN_NO_EXECUTED_GUEST_STEPS")

    def test_missing_executed_pc(self):
        doc = fixture()
        del doc["events"][1]["executed_guest_pc"]
        self.assertAbstains(doc, "ABSTAIN_MISSING_EXECUTED_PC")

    def test_pc_claim_false(self):
        doc = fixture()
        doc["events"][1]["executed_guest_pc"] = False
        self.assertAbstains(doc, "ABSTAIN_MISSING_EXECUTED_PC")

    def test_wrong_ball_receiver(self):
        doc = fixture()
        doc["events"][1]["receiver"] = "source_global_ball"
        self.assertAbstains(doc, "ABSTAIN_WRONG_BALL_RECEIVER")

    def test_wrong_boot_shot_or_ball_epoch(self):
        for field in ("boot", "shot", "ball_epoch"):
            with self.subTest(field=field):
                doc = fixture()
                doc["events"][2][field] = "other"
                self.assertAbstains(doc, "ABSTAIN_SHOT_OR_RECEIVER_EPOCH_MISMATCH")

    def test_discontinuous_phase(self):
        doc = fixture()
        doc["events"][2]["phase"] = "pre_golf_step"
        self.assertAbstains(doc, "ABSTAIN_DISCONTINUOUS_PHASE")

    def test_nonatomic(self):
        doc = fixture()
        doc["events"][2]["atomic"] = False
        self.assertAbstains(doc, "ABSTAIN_NONATOMIC_SAMPLE")

    def test_missing_guest_counter(self):
        doc = fixture()
        del doc["events"][2]["guest_step_index"]
        self.assertAbstains(doc, "ABSTAIN_MISSING_GUEST_COUNTER")

    def test_missing_host_frame(self):
        doc = fixture()
        del doc["events"][2]["host_frame"]
        self.assertAbstains(doc, "ABSTAIN_MISSING_HOST_FRAME")

    def test_guest_counter_gap_and_duplicate(self):
        for step in (20, 24):
            with self.subTest(step=step):
                doc = fixture()
                doc["events"][2]["guest_step_index"] = step
                self.assertAbstains(doc, "ABSTAIN_DISCONTINUOUS_GUEST_COUNTER")

    def test_duplicate_host_frame_and_time_reversal(self):
        for frame in (9, 10):
            with self.subTest(host_frame=frame):
                doc = fixture()
                doc["events"][2]["host_frame"] = frame
                self.assertAbstains(
                    doc, "ABSTAIN_DUPLICATE_OR_NONMONOTONIC_HOST_FRAME")

    def test_no_inferred_guest_cadence_from_host_frames(self):
        doc = fixture()
        doc["clock_domain"] = "host_frame"
        self.assertAbstains(doc, "ABSTAIN_HOST_OR_UNKNOWN_CLOCK")

    def test_missing_source_provenance_flag(self):
        for flag in gate._SOURCE_KEYS:
            with self.subTest(flag=flag):
                doc = fixture()
                del doc["qualifiers"][flag]
                self.assertAbstains(doc, "ABSTAIN_SOURCE_PROVENANCE")

    def test_wrong_source_revision(self):
        doc = fixture()
        doc["source_revision"] = "RSPE01_00"
        self.assertAbstains(doc, "ABSTAIN_SOURCE_REVISION")

    def test_sparse_host_frames_with_contiguous_guest_counter(self):
        doc = fixture()
        doc["events"][1]["host_frame"] = 1
        doc["events"][2]["host_frame"] = 10
        doc["events"][3]["host_frame"] = 999
        out = gate.evaluate(doc)
        self.assertEqual(out["status"], "SYNTHETIC_CONTRACT_PASS")
        self.assertEqual(out["synthetic_qualified_guest_steps"], 3)
        # Never equate host frame separation with guest physics rate.

    def test_strict_bools_and_integer_bounds(self):
        for key, bad in (
            ("atomic", 1), ("executed_guest_pc", 1),
            ("guest_step_index", True), ("host_frame", 1.5),
            ("host_frame", -1), ("host_frame", 1000000001),
        ):
            with self.subTest(key=key, bad=bad):
                doc = fixture()
                doc["events"][1][key] = bad
                with self.assertRaises(ValueError):
                    gate.evaluate(doc)

    def test_reject_unexpected_private_or_raw_fields(self):
        for at in ("top", "event", "qualifiers"):
            with self.subTest(at=at):
                doc = fixture()
                if at == "top":
                    doc["raw_ram"] = "private"
                elif at == "event":
                    doc["events"][1]["memory_address"] = "private"
                else:
                    doc["qualifiers"]["rom_bytes"] = True
                with self.assertRaises(ValueError):
                    gate.evaluate(doc)
        doc = fixture()
        doc["identity"]["boot"] = "0x804bf868"
        with self.assertRaises(ValueError):
            gate.evaluate(doc)

    def test_reject_bad_shapes_and_unbounded_events(self):
        doc = fixture()
        doc["events"] = [{}] * (gate.MAX_EVENTS + 1)
        with self.assertRaises(ValueError):
            gate.evaluate(doc)
        for kind in (None, [], "real_verified"):
            doc = fixture()
            doc["trace_kind"] = kind
            with self.assertRaises(ValueError):
                gate.evaluate(doc)

    def test_stdin_cli_synthetic_and_safe_error(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / (
            "review_p0_guest_step_attestation.py")
        p = subprocess.run([sys.executable, str(script)],
                           input=json.dumps(fixture()), capture_output=True,
                           text=True, check=True)
        result = json.loads(p.stdout)
        self.assertEqual(result["status"], "SYNTHETIC_CONTRACT_PASS")
        self.assertIsNone(result["verified_native_guest_step_count"])
        failed = subprocess.run([sys.executable, str(script)], input="{",
                                capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(json.loads(failed.stdout)["status"],
                         "ABSTAIN_INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
