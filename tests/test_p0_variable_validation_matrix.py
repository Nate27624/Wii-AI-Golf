"""S003 offline synthetic-only fail-closed memory matrix tests. No Dolphin/RAM."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location("p0_validation",ROOT/"scripts/p0_variable_validation_matrix.py")
p0=importlib.util.module_from_spec(S)
S.loader.exec_module(p0)

def registry():
    return {"variables":[{"id":key,"priority":"P0","status":"source_candidate"}
                         for key in p0.P]+[{"id":"other","priority":"P1"}]}

def claim(vid,*observations,origin="synthetic"):
    return {"schema_version":1,"origin":origin,
            "variables":{vid:{"observations":list(observations)}}}

def obs(control,response="stable",**changes):
    o=dict(control=control,response=response,run_id="run1",shot_id="shot1",
           scene_id="scene5",hole_id="hole1",selected_actor="ball1",
           observed_actor="ball1",rendered_actor="ball1",
           generation="g1",observed_generation="g1",rendered_generation="g1",
           frame=10,guest_frame_verified=True,physics_step_verified=True,
           game_owned_acceptance=False,contact_verified=False,
           controller_matches_selected=True,controller_connected=True,
           owner_re_resolved=True,selected_vs_global_distinct=True,
           visual_verified=True,units_verified=True,source_typed=True,
           independent_witness=True,phase="PRE",censored=False,used_as_carry=False)
    o.update(changes)
    return o

class P0ValidationTests(unittest.TestCase):
    def row(self,vid,*observations,origin="synthetic"):
        return next(r for r in p0.build_matrix(registry(),claim(vid,*observations,origin=origin))["rows"]
                    if r["variable_id"]==vid)

    def test_exact_25_no_runtime_or_training(self):
        report=p0.build_matrix(registry())
        self.assertEqual(report["p0_count"],25)
        self.assertEqual(report["runtime_verified_count"],0)
        self.assertFalse(report["training_approved"])
        self.assertEqual(len({r["variable_id"] for r in report["rows"]}),25)
        for r in report["rows"]:
            with self.subTest(vid=r["variable_id"]):
                self.assertEqual(r["candidate_status"],"unresolved")
                self.assertTrue(r["missing_witnesses"])
                self.assertFalse(r["runtime_verified"])
                self.assertFalse(r["training_eligible"])
                self.assertFalse(r["ready_for_independent_live_experiment_review"])

    def test_registry_drift_unknown_duplicate_missing_or_status_spoof(self):
        base=registry()
        for mutation in ("missing","duplicate","added","unknown_status"):
            reg=copy.deepcopy(base)
            if mutation=="missing":
                reg["variables"].pop(0)
            elif mutation=="duplicate":
                reg["variables"][1]["id"]=reg["variables"][0]["id"]
            elif mutation=="added":
                reg["variables"].append({"id":"unknown","priority":"P0"})
            else:
                reg["variables"][0]["status"]="runtime_PROVEN"
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                p0.build_matrix(reg)
        base["variables"][0]["status"]="runtime_verified"
        result=p0.build_matrix(base)
        self.assertFalse(result["rows"][0]["runtime_verified"])
        self.assertFalse(result["training_approved"])

    def test_unsafe_evidence_schema_and_raw_values_rejected(self):
        vid="golf.ball.world_xyz"
        bad=[
            {"schema_version":1,"origin":"real_verified","variables":{}},
            {"schema_version":1,"origin":"synthetic","variables":{},"train":True},
            claim("unknown",obs("flight","changed")),
            claim(vid,dict(obs("flight","changed"),raw_memory="forbidden")),
            claim(vid,obs("unknown_control")),
            claim(vid,obs("flight","magic")),
            claim(vid,obs("flight","changed",shot_id="../private")),
            claim(vid,obs("flight","changed",distance_label="Z"*81)),
            claim(vid,obs("aim_left","changed",signed_delta=float("nan"))),
        ]
        for x in bad:
            with self.subTest(payload=str(x)[:50]),self.assertRaises(ValueError):
                p0.build_matrix(registry(),x)

    def test_idle_no_a_and_aim_only_moving_ball_contradicted(self):
        vid="golf.ball.world_xyz"
        for control in ("idle_no_a","aim_only"):
            r=self.row(vid,obs(control,"changed"))
            self.assertIn("negative_control_failed",r["contradictions"])
            self.assertNotIn(control,r["controls_satisfied"])
            self.assertFalse(r["runtime_verified"])
        r=self.row(vid,obs("aim_only","stable",game_owned_acceptance=True))
        self.assertIn("unverified_contact_or_input_control",r["contradictions"])

    def test_wrong_disconnected_controller_and_inactive_player(self):
        vid="golf.player.selected_record.aim_rotation"
        for control,opts in (
            ("wrong_controller",{"controller_matches_selected":False,"response":"changed"}),
            ("disconnected_controller",{"controller_connected":False,"response":"changed"}),
            ("wrong_controller",{"controller_matches_selected":False,"game_owned_acceptance":True}),
            ("disconnected_controller",{"controller_connected":False,"contact_verified":True})):
            opts=opts.copy()
            response=opts.pop("response","stable")
            r=self.row(vid,obs(control,response,**opts))
            self.assertTrue(r["contradictions"])
            self.assertNotIn(control,r["controls_satisfied"])
        r=self.row("golf.ball.world_xyz",obs("inactive_player","changed"))
        self.assertIn("negative_control_failed",r["contradictions"])

    def test_selected_global_and_rendered_identity_not_interchangeable(self):
        vid="golf.ball.world_xyz"
        for opts in ({"observed_actor":"global"},
                     {"rendered_actor":"other"},
                     {"observed_generation":"reused"},
                     {"rendered_generation":"other"},
                     {"hole_id":"different","frame":False}):
            r=self.row(vid,obs("flight","changed",**opts))
            self.assertNotIn("flight",r["controls_satisfied"])
            self.assertIn("actor_or_frame_identity_unverified",r["contradictions"])
        r=self.row(vid,obs("source_global_control",selected_vs_global_distinct=False))
        self.assertIn("negative_control_failed",r["contradictions"])
        self.assertNotIn("source_global_control",r["controls_satisfied"])
        r=self.row(vid,obs("source_global_control"))
        self.assertIn("source_global_control",r["controls_satisfied"])
        self.assertFalse(r["training_eligible"])

    def test_pointer_reuse_and_scene_generation_re_resolve_required(self):
        vid="golf.ball.world_xyz"
        for control in ("pointer_reuse","generation_change"):
            r=self.row(vid,obs(control,"rejected",owner_re_resolved=False))
            self.assertIn("object_generation_not_re_resolved",r["contradictions"])
        r=self.row("golf.main_ptr",obs("scene_change","changed",owner_re_resolved=False))
        self.assertNotIn("scene_change",r["controls_satisfied"])

    def test_cross_shot_join_explicitly_rejected(self):
        vid="golf.ball.world_xyz"
        r=self.row(vid,obs("cross_shot","matched",joined=True))
        self.assertIn("cross_shot_join",r["contradictions"])
        r=self.row(vid,obs("shot_join","rejected",different_shot_id="shot1"))
        self.assertIn("shot_join_unverified",r["contradictions"])
        r=self.row(vid,obs("shot_join","rejected",different_shot_id="shot2"))
        self.assertIn("shot_join",r["controls_satisfied"])

    def test_airborne_start_is_hard_contradiction(self):
        vid="golf.ball_object.current_translation_candidate"
        r=self.row(vid,obs("flight","changed"),obs("airborne_start","matched",
                                                  visual_label="airborne",state="START"))
        self.assertEqual(r["candidate_status"],"contradicted")
        self.assertIn("airborne_start_conflict",r["contradictions"])

    def test_guest_physics_frame_missing_or_unverified(self):
        vid="golf.ball.world_xyz"
        for changes in ({"guest_frame_verified":False},
                        {"physics_step_verified":False},
                        {"frame":"host_timestamp"},
                        {"frame":True}):
            r=self.row(vid,obs("flight","changed",**changes))
            self.assertNotIn("flight",r["controls_satisfied"])
            self.assertIn("actor_or_frame_identity_unverified",r["contradictions"])
        self.assertIn("unverified_guest_physics_frame",
                      self.row(vid,obs("frame_unsynced","rejected"))["contradictions"])

    def test_moving_settled_same_shot_and_monotonic_guest_frame(self):
        vid="golf.ball.world_xyz"
        a=obs("flight","changed",frame=10)
        b=obs("settled","changed",frame=11)
        r=self.row(vid,a,b)
        self.assertIn("flight",r["controls_satisfied"])
        self.assertIn("settled",r["controls_satisfied"])
        for broken in ({"frame":10},{"frame":9},{"shot_id":"shot2"},
                       {"run_id":"other"},{"generation":"g2",
                         "observed_generation":"g2","rendered_generation":"g2"},
                       {"scene_id":"scene6"},{"hole_id":"hole2"}):
            r=self.row(vid,a,obs("settled","changed",**broken))
            self.assertIn("moving_settled_shot_or_frame_mismatch",r["contradictions"])
            self.assertNotIn("settled",r["controls_satisfied"])

    def test_all_flight_settled_witnesses_must_pair_not_one_valid_pair(self):
        """A legitimate pair must not hide stale, cross-shot or wrong-frame witnesses."""
        vid="golf.ball.world_xyz"
        flight=obs("flight","changed",frame=10)
        stop=obs("settled","changed",frame=11)
        self.assertFalse(self.row(vid,flight,stop)["contradictions"])
        malformed=(
            obs("flight","changed",frame=12,shot_id="other_shot"),
            obs("settled","changed",frame=20,run_id="other_run"),
            obs("flight","changed",frame=12,scene_id="other_scene"),
            obs("settled","changed",frame=20,hole_id="other_hole"),
            obs("flight","changed",frame=12,generation="g2",
                observed_generation="g2",rendered_generation="g2"),
            obs("settled","changed",frame=10),
            obs("flight","changed",frame=12,guest_frame_verified=False),
        )
        for extra in malformed:
            with self.subTest(extra=extra):
                report=self.row(vid,flight,stop,extra)
                self.assertIn("moving_settled_shot_or_frame_mismatch",
                              report["contradictions"])
                self.assertNotIn("flight",report["controls_satisfied"])
                self.assertNotIn("settled",report["controls_satisfied"])
                self.assertFalse(report["runtime_verified"])
                self.assertFalse(report["training_eligible"])

    def test_two_separately_well_formed_shots_remain_hypotheses(self):
        vid="golf.ball.world_xyz"
        pairs=[
            obs("flight","changed",shot_id="shot1",frame=10),
            obs("settled","changed",shot_id="shot1",frame=11),
            obs("flight","changed",shot_id="shot2",frame=50),
            obs("settled","changed",shot_id="shot2",frame=60),
        ]
        result=self.row(vid,*pairs,origin="operator_reviewed")
        self.assertNotIn("moving_settled_shot_or_frame_mismatch",
                         result["contradictions"])
        self.assertIn("flight",result["controls_satisfied"])
        self.assertIn("settled",result["controls_satisfied"])
        self.assertFalse(result["runtime_verified"])
        self.assertFalse(result["training_eligible"])

    def test_opposite_direction_aim_must_be_precontact(self):
        vid="golf.player.selected_record.aim_rotation"
        a=obs("aim_left","changed",direction="left",signed_delta=-1.0)
        b=obs("aim_right","changed",direction="right",signed_delta=1.0)
        r=self.row(vid,a,b)
        self.assertIn("aim_left",r["controls_satisfied"])
        self.assertIn("aim_right",r["controls_satisfied"])
        for bad in (obs("aim_left","changed",direction="left",signed_delta=1.0),
                    obs("aim_right","changed",direction="right",signed_delta=-1.0),
                    obs("aim_left","changed",direction="left"),
                    obs("aim_left","changed",direction="left",signed_delta=-1,phase="POST"),
                    obs("aim_right","changed",direction="right",signed_delta=1,contact_verified=True)):
            r=self.row(vid,bad)
            self.assertNotIn(bad["control"],r["controls_satisfied"])

    def test_100ft_offgreen_penalty_censored_not_carry(self):
        vid="golf.config.standard_scores_table_4x9"
        for label in ("M:100ft","m:100 FT","offgreen_100ft","OFF-GREEN 100 ft"):
            r=self.row(vid,obs("native_result","matched",game_owned_acceptance=True,
                               contact_verified=True,distance_label=label))
            self.assertIn("censored_penalty_as_carry",r["contradictions"])
            self.assertFalse(r["training_eligible"])
            r=self.row(vid,obs("censored_100ft","rejected",censored=True,
                               used_as_carry=False,distance_label=label))
            self.assertIn("censored_100ft",r["controls_satisfied"])
            r=self.row(vid,obs("censored_100ft","rejected",censored=False,
                               used_as_carry=True,distance_label=label))
            self.assertIn("censored_penalty_as_carry",r["contradictions"])

    def test_callback_or_requested_a_is_not_native_contact_result(self):
        vid="golf.sequence_mgr.golf_scores_hole_major_9x4"
        r=self.row(vid,obs("native_result","matched",game_owned_acceptance=True))
        self.assertIn("native_result_or_contact_unverified",r["contradictions"])
        r=self.row(vid,obs("native_result","matched",game_owned_acceptance=True,
                           contact_verified=True,censored=False))
        self.assertIn("native_result",r["controls_satisfied"])
        self.assertFalse(r["runtime_verified"])

    def test_complete_claim_cannot_authorize_training(self):
        vid="golf.player.selected_record.aim_rotation"
        controls=p0.P[vid][0].split()
        witnesses=[]
        for c in controls:
            k={}
            response="stable"
            if c=="aim_left":
                response,k="changed",{"direction":"left","signed_delta":-1}
            elif c=="aim_right":
                response,k="changed",{"direction":"right","signed_delta":1}
            elif c=="wrong_controller":
                k={"controller_matches_selected":False}
            elif c=="disconnected_controller":
                k={"controller_connected":False}
            elif c in ("source_typed","preaction"):
                response="matched"
            witnesses.append(obs(c,response,**k))
        for origin in ("synthetic","operator_reviewed"):
            r=self.row(vid,*witnesses,origin=origin)
            self.assertEqual(r["missing_witnesses"],[])
            self.assertFalse(r["contradictions"])
            self.assertEqual(r["ready_for_independent_live_experiment_review"],
                             origin=="operator_reviewed")
            self.assertFalse(r["runtime_verified"])
            self.assertFalse(r["training_eligible"])

    def test_output_sanitization_json_markdown_and_cli_refusal(self):
        vid="golf.ball.world_xyz"
        o=obs("flight","changed",run_id="secret_session",shot_id="secret_shot",
              selected_actor="secret_actor",observed_actor="secret_actor",
              rendered_actor="secret_actor",distance_label="secret_label")
        report=p0.build_matrix(registry(),claim(vid,o))
        output=json.dumps(report)+p0.markdown(report)
        for private in ("secret_session","secret_shot","secret_actor","secret_label"):
            self.assertNotIn(private,output)
        with tempfile.TemporaryDirectory() as folder:
            reg=Path(folder)/"reg.json"
            reg.write_text(json.dumps(registry()),encoding="utf-8")
            script=ROOT/"scripts/p0_variable_validation_matrix.py"
            done=subprocess.run([sys.executable,str(script),"--registry",str(reg)],
                                capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
            self.assertEqual(json.loads(done.stdout)["p0_count"],25)
            bad=Path(folder)/"bad.json"
            bad.write_text('{"invalid":true}',encoding="utf-8")
            refused=subprocess.run([sys.executable,str(script),"--registry",str(reg),
                                    "--evidence",str(bad)],capture_output=True,text=True)
            self.assertEqual(refused.returncode,2)
            self.assertNotIn("Traceback",refused.stderr)

if __name__=="__main__":
    unittest.main()
