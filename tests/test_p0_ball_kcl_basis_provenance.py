"""Synthetic only: no original KCL, RAM, actual ball position or native parity."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FILE = Path(__file__).resolve().parents[1]/"scripts/review_p0_ball_kcl_basis_provenance.py"
spec = importlib.util.spec_from_file_location("s002_ball_kcl_basis", FILE)
basis = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = basis
spec.loader.exec_module(basis)


PTS = ((0,0,0),(2,0,0),(0,3,0),(0,0,4),(2,3,4))


def sample():
    base = {"revision":"RSPE01 Rev1","cohort_sha256":"a"*64,
            "scene_id":"synthetic_scene","shot_id":"synthetic_shot", "units":"native_candidate",
            "handedness":"right","source_qualified":True}
    ball = dict(base,basis_id="ball_xyz",source_kind="source_selected_ball_translation",
                landmarks=[{"id":f"p{i}","xyz":list(v)} for i,v in enumerate(PTS)])
    terrain = dict(base,basis_id="kcl_xyz",source_kind="source_kcl_prism_vertex",
                   landmarks=[{"id":f"p{i}","xyz":list(v)} for i,v in enumerate(PTS)])
    witness = {"kind":"independent_source_transform","independently_qualified":True,
               "source_reference":"SYNTHETIC_ONLY","from_basis_id":"ball_xyz","to_basis_id":"kcl_xyz",
               "from_units":"native_candidate","to_units":"native_candidate", "length_scale":1.0,
               "matrix_xyz":[[1,0,0],[0,1,0],[0,0,1]],"translation_xyz":[0,0,0]}
    return {"schema":basis.SCHEMA,"ball":ball,"terrain":terrain,
            "transform_witness":witness,"tolerance":1e-6}


class BasisContractTests(unittest.TestCase):
    def verify(self, case, status, reason=None):
        result=basis.assess_claim(case)
        self.assertEqual(result["status"],status)
        if reason: self.assertEqual(result["reason"],reason)
        self.assertFalse(result["native_game_parity_verified"])
        self.assertFalse(result["selected_ball_world_xyz_verified"])
        self.assertFalse(result["training_approved"])
        self.assertNotIn("archive",json.dumps(result))
        self.assertNotIn("synthetic_shot",json.dumps(result))
        return result

    def test_positive_identity_is_only_conditional(self):
        self.assertEqual(self.verify(sample(),"CONDITIONALLY_CONSISTENT")["landmark_count"],5)

    def test_positive_translation_with_independent_witness(self):
        c=sample();c["transform_witness"]["translation_xyz"]=[11,-7,2]
        for p in c["terrain"]["landmarks"]:p["xyz"]=[x+d for x,d in zip(p["xyz"],[11,-7,2])]
        self.verify(c,"CONDITIONALLY_CONSISTENT")

    def test_positive_axis_swap_proper_rotation(self):
        c=sample();m=[[0,1,0],[-1,0,0],[0,0,1]];c["transform_witness"]["matrix_xyz"]=m
        for p in c["terrain"]["landmarks"]:
            x,y,z=p["xyz"];p["xyz"]=[y,-x,z]
        self.verify(c,"CONDITIONALLY_CONSISTENT")

    def test_positive_reflection_with_explicit_opposite_handedness(self):
        c=sample();c["terrain"]["handedness"]="left";c["transform_witness"]["matrix_xyz"]=[[-1,0,0],[0,1,0],[0,0,1]]
        for p in c["terrain"]["landmarks"]:p["xyz"][0]*=-1
        self.verify(c,"CONDITIONALLY_CONSISTENT")

    def test_negative_unwitnessed_reflection(self):
        c=sample();c["transform_witness"]["matrix_xyz"]=[[-1,0,0],[0,1,0],[0,0,1]]
        self.verify(c,"INCONSISTENT","HANDEDNESS_REFLECTION_CONFLICT")

    def test_negative_unwitnessed_axis_swap(self):
        c=sample();c["terrain"]["landmarks"][1]["xyz"]=[0,2,0]
        self.verify(c,"INCONSISTENT","LANDMARK_TRANSFORM_RESIDUAL")

    def test_negative_translation(self):
        c=sample();c["terrain"]["landmarks"][0]["xyz"]=[10,0,0]
        self.verify(c,"INCONSISTENT","LANDMARK_TRANSFORM_RESIDUAL")

    def test_negative_unit_scale_without_witness(self):
        c=sample();c["terrain"]["landmarks"][1]["xyz"][0]*=.01
        self.verify(c,"INCONSISTENT","LANDMARK_TRANSFORM_RESIDUAL")

    def test_positive_declared_scale_and_independent_unit_map(self):
        c=sample();c["terrain"]["units"]="different_units"
        w=c["transform_witness"];w["to_units"]="different_units";w["length_scale"]=.01
        w["matrix_xyz"]=[[.01,0,0],[0,.01,0],[0,0,.01]]
        for p in c["terrain"]["landmarks"]:p["xyz"]=[x*.01 for x in p["xyz"]]
        self.verify(c,"CONDITIONALLY_CONSISTENT")

    def test_negative_nonuniform_scale(self):
        c=sample();c["transform_witness"]["matrix_xyz"]=[[1,0,0],[0,2,0],[0,0,1]]
        self.verify(c,"INCONSISTENT","NONUNIFORM_SCALE_OR_SHEAR")

    def test_negative_wrong_cohort(self):
        c=sample();c["terrain"]["cohort_sha256"]="b"*64
        self.verify(c,"ABSTAIN","SOURCE_SCENE_SHOT_COHORT_MISMATCH")

    def test_negative_wrong_scene(self):
        c=sample();c["terrain"]["scene_id"]="other_scene"
        self.verify(c,"ABSTAIN","SOURCE_SCENE_SHOT_COHORT_MISMATCH")

    def test_negative_wrong_shot(self):
        c=sample();c["terrain"]["shot_id"]="other_shot"
        self.verify(c,"ABSTAIN","SOURCE_SCENE_SHOT_COHORT_MISMATCH")

    def test_negative_wrong_source_receiver(self):
        c=sample();c["ball"]["source_kind"]="source_global_ball"
        self.verify(c,"ABSTAIN","WRONG_SOURCE_OBJECT")

    def test_negative_unqualified_anchors(self):
        c=sample();c["ball"]["source_qualified"]=False
        self.verify(c,"ABSTAIN","UNVERIFIED_SOURCE_ANCHOR")

    def test_negative_absent_witness(self):
        c=sample();del c["transform_witness"]
        self.verify(c,"ABSTAIN","MISSING_INDEPENDENT_TRANSFORM_WITNESS")

    def test_negative_self_fitted_not_independent_witness(self):
        c=sample();c["transform_witness"]["independently_qualified"]=False
        self.verify(c,"ABSTAIN","UNQUALIFIED_TRANSFORM_WITNESS")

    def test_negative_missing_transform_source_ref(self):
        c=sample();c["transform_witness"].pop("source_reference")
        self.verify(c,"ABSTAIN","MISSING_TRANSFORM_SOURCE_REFERENCE")

    def test_negative_unit_owner_mismatch(self):
        c=sample();c["terrain"]["units"]="meters"
        self.verify(c,"ABSTAIN","UNQUALIFIED_UNIT_MAPPING")

    def test_negative_unknown_handedness(self):
        c=sample();c["ball"]["handedness"]="unknown"
        self.verify(c,"ABSTAIN","UNKNOWN_HANDEDNESS")

    def test_negative_insufficient_anchors(self):
        c=sample();c["ball"]["landmarks"]=c["ball"]["landmarks"][:3]
        self.verify(c,"ABSTAIN","INSUFFICIENT_MATCHED_LANDMARKS")

    def test_negative_coplanar_anchor_set(self):
        c=sample()
        for side in ("ball","terrain"):
            for p in c[side]["landmarks"]:p["xyz"][2]=0
        self.verify(c,"ABSTAIN","NONCOPLANAR_3D_ANCHORS_NOT_ESTABLISHED")

    def test_negative_unmatched_anchor_identity(self):
        c=sample();c["terrain"]["landmarks"][0]["id"]="different_id"
        self.verify(c,"ABSTAIN","UNMATCHED_LANDMARK_IDENTITIES")

    def test_negative_duplicate_anchor_id(self):
        c=sample();c["terrain"]["landmarks"][0]["id"]="p1"
        self.verify(c,"ABSTAIN","INVALID_ANCHOR_ID")

    def test_negative_nonfinite_and_bool_scalar(self):
        for v in (float("nan"), float("inf"), True,"1"):
            with self.subTest(v=v):
                c=sample();c["ball"]["landmarks"][1]["xyz"][0]=v
                self.verify(c,"ABSTAIN")

    def test_negative_wrong_revision(self):
        c=sample();c["ball"]["revision"]="RSPE01 Rev2"
        self.verify(c,"ABSTAIN","UNSUPPORTED_REVISION")

    def test_negative_bad_tolerance(self):
        for tol in (0,-1,1,True,"0.1"):
            with self.subTest(tol=tol):
                c=sample();c["tolerance"]=tol
                self.verify(c,"ABSTAIN","INVALID_TOLERANCE")

    def test_cli_only_reports_categorical_no_raw_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"fixture.json";p.write_text(json.dumps(sample()))
            run=subprocess.run([sys.executable,str(FILE),"--input",str(p)],capture_output=True,text=True,check=False)
            self.assertEqual(run.returncode,0)
            self.assertEqual(json.loads(run.stdout)["status"],"CONDITIONALLY_CONSISTENT")
            self.assertNotIn("synthetic_shot",run.stdout)
            self.assertNotIn("ball_xyz",run.stdout)
            self.assertNotIn("0.0",run.stdout)
            p.write_text("not JSON")
            err=subprocess.run([sys.executable,str(FILE),"--input",str(p)],capture_output=True,text=True,check=False)
            self.assertEqual(err.returncode,2)
            self.assertEqual(json.loads(err.stdout)["reason"],"UNREADABLE_EVIDENCE_INPUT")


if __name__ == "__main__":
    unittest.main()
