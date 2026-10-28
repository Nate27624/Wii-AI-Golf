"""Synthetic-only source-written selected player-state B0-B3 checks."""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import audit_golf_two_bank_roster_private as roster
import audit_selected_player_state_four_phase_private as state
from test_selected_ball_start_link_private import fixture


def create():
    words, refs = fixture()
    rec = refs["pm"] + 4
    words[rec + 0x24] = 1
    for lipc, liword, stpc, stword in state.STATE_WRITES:
        words[lipc] = liword
        words[stpc] = stword
    return words, refs


def run_one(words, header=b"RSPE01\x00\x01"):
    def rd(pc):
        if pc in words:
            return words[pc]
        if (roster.PLAYER_MANAGER_CODE[0] <= pc < roster.PLAYER_MANAGER_CODE[1]
                or 0x8029E62C <= pc < 0x802A2210):
            return 0
        raise ValueError("Undefined synthetic memory word")
    return state.read_selected_state(rd, header)


def four(state_words=(1, 1, 1, 1)):
    out = []
    for w in state_words:
        words, refs = create()
        words[refs["pm"] + 4 + 0x24] = w
        out.append(run_one(words))
    return out


class SelectedPlayerStateFourPhaseTests(unittest.TestCase):
    def test_reads_exact_source_witness_and_source_selected_word(self):
        s = four()[0]
        self.assertEqual(s["state"], 1)
        self.assertEqual(s["selected_index"], 0)
        self.assertEqual(s["writer_instruction_sites_checked"], 5)

    def test_state_is_stable_during_no_shot_and_still_not_verified(self):
        r = state.summarize(four(), aim_visibly_moved=True,
                            operator_same_session=True)
        self.assertTrue(r["candidate_word_stable_during_no_shot"])
        self.assertEqual(r["candidate_word_distinct_value_count"], 1)
        self.assertEqual(r["candidate_word_changed_across_transitions"],
                         [False, False, False])
        self.assertEqual(r["candidate_word_matches_one_of_five_writer_literals_per_phase"],
                         [True, True, True, True])
        self.assertFalse(r["contact_or_landing_verified"])
        self.assertFalse(r["approved_for_model_training"])

    def test_aim_only_change_is_reported_not_promoted(self):
        r = state.summarize(four((1, 1, 2, 1)),
                            aim_visibly_moved=True,
                            operator_same_session=True)
        self.assertEqual(r["candidate_word_changed_across_transitions"],
                         [False, True, True])
        self.assertFalse(r["candidate_word_stable_during_no_shot"])
        self.assertFalse(r["gameplay_state_verified"])

    def test_zero_is_separate_from_known_writer_literals(self):
        r = state.summarize(four((0, 0, 0, 0)))
        self.assertEqual(r["candidate_word_is_zero_per_phase"],
                         [True] * 4)
        self.assertEqual(r["candidate_word_matches_one_of_five_writer_literals_per_phase"],
                         [False] * 4)
        self.assertFalse(r["writer_literal_set_exhaustive_verified"])

    def test_unknown_state_is_not_clamped_or_named(self):
        r = state.summarize(four((0xDEADBEEF,)*4))
        self.assertEqual(r["candidate_word_distinct_value_count"], 1)
        self.assertEqual(r["candidate_word_matches_one_of_five_writer_literals_per_phase"],
                         [False]*4)
        self.assertNotIn("3735928559", json.dumps(r))
        self.assertNotIn("0xdeadbeef", json.dumps(r).lower())

    def test_source_writer_modification_fails_closed(self):
        words, _ = create()
        words[0x8029F1C0] = 0
        with self.assertRaisesRegex(ValueError, "writer"):
            run_one(words)

    def test_header_and_selected_actor_mismatch_fail_closed(self):
        words, _ = create()
        with self.assertRaises(ValueError):
            run_one(words, b"RSPE01\x00\x00")
        words, refs = create()
        words[refs["pm"] + 0x334] = 0x9000FFFF
        with self.assertRaises(ValueError):
            run_one(words)

    def test_no_raw_words_heap_pointer_or_paths_in_summary(self):
        r = state.summarize(four((0x12345678,)*4))
        s = json.dumps(r)
        for secret in ("305419896", "0x12345678",
                       "record_pointer", "0x900", "mem1.raw"):
            self.assertNotIn(secret, s)
        self.assertFalse(r["allowed_to_publish"])

    def test_source_record_identity_change_cannot_be_stable(self):
        rows = four()
        rows[2]["record_pointer"] += 0xCC
        r = state.summarize(rows, aim_visibly_moved=True,
                            operator_same_session=True)
        self.assertFalse(r["source_selected_record_unchanged"])
        self.assertFalse(r["candidate_word_stable_during_no_shot"])

    def test_changed_slot_or_hole_refuses_comparison(self):
        rows = four()
        rows[2]["selected_index"] = 1
        with self.assertRaises(ValueError):
            state.summarize(rows)
        rows = four()
        rows[2]["hole"] += 1
        with self.assertRaises(ValueError):
            state.summarize(rows)

    def test_missing_or_wrong_source_site_count_fails_closed(self):
        rows = four()
        rows[3]["writer_instruction_sites_checked"] = 4
        with self.assertRaises(ValueError):
            state.summarize(rows)

    def test_cli_missing_private_session_error_redacts_paths(self):
        with tempfile.TemporaryDirectory() as d:
            err = StringIO()
            with redirect_stderr(err):
                result = state.main(["--private-root", str(Path(d)/"PRIVATE-0x9000")])
            self.assertEqual(result, 1)
            self.assertNotIn(d, err.getvalue())
            self.assertNotIn("PRIVATE-0x9000", err.getvalue())


if __name__ == "__main__":
    unittest.main()
