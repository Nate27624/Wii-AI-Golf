"""Fabricated-only regression tests for a source-typed golf display flag."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_seven_target_emitter_flag_private as mod


def state():
    return {
        "slot": 0, "hole": 1,
        "_private_owners": tuple(0x90000000 + i * 0x100 for i in range(7)),
        "_private_selectors": (4, 1, 0),
        "_private_pin": (100, 200, 300),
        "_private_start": (10, 20, 30),
        "_private_ball": (10, 20, 30),
        "_private_target_effect_ref": 0x90008000,
        "target_emitter_kill_requested": False,
        "minimap_visibility_requested": True,
    }


def cohort():
    d = {i: state() for i in mod.PHASES}
    d[2]["_private_ball"] = (11, 21, 31)
    d[6]["_private_ball"] = (12, 22, 32)
    d[7]["_private_ball"] = (13, 23, 33)
    return d


class TargetEmitterTests(unittest.TestCase):
    def test_big_endian_byte_true_and_zero(self):
        self.assertTrue(mod._flag_from_first_be_byte(0x01020304))
        self.assertFalse(mod._flag_from_first_be_byte(0x00FFFFFF))
        self.assertFalse(mod._flag_from_first_be_byte(0))

    def test_do_not_use_low_byte_instead(self):
        self.assertFalse(mod._flag_from_first_be_byte(0x00000001))
        with self.assertRaises(ValueError):
            mod._flag_from_first_be_byte(0x02000000)

    def test_invalid_word_rejected(self):
        for value in (-1, 2**32, 1.0, None, True, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                mod._flag_from_first_be_byte(value)

    def test_stable_flag_is_not_misreported_as_hit(self):
        r = mod.summarize(cohort())
        self.assertEqual([x["target_emitter_kill_flag_changed"]
                          for x in r["provisional_within_shot_comparisons"]],
                         [False] * 4)
        self.assertFalse(r["ball_contact_or_impact_verified"])
        self.assertFalse(r["green_landing_or_score_verified"])
        self.assertFalse(r["training_approved"])

    def test_change_on_late_wedge_is_only_ui_toggle(self):
        d = cohort()
        d[7]["target_emitter_kill_requested"] = True
        edges = mod.summarize(d)["provisional_within_shot_comparisons"]
        self.assertEqual([x["target_emitter_kill_flag_changed"] for x in edges],
                         [False, False, True, True])
        self.assertFalse(mod.summarize(d)["target_effect_blinking_observed_on_screen"])

    def test_reference_pointer_change_reported_not_hidden(self):
        d = cohort()
        d[7]["_private_target_effect_ref"] = 0
        report = mod.summarize(d)
        self.assertTrue(report["provisional_within_shot_comparisons"][2]
                        ["target_effect_reference_changed"])
        self.assertFalse(report["per_snapshot"][6]["target_effect_reference_nonnull"])

    def test_source_pin_start_and_config_guards(self):
        for key, value in (
            ("_private_pin", (100, 200, 301)),
            ("_private_start", (11, 20, 30)),
            ("_private_selectors", (4, 1, 1)),
            ("_private_owners", tuple(0x90000000 + i * 0x100
                                      for i in range(6)) + (0x90009000,)),
            ("slot", 2),
            ("hole", 2),
        ):
            d = cohort()
            d[6][key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                mod.summarize(d)

    def test_malformed_state_refused(self):
        for key, value in (
            ("_private_ball", (1, 2)),
            ("_private_pin", (-1, 2, 3)),
            ("target_emitter_kill_requested", 1),
            ("minimap_visibility_requested", 0),
            ("_private_target_effect_ref", -1),
            ("_private_selectors", [4, 1, 0]),
            ("_private_start", (1, float("nan"), 3)),
        ):
            d = cohort()
            d[5][key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                mod.summarize(d)

    def test_only_provisional_same_shot_edges(self):
        report = mod.summarize(cohort())
        self.assertEqual([x["pair"] for x in
                          report["provisional_within_shot_comparisons"]],
                         ["1_to_2", "5_to_6", "6_to_7", "5_to_7"])
        self.assertFalse(report["human_phase_labels_and_order_machine_verified"])

    def test_private_values_not_in_public_report(self):
        d = cohort()
        d[6]["target_emitter_kill_requested"] = True
        r = json.dumps(mod.summarize(d))
        for secret in (
            "_private_",
            "0x90000000", "0x90008000", "0x90009000",
            '"_private_pin"', '"_private_ball"', "sha256", "manifest-PRIVATE",
            '"_private_target_effect_ref"',
        ):
            self.assertNotIn(secret, r)

    def test_sample_reads_source_exact_bool_byte_and_target_pointer(self):
        field = 0x90001000
        cfg = 0x90002000
        pm = 0x90003000
        ball = 0x90004000
        u = {
            mod.roster.GOLF_CONFIG_STATIC: cfg,
            mod.roster.PLAYER_MANAGER_STATIC_CANDIDATE: pm,
            pm + 4 + 0x88: ball,
            ball + 0x4C: ball + 0x30,
            field + 0xA0: 0,
            field + 0xA4: 0x010000FF,
            field + 0x88: 0x00AAAAAA,
        }

        class Reader:
            def u32(self, addr):
                if addr not in u:
                    raise ValueError("out-of-scope source read")
                return u[addr]

        base = {
            "field": field, "selected_index": 0, "hole": 1,
            "pin_obj": 0x90005000, "start_obj": 0x90006000,
            "cfg_bc": 4, "cfg_c0": 1, "cfg_c4": 0,
            "pin": (10, 20, 30),
            "triplets": {
                "source_current_start": (1, 2, 3),
                "ball_object_0x030": (4, 5, 6),
            },
        }
        with patch.object(mod.seven, "_get", return_value=base):
            s = mod._sample(Reader())
        self.assertTrue(s["target_emitter_kill_requested"])
        self.assertFalse(s["minimap_visibility_requested"])
        self.assertEqual(s["_private_target_effect_ref"], 0)

    def test_source_reader_refuses_bad_bool(self):
        with patch.object(mod.seven, "_get",
                          side_effect=ValueError("source scene invalid")):
            class Reader:
                def u32(self, addr):
                    raise AssertionError("must not read if source fails")
            with self.assertRaisesRegex(ValueError, "source scene invalid"):
                mod._sample(Reader())

    def test_original_bank_manifest_must_pass_before_sampling(self):
        with patch.object(mod.seven, "_check_archive",
                          side_effect=ValueError("SHA incorrect")) as gate:
            with patch.object(mod, "_sample", side_effect=AssertionError(
                    "source sampling must not run")):
                with self.assertRaises(ValueError):
                    mod.analyze(Path("fake-data"))
        self.assertEqual(gate.call_count, 1)

    def test_python_isolated_cli(self):
        script = ROOT / "scripts" / "audit_p0_seven_target_emitter_flag_private.py"
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run(
                [sys.executable, "-I", str(script), "--help"],
                cwd=td, text=True, capture_output=True, timeout=20)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--archive", p.stdout)

    def test_absent_archive_abstains_no_private_path_print(self):
        with patch.object(mod.seven, "_check_archive",
                          side_effect=ValueError("private-capture-path")):
            with patch("sys.stderr", new_callable=__import__("io").StringIO) as err:
                code = mod.main(["--archive", "some-private-path"])
        self.assertEqual(code, 2)
        self.assertNotIn("private-capture-path", err.getvalue())
        self.assertNotIn("some-private-path", err.getvalue())


if __name__ == "__main__":
    unittest.main()
