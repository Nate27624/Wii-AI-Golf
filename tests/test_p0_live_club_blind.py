"""Synthetic-only source-gated club experiment regressions; no Dolphin."""
from __future__ import annotations
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src")]
import p0_live_club_blind as study

LABELS=("WEDGE","IRON","DRIVER")

def sample(club="WEDGE",*,aim=False):
    groups={}
    for name,(_,n,_) in study.LAYOUT.items():
        values=[0]*n
        if name=="selected_player":
            values[7]={"WEDGE":1,"IRON":2,"DRIVER":3}.get(club,9)
            values[15]=22 if aim else 11
        if name=="golf_config":
            values[10]={"WEDGE":10,"IRON":20,"DRIVER":30}.get(club,90)
        groups[name]=tuple(values)
    return {"groups":groups,"aim":22 if aim else 11,
            "identity":tuple(range(14)),"ball":(1,2,3),"phase":"C",
            "index":0,"start_ns":1,"end_ns":2,
            "bridge_bracket_NOT_GUEST_PHYSICS":(5,6)}

def window(club="WEDGE",*,aim=False):
    return [sample(club,aim=aim),sample(club,aim=aim)]

def windows(labels=LABELS):
    d={}
    for i,club in enumerate(labels):
        for prefix in ("T0","T1","V"):
            d[f"{prefix}_{i}"]=window(club)
    d["AIM0"]=window(labels[0],aim=True)
    return d

class ClubTests(unittest.TestCase):
    def test_label_validation(self):
        self.assertEqual(study.labels_from_prompt("Wedge, Iron"),("WEDGE","IRON"))
        for invalid in ("Wedge","Wedge,Wedge","Wedge,7Iron","Wedge,Iron,Driver,Putter,Putter"):
            with self.assertRaises(study.Abstain):study.labels_from_prompt(invalid)
    def test_heldout_three_classes_and_blind(self):
        model,report=study.evaluate(windows(),LABELS)
        self.assertTrue(report["heldout_pass"])
        for club in LABELS:self.assertEqual(study.predict(window(club),model),club)
    def test_aim_confound_removed_even_if_pseudo_club_separates(self):
        model,report=study.evaluate(windows(("WEDGE","IRON")),("WEDGE","IRON"))
        self.assertTrue(report["aim_control_changed"])
        self.assertIn("selected_player+0x1C",report["candidate_locations"])
        self.assertNotIn("selected_player+0x3C",report["candidate_locations"])
    def test_unchanged_aim_control_abstains(self):
        w=windows(("WEDGE","IRON"));w["AIM0"]=window("WEDGE")
        with self.assertRaisesRegex(study.Abstain,"AIM_CONTROL_UNCHANGED"):
            study.evaluate(w,("WEDGE","IRON"))
    def test_phase_drift_rejects_field(self):
        w=windows(("WEDGE","IRON"))
        base=w["T1_0"][1]["groups"]["selected_player"]
        w["T1_0"][1]["groups"]["selected_player"]=tuple(99 if i==7 else v for i,v in enumerate(base))
        _,report=study.evaluate(w,("WEDGE","IRON"))
        self.assertNotIn("selected_player+0x1C",report["candidate_locations"])
        self.assertIn("golf_config+0x28",report["candidate_locations"])
    def test_holdout_failure_disables_all_predictions(self):
        w=windows(("WEDGE","IRON"));w["V_1"]=window("WEDGE")
        model,report=study.evaluate(w,("WEDGE","IRON"))
        self.assertFalse(report["inference_enabled"])
        self.assertEqual(study.predict(window("IRON"),model),"UNKNOWN")
    def test_out_of_vocabulary_abstains(self):
        model,_=study.evaluate(windows(),LABELS)
        self.assertEqual(study.predict(window("UNKNOWN"),model),"UNKNOWN")
    def test_source_qualified_read_and_stop_on_identity_or_ball(self):
        identity=list(range(14))
        identity[0]=0x80010000;identity[2]=0x90010000;identity[6]=0x90020000
        event={"identity":tuple(identity),
               "words":{"selected_ball_plus_0x30":(1,2,3),
                        "aim_candidate_plus_0x3c":(11,)},
               "start_ns":1,"frame_bracket":(7,8)}
        class Fake:
            def __init__(self):self.calls=[]
            def call(self,method,params):
                self.calls.append((method,params))
                assert method=="memory.read_u32"
                return 33
        with patch.object(study.source,"packet",return_value=event), \
             patch.object(study.source,"end_epoch_matches",return_value=True):
            rpc=Fake()
            with self.assertRaisesRegex(study.Abstain,"SOURCE_IDENTITY_CHANGED"):
                study.read_window(rpc,"C",0,identity=("wrong",))
            with self.assertRaisesRegex(study.Abstain,"SELECTED_BALL_MOVED"):
                study.read_window(rpc,"C",0,initial_ball=(9,9,9))
            row=study.read_window(rpc,"C",0)
            self.assertEqual(len(rpc.calls),51+39+32)
            self.assertEqual(len(row["groups"]["selected_player"]),51)
            self.assertEqual(len(row["groups"]["golf_main"]),32)
            serialized=study.serialize_packet(row)
            self.assertEqual(serialized["bridge_bracket_NOT_GUEST_PHYSICS"],(7,8))
            self.assertFalse(serialized["training_approved"])
    def test_all_stage_prompts_mocked_and_private_sha_seal(self):
        class FakeRPC:
            def __init__(self,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*_):return None
            def call(self,method,params):return {"bridge_version":"synthetic"}
        phases=["T0_0","T0_1","T1_1","T1_0","AIM0","V_0","V_1","B_0","B_1"]
        clubs={"T0_0":"WEDGE","T0_1":"IRON","T1_1":"IRON","T1_0":"WEDGE",
               "AIM0":"WEDGE","V_0":"WEDGE","V_1":"IRON","B_0":"WEDGE","B_1":"IRON"}
        def fake_read(rpc,phase,index,**_):
            item=sample(clubs[phase],aim=phase=="AIM0")
            return dict(item,phase=phase,index=index)
        answers=["READY","Wedge,Iron"]
        for phase in phases:
            answers.extend(["YES",clubs[phase]])
        output=io.StringIO()
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(study,"read_window",side_effect=fake_read), \
             patch("builtins.input",side_effect=answers),redirect_stdout(output):
            args=SimpleNamespace(private_root=Path(temp),port=55355,
                                 samples_per_window=2,blind_windows=2,focus_seconds=8)
            self.assertEqual(study.run(args,rpc_class=FakeRPC,sleep=lambda _:None),0)
            folder=next(Path(temp).glob("p0-club-blind-*-PRIVATE"))
            data=(folder/"candidate-events-PRIVATE.jsonl").read_bytes()
            manifest=json.loads((folder/"manifest-PRIVATE.json").read_text())
            from hashlib import sha256
            self.assertEqual(manifest["sha256"],sha256(data).hexdigest())
            self.assertEqual(manifest["sample_packets"],18)
            self.assertEqual(manifest["blind_predictions"],{"B_0":"WEDGE","B_1":"IRON"})
            self.assertEqual(manifest["blind_truth"],{"B_0":"WEDGE","B_1":"IRON"})
            self.assertTrue(manifest["calibration"]["heldout_pass"])
            self.assertIn("BLIND CLUB PREDICTION B_0: WEDGE",output.getvalue())
            self.assertFalse(manifest["game_club_id_verified"])
    def test_empty_model_unknown(self):
        self.assertEqual(study.predict(window(),[]),"UNKNOWN")

if __name__=="__main__":
    unittest.main()
