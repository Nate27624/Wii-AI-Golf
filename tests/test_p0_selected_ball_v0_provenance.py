"""Synthetic S002 controls; these never establish native game-time execution."""
import importlib.util
from pathlib import Path
import unittest

PATH = (Path(__file__).resolve().parents[1] / "scripts" /
        "audit_p0_selected_ball_v0_provenance_private.py")
spec = importlib.util.spec_from_file_location("s002_v0", PATH)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class SourceHandoffControls(unittest.TestCase):
    def test_source_bl_and_malformed_branch_negative_controls(self):
        for pc, target, label in audit.CALLS:
            word = (18 << 26) | ((target - pc) & 0x03FFFFFC) | 1
            self.assertEqual(audit.direct_bl_target(pc, word), target)
            self.assertIsNone(audit.direct_bl_target(pc, word & ~1))
            self.assertIsNone(audit.direct_bl_target(pc, word | 2))
            self.assertIsNone(audit.direct_bl_target(pc, 0x4E800421))
        self.assertIsNone(audit.direct_bl_target(0, -1))

    def test_intermediate_precedes_late_candidate_copy(self):
        row = audit.symbolic_handoff(state3=True, flag1=True,
             intermediate_returns=True, incoming_is_selected=True)
        steps = row["steps"]
        self.assertLess(steps.index("call_intermediate_global_processing"),
                        steps.index("candidate_copy_incoming_to_global"))
        self.assertFalse(row["selected_ball_v0_verified"])
        self.assertFalse(row["runtime_execution_verified"])

    def test_state3_false_removes_late_copy(self):
        row = audit.symbolic_handoff(state3=False, flag1=True,
             intermediate_returns=True, incoming_is_selected=None)
        self.assertNotIn("candidate_copy_incoming_to_global", row["steps"])

    def test_flag_unknown_multiplier(self):
        row = audit.symbolic_handoff(state3=True, flag1=False,
             intermediate_returns=True, incoming_is_selected=True)
        self.assertEqual(row["scalar_0x8c_input"], "unknown_optional_multiplier")

    def test_intermediate_nonreturn_or_unknown_abstains(self):
        for returned in (False, None):
            row = audit.symbolic_handoff(state3=True, flag1=True,
                 intermediate_returns=returned, incoming_is_selected=True)
            self.assertNotIn("candidate_copy_incoming_to_global", row["steps"])

    def test_selected_ball_identity_and_training_fail_closed(self):
        for identity in (True, False, None):
            row = audit.symbolic_handoff(state3=True, flag1=None,
                 intermediate_returns=True, incoming_is_selected=identity)
            self.assertFalse(row["selected_ball_v0_verified"])
            self.assertFalse(row["training_approved"])

    def test_invalid_branch_predicate_rejected(self):
        with self.assertRaises(ValueError):
            audit.symbolic_handoff(state3=1, flag1=None,
                 intermediate_returns=None, incoming_is_selected=None)

if __name__ == "__main__":
    unittest.main()
