"""Synthetic-only S002 SequenceMgr vs Config score hypotheses. No game RAM."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_seven_sequence_scores_private as audit


def state(scores=None):
    return {
        "slot": 0, "hole": 2,
        "owner": (1, 2, 3, 4, 5, 6, 7),
        "selectors": (2, 3, 4),
        "pin": (11, 12, 13),
        "tee": (14, 15, 16),
        "ball": (1, 2, 3),
        "seq_pointer": 0x90001000 if scores is not None else 0,
        "seq_sport": 2 if scores is not None else None,
        "seq_training_game": 1 if scores is not None else None,
        "seq_sequence": 6 if scores is not None else None,
        "seq_golf_mode": 0 if scores is not None else None,
        "seq_scores": tuple([0] * 36) if scores is True else scores,
    }


def cohort(scores=True):
    d = {n: state(scores) for n in audit.PHASES}
    d[2]["ball"] = (3, 4, 5)
    d[6]["ball"] = (6, 7, 8)
    d[7]["ball"] = (9, 10, 11)
    return d


class SequenceTests(unittest.TestCase):
    def test_stable_table_is_not_a_verified_reward(self):
        r = audit.summarize(cohort())
        self.assertEqual([row["transition"] for row in r["comparison_edges"]],
                         ["1_to_2", "5_to_6", "6_to_7", "5_to_7"])
        self.assertTrue(all(row["sequence_manager_score_table_changed_words_of_36"] == 0
                            for row in r["comparison_edges"]))
        self.assertFalse(r["mode4_training_scoring_use_verified"])
        self.assertFalse(r["training_approved"])

    def test_selected_hole_player_cell_uses_hole_major_order(self):
        d = cohort()
        z = list(d[7]["seq_scores"])
        z[2 * 4 + 0] = 12
        d[7]["seq_scores"] = tuple(z)
        a = audit.summarize(d)["comparison_edges"]
        self.assertEqual(a[2]["sequence_manager_score_changed_count_by_hole"],
                         [0, 0, 1, 0, 0, 0, 0, 0, 0])
        self.assertTrue(a[2]["source_selected_hole_player_cell_changed"])
        self.assertEqual(a[2]["sequence_manager_score_table_changed_words_of_36"], 1)

    def test_other_hole_is_not_selected_cell(self):
        d = cohort()
        z = list(d[2]["seq_scores"])
        z[5*4 + 1] = 1
        d[2]["seq_scores"] = tuple(z)
        a = audit.summarize(d)["comparison_edges"][0]
        self.assertEqual(a["sequence_manager_score_changed_count_by_hole"][5], 1)
        self.assertFalse(a["source_selected_hole_player_cell_changed"])
        self.assertEqual(a["other_score_cells_changed"], 1)

    def test_inactive_singleton_does_not_fabricate_zero_changes(self):
        d = cohort(scores=None)
        a = audit.summarize(d)["comparison_edges"]
        self.assertTrue(all(not r["sequence_manager_present_both"] for r in a))
        self.assertTrue(all(r["sequence_manager_score_table_changed_words_of_36"] is None
                            for r in a))
        self.assertTrue(all(r["source_selected_hole_player_cell_changed"] is None
                            for r in a))

    def test_sport_not_golf_is_not_active_golf_claim(self):
        d = cohort()
        for p in d.values():
            p["seq_sport"] = 1
        a = audit.summarize(d)["comparison_edges"]
        self.assertTrue(all(not r["sequence_manager_sport_golf_both"] for r in a))
        self.assertFalse(a[0]["source_selected_hole_player_cell_changed"])

    def test_sequence_change_is_not_score_change(self):
        d = cohort()
        d[7]["seq_sequence"] = 7
        a = audit.summarize(d)["comparison_edges"][2]
        self.assertTrue(a["sequence_manager_sequence_changed"])
        self.assertEqual(a["sequence_manager_score_table_changed_words_of_36"], 0)

    def test_owner_confounds_refused(self):
        for key, new in (
            ("owner", (1, 2, 3, 4, 5, 6, 9)),
            ("slot", 1), ("hole", 3),
            ("selectors", (2, 3, 5)),
            ("pin", (11, 12, 18)),
            ("tee", (14, 18, 16)),
            ("seq_pointer", 0x90009000),
        ):
            d = cohort()
            d[6][key] = new
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit.summarize(d)

    def test_bad_score_shapes_and_words_refused(self):
        for bad in ((0,)*35, (0,)*37, (-1,)*36, (2**32,)*36, ("0",)*36):
            d = cohort()
            d[5]["seq_scores"] = bad
            with self.subTest(length=len(bad)), self.assertRaises(ValueError):
                audit.summarize(d)

    def test_source_reader_sport_game_and_score_array_offsets(self):
        cfg, field, pm, seq, ball, pin, start = [
            0x90001000, 0x90002000, 0x90003000, 0x90004000,
            0x90005000, 0x90006000, 0x90007000,
        ]
        rec=pm+4
        values={
            audit.roster.GOLF_CONFIG_STATIC:cfg,
            audit.roster.GOLF_FIELD_STATIC:field,
            audit.roster.PLAYER_MANAGER_STATIC_CANDIDATE:pm,
            audit.SEQUENCE_STATIC:seq,
            cfg+0x94:4,cfg+0x98:2,
            rec+0x88:ball, ball+0x4C:ball+0x30,
            field+0x44:pin, field+0x50:start,
            seq+0x04:2,seq+0x08:6,seq+0x0C:1,seq+0xAC:0,
        }
        for i in range(36):
            values[seq+0x14+4*i]=200+i
        class Reader:
            def u32(self,a):
                if a not in values: raise ValueError("unexpected source read")
                return values[a]
        fake={
            "selected_index":0,"hole":2,"pin_obj":pin,"start_obj":start,
            "cfg_bc":1,"cfg_c0":2,"cfg_c4":3,"pin":(7,8,9),
            "triplets":{"source_current_start":(4,5,6),
                        "ball_object_0x030":(1,2,3)}
        }
        with patch.object(audit.seven,"_get",return_value=fake):
            r=audit._sample(Reader())
        self.assertEqual(r["seq_scores"],tuple(range(200,236)))
        self.assertEqual(r["seq_sport"],2)
        self.assertEqual(r["seq_training_game"],1)
        self.assertEqual(r["seq_pointer"],seq)

    def test_source_reader_null_singleton_is_unavailable_not_negative(self):
        cfg,field,pm,ball,pin,start=(0x90001000,0x90002000,0x90003000,
                                     0x90005000,0x90006000,0x90007000)
        values={
            audit.roster.GOLF_CONFIG_STATIC:cfg,
            audit.roster.GOLF_FIELD_STATIC:field,
            audit.roster.PLAYER_MANAGER_STATIC_CANDIDATE:pm,
            audit.SEQUENCE_STATIC:0,
            cfg+0x94:4,cfg+0x98:2,
            pm+4+0x88:ball,ball+0x4C:ball+0x30,
            field+0x44:pin,field+0x50:start,
        }
        class Reader:
            def u32(self,a):return values[a]
        fake={"selected_index":0,"hole":2,"pin_obj":pin,"start_obj":start,
              "cfg_bc":1,"cfg_c0":2,"cfg_c4":3,"pin":(7,8,9),
              "triplets":{"source_current_start":(4,5,6),
                          "ball_object_0x030":(1,2,3)}}
        with patch.object(audit.seven,"_get",return_value=fake):
            s=audit._sample(Reader())
        self.assertIsNone(s["seq_scores"])
        self.assertEqual(s["seq_pointer"],0)

    def test_source_reader_wrong_mode_refused(self):
        class Reader:
            def u32(self,a):return 0
        with patch.object(audit.seven,"_get",return_value={
            "selected_index":0,"hole":0,
        }),self.assertRaises(ValueError):
            audit._sample(Reader())

    def test_source_archive_error_precedes_source_reads(self):
        with patch.object(audit.seven,"_check_archive",
                          side_effect=ValueError("bad sha")):
            with self.assertRaises(ValueError):
                audit.analyze(Path("not-an-archive"))

    def test_output_privacy_and_training_abstention(self):
        s=json.dumps(audit.summarize(cohort()))
        for secret in ('"seq_pointer"', '"seq_scores"', '"ball"', '"owner"',
                       '"pin"', '"tee"', 'private_path', '"hashes"', '0x9000'):
            self.assertNotIn(secret,s)
        self.assertIn('"training_approved": false',s)

    def test_isolated_python_help_from_unrelated_dir(self):
        script=ROOT/"scripts"/"audit_p0_seven_sequence_scores_private.py"
        with tempfile.TemporaryDirectory() as td:
            p=subprocess.run([sys.executable,"-I",str(script),"--help"],
                             cwd=td,capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("--archive",p.stdout)


if __name__=="__main__":
    unittest.main()
