"""Synthetic S002 controls; these never establish native game-time execution."""
import importlib.util
import inspect
from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch

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


    def test_archive_discovery_fails_closed_on_zero_or_multiple(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Wii-AI-Golf-Data"
            captures = root / "captures"
            captures.mkdir(parents=True)
            with patch.object(audit.original.src.selected, "DATA_ROOT", root):
                with self.assertRaises(ValueError):
                    audit.discover_approved_archive()
                for index in (1, 2):
                    candidate = captures / ("archive" + str(index))
                    candidate.mkdir()
                    marker = candidate / "manifest-PRIVATE.json"
                    marker.write_text(json.dumps({
                        "kind": "p0-private-numbered-capture-inventory",
                        "capture_count": 7,
                        "capture_numbers": list(range(1, 8)),
                        "training_approved": False,
                    }), encoding="utf-8")
                    if index == 1:
                        self.assertEqual(audit.discover_approved_archive(), candidate)
                    else:
                        with self.assertRaises(ValueError):
                            audit.discover_approved_archive()

    def test_archive_discovery_rejects_unqualified_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Wii-AI-Golf-Data"
            captures = root / "captures"
            candidate = captures / "candidate"
            candidate.mkdir(parents=True)
            (candidate / "manifest-PRIVATE.json").write_text(json.dumps({
                "kind": "p0-private-numbered-capture-inventory",
                "capture_count": 7,
                "capture_numbers": list(range(1, 8)),
                "training_approved": True,
            }), encoding="utf-8")
            with patch.object(audit.original.src.selected, "DATA_ROOT", root):
                with self.assertRaises(ValueError):
                    audit.discover_approved_archive()


    def test_integrator_windows_within_published_function_bounds(self):
        published = {
            "integrator_receiver_prefix": (0x80299890, 0x80299ACC),
            "global_processing_call": (0x80299C70, 0x8029A038),
            "selected_sim_entry": (0x8029B554, 0x8029B57C),
        }
        for name, (lo, hi) in audit.WINDOWS.items():
            self.assertGreaterEqual(lo, published[name][0])
            self.assertLessEqual(hi, published[name][1])
            self.assertGreater(hi, lo)
            self.assertEqual((hi-lo) % 4, 0)

    def test_symbolic_ppc_operand_decoding(self):
        # lwz r3, +0x6B4(r3) and stfs f7, +0x78(r29) are
        # synthetic encodings, never native source attestations.
        lwz = (32 << 26) | (3 << 21) | (3 << 16) | 0x6B4
        w = audit.decode_symbolic(0x8029B554, lwz)
        self.assertEqual((w["kind"], w["register"], w["base"], w["offset"]),
                         ("lwz", 3, 3, 0x6B4))
        stfs = (52 << 26) | (7 << 21) | (29 << 16) | 0x78
        t = audit.decode_symbolic(0x8029A4BC, stfs)
        self.assertEqual((t["kind"], t["base"], t["offset"]), ("stfs", 29, 0x78))
        self.assertNotIn("word", t)

    def test_symbolic_ppc_conditional_branch(self):
        # bc BO=4 BI=2, branch +0x5c.
        word = (16 << 26) | (4 << 21) | (2 << 16) | 0x5C
        row = audit.decode_symbolic(0x80299B74, word)
        self.assertEqual(row["kind"], "bc")
        self.assertEqual(row["target"], "0x80299BD0")
        self.assertEqual((row["bo"], row["bi"], row["lk"]), (4, 2, False))
        with self.assertRaises(ValueError):
            audit.decode_symbolic(0, -1)


    def test_ppc_mr_r30_r4_exact_alias(self):
        # or r30,r4,r4; synthetically construct the alias, no native bytes.
        good = (31 << 26) | (4 << 21) | (30 << 16) | (4 << 11) | (444 << 1)
        self.assertTrue(audit.is_mr(good, dest=30, source=4))
        for altered in (good | 1, good ^ (1 << 21),
                        good ^ (1 << 16), good ^ (1 << 11)):
            self.assertFalse(audit.is_mr(altered, dest=30, source=4))

    def test_mode_operand_candidates_are_cautiously_classified(self):
        lbz = (34 << 26) | (5 << 21) | (30 << 16) | 0x138
        c = audit.mode_reference(0x80299900, lbz)
        self.assertEqual((c["base"], c["offset"]), (30, 0x138))
        self.assertIn("candidate", c["role"])
        cmpwi = (11 << 26) | (30 << 16) | 3
        self.assertEqual(audit.mode_reference(0x80299904, cmpwi)
                         ["comparison_register"], 30)
        neutral = (34 << 26) | (5 << 21) | (29 << 16) | 0x138
        self.assertIsNone(audit.mode_reference(0x80299908, neutral))

    def test_mode_source_body_bounded_to_published_function(self):
        self.assertEqual(audit.MODE_WINDOW, (0x80299890, 0x80299ACC))
        self.assertTrue(all(audit.MODE_WINDOW[0] <= pc < audit.MODE_WINDOW[1]
                            for pc, _ in audit.MODE_CALLS))
        self.assertEqual(audit.MAX_MODE_REFERENCES, 12)


    def test_native_reader_uses_sha_qualified_per_phase_folders(self):
        # Real original._check_archive returns {capture_number: directory},
        # not the parent inventory directory.
        for function in (audit.verify_original_calls,
                         audit.source_window_report, audit.mode_source_report):
            source = inspect.getsource(function)
            self.assertIn("folders = original._check_archive(archive)", source)
            self.assertIn("folders[phase]", source)
            self.assertIn("original._check_archive(archive)", source)
        self.assertEqual(audit.PHASES, (1, 5, 7))



    def test_alternative_initializer_source_windows_are_complete_and_disjoint(self):
        self.assertEqual(
            audit.ALT_CALLER_FUNCTIONS["small_initializer_caller"],
            (0x8029A1D0, 0x8029A204))
        self.assertEqual(
            audit.ALT_CALLER_FUNCTIONS["initializer_and_state_copy_caller"],
            (0x8029A204, 0x8029A2D0))
        self.assertEqual(len(audit.ALT_CALLS), 3)
        for pc, target in audit.ALT_CALLS:
            self.assertTrue(any(lo <= pc < hi
                                for lo, hi in audit.ALT_CALLER_FUNCTIONS.values()))
            instruction = (18 << 26) | ((target - pc) & 0x03FFFFFC) | 1
            self.assertEqual(audit.direct_bl_target(pc, instruction), target)
            self.assertIsNone(audit.direct_bl_target(pc, instruction & ~1))
        source = inspect.getsource(audit.alternative_initializer_report)
        self.assertIn("folders = original._check_archive(archive)", source)
        self.assertIn("folders[phase]", source)
        self.assertIn("receiver_must_definition", source)


if __name__ == "__main__":
    unittest.main()
