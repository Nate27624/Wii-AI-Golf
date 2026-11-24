"""Pure-host falsification controls for the bounded S002 power-to-launch ledger."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import struct
import subprocess
import sys
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "audit_p0_accepted_power_launch_boundary_private.py"
SPEC = importlib.util.spec_from_file_location("s002_accepted_boundary", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def e(op: str, r: str = "calcA") -> dict[str, str]:
    return {"op": op, "receiver": r}


class AcceptedPowerBoundaryTests(unittest.TestCase):
    def check(self, paths, *, complete=True, aliases=True):
        return audit.classify_synthetic_reaching_paths(
            paths, complete_cfg=complete, receiver_alias_proven=aliases)

    def test_reuse_existing_sha_qualified_receipts_without_private_source(self):
        ledger = audit.source_ledger()
        self.assertEqual(len(ledger["published_original_source_receipts"]), 4)
        self.assertEqual(ledger["kind"], audit.KIND)
        self.assertEqual([edge["status"] for edge in ledger["edges"]],
                         ["PASS", "UNKNOWN", "PASS", "UNKNOWN"])
        self.assertEqual(ledger["edges"][0]["scope"], "static_original_sha_qualified")
        for key in ("actual_accepted_power_verified", "selected_launch_p0_v0_verified",
                    "native_game_parity_verified", "training_approved",
                    "source_private_study_executed_by_this_tool"):
            self.assertIs(ledger[key], False)

    def test_calc40_zero_nonzero_and_absent_branches_do_not_label_power(self):
        for value, state in ((0, "ZERO"), (1, "NONZERO"),
                             (0xffffffff, "NONZERO"), (None, "UNKNOWN")):
            with self.subTest(value=value):
                result = audit.classify_calc_branch(value, 3, 1, 0, 0.5)
                self.assertEqual(result["calc40_source_branch"], state)
                self.assertFalse(result["committed_power_verified"])
                self.assertFalse(result["native_branch_meaning_verified"])

    def test_state_flag_context_unknown_and_zero_are_distinct(self):
        empty = audit.classify_calc_branch(1, None, None, None, None)
        full = audit.classify_calc_branch(1, 0, 0, 0, 0.0)
        self.assertFalse(empty["state_flag_context_available"])
        self.assertTrue(full["state_flag_context_available"])
        self.assertFalse(full["committed_power_verified"])

    def test_branch_inputs_fail_closed_malformed(self):
        for value in (-1, 2**32, True, "1", 1.5):
            with self.subTest(value=value), self.assertRaises(audit.Abstain):
                audit.classify_calc_branch(value, 1, 0, 0, 0.5)
        for args in ((1, -1, 0, 0, 0.5), (1, 3, True, 0, 0.5),
                     (1, 3, 0, 2**32, 0.5), (1, 3, 0, 0, float("nan"))):
            with self.subTest(args=args), self.assertRaises(audit.Abstain):
                audit.classify_calc_branch(*args)

    def test_nonlin_read_before_reset_is_synthetic_live(self):
        result = self.check([[e("nonlinear"), e("read"), e("reset")]])
        self.assertEqual(result["per_path"], ["LIVE"])
        self.assertEqual(result["synthetic_reaching_definition"],
                         "LIVE_ON_ALL_ENUMERATED_PATHS_SYNTHETIC")
        self.assertIs(result["actual_shot_commit_verified"], False)

    def test_same_receiver_reset_kills_nonlin(self):
        result = self.check([[e("nonlinear"), e("reset"), e("read")]])
        self.assertEqual(result["per_path"], ["KILLED_BY_RESET"])
        self.assertEqual(result["synthetic_reaching_definition"],
                         "KILLED_ON_ALL_ENUMERATED_PATHS_SYNTHETIC")

    def test_same_receiver_later_overwrite_kills_nonlin(self):
        result = self.check([[e("nonlinear"), e("other_write"), e("read")]])
        self.assertEqual(result["per_path"], ["KILLED_BY_OVERWRITE"])

    def test_distinct_receiver_reset_does_not_kill(self):
        result = self.check([[e("nonlinear"), e("reset", "scratch"), e("read")]])
        self.assertEqual(result["per_path"], ["LIVE"])
        self.assertFalse(result["source_same_receiver_proven"])

    def test_unproven_alias_abstains_even_if_names_match(self):
        result = self.check([[e("nonlinear"), e("read")]], aliases=False)
        self.assertEqual(result["synthetic_reaching_definition"], "UNKNOWN")
        self.assertEqual(result["per_path"], ["LIVE"])

    def test_incomplete_cfg_abstains_even_if_path_live(self):
        result = self.check([[e("nonlinear"), e("read")]], complete=False)
        self.assertEqual(result["synthetic_reaching_definition"], "UNKNOWN")

    def test_mixed_branch_contains_uninitialized_read(self):
        result = self.check([[e("nonlinear"), e("read")], [e("read")]])
        self.assertEqual(result["per_path"], ["LIVE", "NO_QUALIFIED_REACHING_DEF"])
        self.assertEqual(result["synthetic_reaching_definition"],
                         "MIXED_OR_MISSING_DEFINITION_SYNTHETIC")

    def test_conditional_all_killed_and_multiple_paths(self):
        result = self.check([[e("nonlinear"), e("reset"), e("read")],
                             [e("nonlinear"), e("other_write"), e("read")]])
        self.assertEqual(result["synthetic_reaching_definition"],
                         "KILLED_ON_ALL_ENUMERATED_PATHS_SYNTHETIC")

    def test_wrong_object_read_is_not_source_proof(self):
        result = self.check([[e("nonlinear"), e("read", "selectedBall")]])
        self.assertEqual(result["per_path"], ["NO_QUALIFIED_REACHING_DEF"])
        self.assertIs(result["selected_ball_launch_transfer_verified"], False)

    def test_reaching_path_rejects_unbounded_or_malformed(self):
        invalid = [[], [e("read")]*65, [e("nonlinear")],
                   [e("read"), e("read")], [{"op": "commit", "receiver": "calcA"}],
                   [{"op": "read", "receiver": "r 3"}],
                   [{"op": "read", "receiver": "calcA", "address": "private"}]]
        for path in invalid:
            with self.subTest(path=path[:2]), self.assertRaises(audit.Abstain):
                self.check([path])
        with self.assertRaises(audit.Abstain):
            self.check([])
        with self.assertRaises(audit.Abstain):
            self.check([[e("read")]]*17)
        with self.assertRaises(audit.Abstain):
            audit.classify_synthetic_reaching_paths([[e("read")]],
                                                   complete_cfg=1,
                                                   receiver_alias_proven=True)

    def test_case1_f32_half_bijection_in_safe_range(self):
        for i in range(1001):
            x = struct.unpack(">f", struct.pack(">f", i / 1000))[0]
            case = audit.case1_aux_f32(x)
            self.assertTrue(case["roundtrip_binary32_exact"], x)
            self.assertFalse(case["f28_is_accepted_shot_power"])
            self.assertFalse(case["aux_is_selected_ball_launch_scalar"])

    def test_case1_f32_subnormal_halving_is_not_invertible(self):
        result = audit.case1_aux_f32(2**-149)
        self.assertFalse(result["roundtrip_binary32_exact"])
        self.assertTrue(result["underflow_or_rounding_loss"])

    def test_case1_rejects_nonfinite_and_outside_f32(self):
        for v in (float("nan"), float("inf"), float("-inf"), 1e300, "0.5", True):
            with self.subTest(value=str(v)), self.assertRaises(audit.Abstain):
                audit.case1_aux_f32(v)

    def test_cli_ledger_is_allowlisted_json_and_not_training(self):
        process = subprocess.run([sys.executable, "-I", str(SCRIPT)],
                                 capture_output=True, text=True, check=True)
        record = json.loads(process.stdout)
        self.assertEqual(record["kind"], audit.KIND)
        self.assertFalse(record["actual_accepted_power_verified"])
        self.assertFalse(record["training_approved"])
        self.assertNotIn("C:\\", process.stdout)
        self.assertNotIn("/home/", process.stdout)

    def test_cli_synthetic_controls_remain_unverified(self):
        process = subprocess.run([sys.executable, "-I", str(SCRIPT),
                                  "--stage=synthetic-controls"],
                                 capture_output=True, text=True, check=True)
        record = json.loads(process.stdout)
        self.assertEqual(record["controls"]["reset_before_read"], "KILLED_BY_RESET")
        self.assertEqual(record["controls"]["before_reset"], "LIVE")
        self.assertEqual(record["controls"]["different_receiver"], "LIVE")
        self.assertEqual(record["controls"]["branch_bypass"], "NO_QUALIFIED_REACHING_DEF")
        self.assertFalse(record["actual_accepted_power_verified"])


if __name__ == "__main__":
    unittest.main()
