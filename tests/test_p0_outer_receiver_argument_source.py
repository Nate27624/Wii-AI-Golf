"""Fabricated-only, native-free upstream source argument tests for P0 #240."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_p0_outer_receiver_argument_source as source

NOP = 0x60000000

def branch(pc, dest, link=True):
    return (18 << 26) | ((dest - pc) & 0x03FFFFFC) | int(link)

def mr(dst, src):
    return (31 << 26) | (src << 21) | (dst << 16) | (src << 11) | (444 << 1)

def lwz_r3(base=31):
    return (32 << 26) | (3 << 21) | (base << 16) | 0x20

def source_map():
    words = {}
    for _, start, target, *_ in source.SOURCES:
        words[start + 0x18] = mr(3, 31)
        words[start + 0x20] = branch(start + 0x20, target)
    return words

def analyze(words):
    return source.inspect_upstream(lambda pc: words.get(pc, NOP))

class UpstreamSourceTests(unittest.TestCase):
    def test_two_exact_source_calls_and_mr_candidates(self):
        rows = analyze(source_map())["outer_call_windows"]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["exact_direct_calls_found_within_window"], 1)
            self.assertEqual(row["candidate_callsite_source_entry_offset"], "+0x020")
            self.assertEqual(row["nearest_supported_r3_definition_class"],
                             "mr_r3_from_r31")
            self.assertEqual(row["nearest_r3_definition_distance_words"], 2)
            self.assertEqual(row["status"], "SYNTAX_ONLY_NEEDS_CFG_AND_RUNTIME")
            self.assertFalse(row["runtime_receiver_object_verified"])

    def test_source_labels_are_not_runtime_association(self):
        r = analyze(source_map())
        for key in ("source_byte_provenance_authenticated_by_this_helper",
                    "source_global_or_selected_ball_receiver_identified",
                    "cache_writer_executed_in_captured_shot_verified",
                    "rendered_ball_identity_or_physics_verified",
                    "training_approved", "allowed_to_publish"):
            self.assertFalse(r[key])
        self.assertTrue(r["source_reader_requires_independent_RSPE01_rev1_SHA_gate"])
        self.assertTrue(r["window_absence_is_not_proof_of_no_other_call"])

    def test_missing_call_abstains_without_claiming_absence(self):
        d = source_map()
        first = source.SOURCES[0][1]
        del d[first + 0x20]
        row = analyze(d)["outer_call_windows"][0]
        self.assertEqual(row["status"], "NO_EXACT_DIRECT_CALL_IN_BOUNDED_WINDOW")
        self.assertIsNone(row["nearest_supported_r3_definition_class"])
        self.assertTrue(row["bounded_syntactic_candidate_only"])

    def test_multiple_exact_calls_abstain(self):
        d = source_map()
        first, target = source.SOURCES[0][1:3]
        d[first + 0x40] = branch(first + 0x40, target)
        row = analyze(d)["outer_call_windows"][0]
        self.assertEqual(row["status"], "MULTIPLE_DIRECT_CALLS_ABSTAIN")
        self.assertEqual(row["exact_direct_calls_found_within_window"], 2)
        self.assertIsNone(row["candidate_callsite_source_entry_offset"])

    def test_unlinked_branch_to_target_does_not_count_as_call(self):
        d = source_map()
        entry, target = source.SOURCES[0][1:3]
        d[entry + 0x20] = branch(entry + 0x20, target, link=False)
        self.assertEqual(analyze(d)["outer_call_windows"][0]["exact_direct_calls_found_within_window"], 0)

    def test_wrong_target_does_not_count(self):
        d = source_map()
        entry, target = source.SOURCES[0][1:3]
        d[entry + 0x20] = branch(entry + 0x20, target + 4)
        self.assertEqual(analyze(d)["outer_call_windows"][0]["exact_direct_calls_found_within_window"], 0)

    def test_conditional_branch_hazard_near_call(self):
        d = source_map()
        entry = source.SOURCES[0][1]
        d[entry + 0x1C] = 16 << 26
        row = analyze(d)["outer_call_windows"][0]
        self.assertTrue(row["prior_control_transfer_in_window"])
        self.assertTrue(row["control_transfer_after_nearest_definition"])
        self.assertEqual(row["status"], "SYNTAX_ONLY_WITH_CONTROL_FLOW_HAZARD")

    def test_indirect_branch_hazard_before_r3_definition(self):
        d = source_map()
        entry = source.SOURCES[0][1]
        d[entry + 4] = (19 << 26) | (528 << 1)
        row = analyze(d)["outer_call_windows"][0]
        self.assertTrue(row["prior_control_transfer_in_window"])
        self.assertFalse(row["control_transfer_after_nearest_definition"])

    def test_intervening_linked_call_could_clobber_receiver(self):
        d = source_map()
        entry = source.SOURCES[0][1]
        d[entry + 0x1C] = branch(entry + 0x1C, entry + 0x60)
        row = analyze(d)["outer_call_windows"][0]
        self.assertEqual(row["status"], "SYNTAX_ONLY_WITH_CONTROL_FLOW_HAZARD")

    def test_closer_load_takes_precedence_over_mr(self):
        d = source_map()
        entry = source.SOURCES[0][1]
        d[entry + 0x1C] = lwz_r3(base=30)
        row = analyze(d)["outer_call_windows"][0]
        self.assertEqual(row["nearest_supported_r3_definition_class"], "gpr_load_r3_from_r30")
        self.assertEqual(row["nearest_r3_definition_distance_words"], 1)

    def test_unsupported_xform_def_is_explicit_uncertainty(self):
        d = source_map()
        entry = source.SOURCES[0][1]
        d[entry + 0x1C] = (31 << 26) | (3 << 21) | (5 << 16) | (6 << 11) | (266 << 1)
        row = analyze(d)["outer_call_windows"][0]
        self.assertTrue(row["unsupported_possible_r3_write_seen"])
        self.assertEqual(row["status"], "SYNTAX_ONLY_WITH_CONTROL_FLOW_HAZARD")

    def test_no_r3_definition_abstains(self):
        d = source_map()
        entry = source.SOURCES[0][1]
        del d[entry + 0x18]
        row = analyze(d)["outer_call_windows"][0]
        self.assertEqual(row["status"], "NO_SUPPORTED_NEAR_CALL_R3_SOURCE_ABSTAIN")

    def test_invalid_word_or_callback_rejected(self):
        d = source_map()
        entry = source.SOURCES[0][1]
        for word in (None, -1, 2**32, 1.5, True):
            with self.subTest(word=word):
                d[entry] = word
                with self.assertRaises(ValueError):
                    analyze(d)
        with self.assertRaises(ValueError):
            source.inspect_upstream(None)

    def test_abs_and_negative_branches_do_not_invent_call(self):
        self.assertEqual(source._branch(0x8029B43C, branch(0x8029B43C, 0x80299ACC)),
                         (0x80299ACC, True))
        # Absolute branch to small numeric target; not relative to PC.
        absolute = (18 << 26) | 0x1002 | 1
        self.assertEqual(source._branch(0x8029B43C, absolute), (0x1000, True))

    def test_output_is_sanitized_no_instruction_address_or_raw_word(self):
        r = analyze(source_map())
        payload = json.dumps(r)
        for address in ("0x8029B43C", "0x80299ACC", "0x8029A204", "0x80299C20",
                        str(mr(3,31)), "heap_address", "source_words"):
            self.assertNotIn(address, payload)

if __name__ == "__main__":
    unittest.main()
