"""Synthetic-only tests. No private snapshots, Dolphin, controller or RAM."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_seven_source_trajectory_private as audit


def sample(ball=(1,2,3),*,start=(1,2,3),pin=(10,20,30),
           slot=0,hole=1,ball_ref=1234,pin_ref=5555,start_ref=4444):
    t={key:(1,2,3) for key in audit.FIELDS}
    t["ball_nested_plus_0x4c"]=ball
    t["source_current_start"]=start
    t["source_selected_pin"]=pin
    return {
        "selected_index":slot,"hole":hole,
        "refs":{"scene_field":1000,"ball":ball_ref,
                "pin":pin_ref,"start":start_ref},
        "triplets":t,
    }


class SevenTrajectoryTests(unittest.TestCase):
    def test_wedge_three_ordered_phases_changed_without_tee_pin_change(self):
        stages={5:sample(ball=(1,2,3)),6:sample(ball=(1,7,3)),
                7:sample(ball=(8,9,10))}
        r=audit.summarize(stages)
        self.assertEqual(r["wedge_three_phase_selected_ball_distinct_bitpatterns"],3)
        edges=r["within_shot_transitions"]
        self.assertEqual(len(edges),3)
        self.assertTrue(all(x["ball_candidate_changed_with_stable_start_and_pin"]
                            for x in edges))
        self.assertFalse(r["true_world_ball_xyz_verified"])
        self.assertFalse(r["training_approved"])
        self.assertNotIn('"8, 9, 10"',json.dumps(r))

    def test_pin_coordinate_change_confounds_ball(self):
        a=sample()
        b=sample(ball=(4,5,6),pin=(99,20,30))
        r=audit.compare_transition("wedge",5,6,a,b)
        self.assertFalse(r["ball_candidate_changed_with_stable_start_and_pin"])
        self.assertTrue(r["ball_candidate_changed_but_pin_or_pointer_confounded"])

    def test_different_pin_pointer_confounds_even_if_coordinates_match(self):
        r=audit.compare_transition("wedge",5,6,sample(),
                                  sample(ball=(4,5,6),pin_ref=9999))
        self.assertTrue(r["ball_candidate_changed_but_pin_or_pointer_confounded"])
        self.assertFalse(r["ball_candidate_changed_with_stable_start_and_pin"])

    def test_driver_wedge_not_compared_directly(self):
        p={1:sample(),2:sample(ball=(4,5,6)),
           5:sample(),6:sample(ball=(7,8,9)),7:sample(ball=(9,9,9))}
        r=audit.summarize(p)
        self.assertEqual(len(r["within_shot_transitions"]),4)
        names=[x["name"] for x in r["within_shot_transitions"]]
        self.assertEqual(names,[e[0] for e in audit.TRANSITIONS])
        self.assertTrue(r["different_club_and_A_controls_not_causally_compared"])

    def test_selected_actor_or_hole_change_aborts_pair_instead_of_claim(self):
        for kw in ({"slot":1},{"hole":2}):
            r=audit.compare_transition("wedge",5,6,sample(),
                                       sample(ball=(7,8,9),**kw))
            self.assertTrue(r["within_shot_candidate_comparison_refused"])
            self.assertFalse(r["ball_motion_proven"])
            self.assertNotIn("different_component_counts_of_three",r)

    def test_source_file_bank_lengths_map_without_assuming_extension(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"5.1.raw").write_bytes(b"\x00"*0)
            (root/"5.2.raw").write_bytes(b"\x00"*0)
            with self.assertRaisesRegex(ValueError,"wrong sized"):
                audit._phase_banks(root,5)

    def test_missing_required_phase_files_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"missing complete"):
                audit.run_local(Path(td))

    def test_analyzes_current_scene_source_not_arbitrary_words(self):
        # Gate check must be mocked at the reader boundary: tiny byte strings
        # are invalid native banks and would stop before our source validator.
        with patch.object(audit.ROSTER,"TwoBankReader",return_value=object()):
            with patch.object(audit.source,"_sample",
                              side_effect=ValueError("Rev1 source gate failed")):
                with self.assertRaisesRegex(ValueError,"Rev1 source gate failed"):
                    audit._source_sample(b"",b"")

    def test_python_isolated_cli_imports_real_source_helpers(self):
        with tempfile.TemporaryDirectory() as td:
            cmd=[sys.executable,"-I",str(ROOT/"scripts"/
                 "audit_p0_seven_source_trajectory_private.py"),"--help"]
            p=subprocess.run(cmd,cwd=td,capture_output=True,
                             text=True,timeout=15,check=False)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("--dump-directory",p.stdout)
        self.assertNotIn("ModuleNotFoundError",p.stderr)


if __name__=="__main__":
    unittest.main()
