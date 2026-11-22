"""Synthetic-only Ball/KCol result-producer and ball-vector reader audit."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/"scripts"
TESTS = ROOT/"tests"
sys.path.insert(0, str(SCRIPTS))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load("p0_ball_result_provenance",
         SCRIPTS/"p0_ball_kcol_result_provenance_private.py")
prior = load("p0_ball_material_fixture",
             TESTS/"test_p0_ball_kcol_material_branch_private.py")


class BallResultProvenanceTests(unittest.TestCase):
    def test_source_gates_and_seven_bounded_windows(self):
        words, read = prior.fixture()
        output = m.inspect(read)
        self.assertTrue(output["earlier_exact_material_and_call_gates_passed"])
        self.assertEqual(len(output["windows"]), 7)
        self.assertEqual(output["total_native_source_words"], 592)
        self.assertLessEqual(output["total_native_source_words"],
                             m.MAX_SOURCE_WORDS)

    def test_detail_is_local_only_and_bounded(self):
        words, read = prior.fixture()
        compact = m.inspect(read)
        verbose = m.inspect(read, detail=True)
        self.assertTrue(all("native_code_lines_local_only" not in x
                            for x in compact["windows"]))
        self.assertTrue(all(
            len(x["native_code_lines_local_only"]) == x["instruction_count"]
            for x in verbose["windows"]))
        self.assertEqual(
            sum(x["instruction_count"] for x in verbose["windows"]), 592)

    def test_no_tree_or_velocity_promotion(self):
        words, read = prior.fixture()
        output = m.inspect(read)
        self.assertFalse(output["classification_13_tree_event_proven"])
        self.assertFalse(output["ball_velocity_field_semantics_proven"])
        self.assertFalse(output["tree_hitbox_geometry_verified"])
        self.assertFalse(output["training_approved"])
        self.assertTrue(all(
            not x["classification_producer_identified"] and
            not x["ball_vector_receiver_verified"]
            for x in output["windows"]))

    def test_wrong_original_material_anchor_abstains(self):
        words, read = prior.fixture()
        site = m.units.UNITS["Ball"][0] + 0x0B84
        words[site] = 0
        with self.assertRaises(ValueError):
            m.inspect(read)

    def test_window_source_bounds_fail_closed(self):
        words, read = prior.fixture()
        original = m.WINDOWS
        try:
            m.WINDOWS = (
                ("bad", "GolfKCol", 0x2091, 0x2099),
            )
            with self.assertRaises(ValueError):
                m.inspect(read)
        finally:
            m.WINDOWS = original

    def test_native_word_limit_fail_closed(self):
        words, read = prior.fixture()
        original = m.MAX_SOURCE_WORDS
        try:
            m.MAX_SOURCE_WORDS = 1
            with self.assertRaises(ValueError):
                m.inspect(read)
        finally:
            m.MAX_SOURCE_WORDS = original

    def test_original_query_entry_and_prism_accessor_are_included(self):
        regions = {x[0]:x[1:] for x in m.WINDOWS}
        self.assertEqual(regions["kcol_main_query_output"],
                         ("GolfKCol", 0x0000, 0x0120))
        self.assertEqual(regions["kcol_prism_flag_accessors"],
                         ("GolfKCol", 0x0194, 0x01D8))
        self.assertEqual(regions["ball_vector_reader_writer_context"],
                         ("Ball", 0x34F0, 0x35CC))


if __name__ == "__main__":
    unittest.main()
