"""Synthetic-only falsification tests for offline P0 swing power candidate review."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "p0_power_review", ROOT / "scripts" / "review_p0_swing_power_candidates.py")
p0 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p0)


def fixture():
    # Synthetic graded signal: GAUGE - PRE is low .2, high .6.
    # All controls are negative; all RECOVER samples equal PRE.
    trials = []
    for i, tag in enumerate(p0.TRIALS):
        low = tag.startswith("L")
        fields = {k: 1.0 for k in p0.FIELDS}
        peak = {k: 1.0 + (.2 if low else .6) for k in p0.FIELDS}
        trials.append({
            "trial": tag, "shot_id": "shot"+str(i), "scene_id": "scene5",
            "hole_id": "hole0", "actor_id": "selected_actor",
            "generation": "gen"+str(i), "source_gated": True,
            "owner_stable": True, "operator_precontact": True,
            "display_percent": (25 if low else 75),
            "windows": {
                "PRE": {"span_ms": 150, "values": dict(fields)},
                "GAUGE": {"span_ms": 150, "values": dict(peak)},
                "RECOVER": {"span_ms": 150, "values": dict(fields)},
            },
        })
    controls = {kind: {"source_gated": True, "operator_no_contact": True,
                       "delta": {k: 0.0 for k in p0.FIELDS}}
                for kind in p0.CONTROLS}
    return {"schema_version": 1, "kind": "p0_power_visible_meter_contrast",
            "origin": "synthetic", "revision": "RSPE01 Rev1",
            "trials": trials, "controls": controls}


def row(report, name="player_record_090"):
    return next(x for x in report["rows"] if x["candidate"] == name)


class PowerReviewTests(unittest.TestCase):
    def test_plan_is_read_only_and_pre_registered(self):
        plan = p0.plan()
        self.assertEqual(plan["trials_in_order"], ["L1", "H1", "H2", "L2"])
        self.assertEqual(plan["negative_controls"], list(p0.CONTROLS))
        self.assertFalse(plan["training_approved"])

    def test_exact_source_gated_repeated_graded_hypothesis_never_training(self):
        report = p0.review(fixture())
        self.assertEqual(row(report)["status"], "REPEATABLE_GAUGE_ASSOCIATION_ONLY")
        self.assertTrue(row(report)["graded_in_two_counterbalanced_pairs"])
        self.assertFalse(row(report)["runtime_verified"])
        self.assertFalse(row(report)["training_eligible"])
        self.assertFalse(report["training_approved"])
        self.assertFalse(report["power_measured"])
        self.assertFalse(report["game_A_acceptance_verified"])

    def test_known_easing_and_flags_are_not_promoted_to_power(self):
        report = p0.review(fixture())
        for field in ("player_record_030", "player_record_034_byte0",
                      "player_record_034_byte1", "player_record_094",
                      "player_record_098"):
            self.assertEqual(row(report, field)["status"],
                             "GRADED_BUT_ALTERNATIVE_EXPLANATION")
        for field in p0.GEOMETRY:
            self.assertEqual(row(report, field)["status"], "GEOMETRY_OR_AIM_CONTROL")

    def test_idle_A_only_motion_without_A_confounds(self):
        for control in p0.CONTROLS:
            sample = fixture()
            sample["controls"][control]["delta"]["player_record_090"] = .1
            self.assertEqual(row(p0.review(sample))["status"], "NO_CONTACT_CONFOUND")

    def test_nonmonotonic_and_inconsistent_sign_falsify(self):
        sample = fixture()
        sample["trials"][2]["windows"]["GAUGE"]["values"]["player_record_090"] = 1.1
        self.assertEqual(row(p0.review(sample))["status"], "NOT_GRADED_IN_BOTH_PAIRS")
        sample = fixture()
        sample["trials"][1]["windows"]["GAUGE"]["values"]["player_record_090"] = .5
        self.assertEqual(row(p0.review(sample))["status"], "NO_REPEATED_SIGNED_RESPONSE")

    def test_recovery_latch_is_not_power(self):
        sample = fixture()
        sample["trials"][3]["windows"]["RECOVER"]["values"]["player_record_090"] = 1.1
        self.assertEqual(row(p0.review(sample))["status"], "PERSISTENT_AFTER_RECOVERY")

    def test_missing_witness_no_false_green(self):
        sample = fixture()
        del sample["trials"][0]["windows"]["GAUGE"]["values"]["player_record_090"]
        self.assertEqual(row(p0.review(sample))["status"], "NOT_MEASURED")
        sample = fixture()
        del sample["controls"]["A_ONLY"]["delta"]["player_record_090"]
        self.assertEqual(row(p0.review(sample))["status"], "MISSING_NEGATIVE_CONTROL")

    def test_identity_and_source_gates_fail_closed(self):
        for edit in (
            lambda s: s["trials"][2].update(shot_id="shot0"),
            lambda s: s["trials"][1].update(hole_id="hole1"),
            lambda s: s["trials"][0].update(source_gated=False),
            lambda s: s["trials"][0].update(owner_stable=False),
            lambda s: s["trials"][0].update(operator_precontact=False),
            lambda s: s["controls"]["MOTION_NO_A"].update(operator_no_contact=False),
            lambda s: s["trials"][1].update(display_percent=30),
            lambda s: s["trials"].reverse(),
        ):
            sample = fixture()
            edit(sample)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                p0.review(sample)

    def test_nonfinite_raw_extra_private_or_censored_results_refused(self):
        for edit in (
            lambda s: s["trials"][0]["windows"]["PRE"]["values"].update(
                player_record_090=float("nan")),
            lambda s: s["trials"][0]["windows"]["PRE"]["values"].update(
                private_raw_word="3F800000"),
            lambda s: s["trials"][0]["windows"]["GAUGE"].update(
                raw_pointer="0x90000000"),
            lambda s: s["trials"][0].update(native_distance_ft=100),
            lambda s: s.update(training_approved=True),
            lambda s: s["trials"][0]["windows"]["GAUGE"].update(span_ms=9000),
        ):
            sample = fixture()
            edit(sample)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                p0.review(sample)

    def test_no_sensitive_identity_or_numeric_value_emitted(self):
        sample = fixture()
        sample["trials"][0]["shot_id"] = "secret_shot"
        sample["trials"][0]["windows"]["GAUGE"]["values"]["player_record_090"] = 1.324154
        output = json.dumps(p0.review(sample))
        self.assertNotIn("secret_shot", output)
        self.assertNotIn("1.324154", output)
        self.assertNotIn("RSPE01 Rev1", output)

    def test_cli_plan_and_abstain(self):
        path = ROOT / "scripts" / "review_p0_swing_power_candidates.py"
        a = subprocess.run([sys.executable, str(path), "--plan"],
                           capture_output=True, text=True)
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertFalse(json.loads(a.stdout)["training_approved"])
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "bad.json"
            f.write_text('{"bad":"raw"}', encoding="utf-8")
            b = subprocess.run([sys.executable, str(path), "--evidence", str(f)],
                               capture_output=True, text=True)
            self.assertEqual(b.returncode, 2)
            self.assertIn("ABSTAIN_UNQUALIFIED", b.stdout)
            self.assertNotIn(str(f), b.stdout)


if __name__ == "__main__":
    unittest.main()
