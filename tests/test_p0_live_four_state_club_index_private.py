"""Offline tests of source-gated, operator-controlled four-state live experiment."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
P=ROOT/"scripts"/"p0_live_four_state_club_index_private.py"
spec=importlib.util.spec_from_file_location("four_state_live",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

C2I={"DRIVER":3,"IRON":2,"WEDGE":1,"PUTTER":0}

def fixture():
    E=[]
    for phase,target,_ in m.stages():
        if phase in ("B0","IDLE","DOWN","AIM"):
            club="DRIVER"
        elif phase=="UP":
            club="IRON"
        elif target is not None:
            club=target
        else:
            club=("WEDGE","DRIVER","PUTTER","IRON")[int(phase[1:])]
        E.append({"phase":phase,"club":club,"index":C2I[club],
                  "frame_start":1,"frame_end":2})
    return E

class FakeRPC:
    def __init__(self,values,ball="00"*12):
        self.values=values
        self.ball=ball
        self.frame=100
    def call(self,method,args):
        if method=="frame.get_count":
            self.frame+=1
            return self.frame
        if method=="memory.read_u32":
            return self.values[args[0]]
        if method=="memory.read_bytes":
            return self.ball
        raise AssertionError(method)

class TestLiveFourState(unittest.TestCase):
    def test_positive_all_clubs_and_controls(self):
        r=m.analyze(fixture())
        self.assertEqual(r["status"],"LIVE_FOUR_STATE_CANDIDATE_VALIDATED")
        self.assertEqual(r["operator_index_map"],C2I)
        self.assertTrue(all(r["control_and_holdout_checks"].values()))
        self.assertFalse(r["full_native_register_and_object_identity_proven"])
        self.assertFalse(r["training_approved"])

    def test_aim_only_confounded_index_rejected(self):
        E=fixture()
        next(x for x in E if x["phase"]=="AIM")["index"]=2
        r=m.analyze(E)
        self.assertEqual(r["status"],"LIVE_FOUR_STATE_CANDIDATE_NOT_VALIDATED")
        self.assertFalse(r["control_and_holdout_checks"]["aim_same_index_and_club"])

    def test_heldout_wrong_visible_label_rejected(self):
        E=fixture()
        next(x for x in E if x["phase"]=="V3")["club"]="PUTTER"
        r=m.analyze(E)
        self.assertFalse(r["control_and_holdout_checks"]["heldout_four_correct"])

    def test_wrong_direction_step_rejected(self):
        E=fixture()
        next(x for x in E if x["phase"]=="UP")["index"]=1
        r=m.analyze(E)
        self.assertFalse(r["control_and_holdout_checks"]["up_one_step_or_bound"])

    def test_nonunique_two_pass_map_rejected(self):
        E=fixture()
        for row in E:
            if row["club"]=="IRON" and row["phase"].startswith("T"):
                row["index"]=3
        r=m.analyze(E)
        self.assertFalse(r["control_and_holdout_checks"]["four_unique_index_values"])

    def test_missing_window_refused(self):
        with self.assertRaises(m.Abstain):
            m.analyze(fixture()[:-1])

    def test_quick_positive_manual_up_down_aim(self):
        result=m.analyze_quick(fixture()[:5])
        self.assertEqual(result["status"],
                         "QUICK_DPAD_FOUR_STATE_CANDIDATE_SUPPORTED")
        self.assertFalse(result["game_club_id_verified"])
        self.assertFalse(result["training_approved"])

    def test_quick_reject_no_visible_club_switch(self):
        rows=fixture()[:5]
        for row in rows:
            row["club"]="DRIVER"
        result=m.analyze_quick(rows)
        self.assertEqual(result["status"],
                         "QUICK_DPAD_FOUR_STATE_CANDIDATE_NOT_SUPPORTED")

    def test_quick_reject_aim_only_index_change(self):
        rows=fixture()[:5]
        rows[-1]["index"]=2
        result=m.analyze_quick(rows)
        self.assertFalse(result["controls"]["aim_only_same_club_and_index"])

    def test_source_root_unchanged_two_word_samples(self):
        # Identity same tuple shape as canonical p0_live_no_contact_compare:
        mgr,scene,config,field,pm,player,record,ball,nested,start,tee,pin,pinvec,hole=(
            0x80001000,0x90000000,0x90001000,0x90002000,0x90003000,0,
            0x90003004,0x90004000,0x90005000,0x90006000,0x90007000,
            0x90008000,0x90009000,3)
        ident=(mgr,scene,config,field,pm,player,record,ball,nested,start,tee,pin,pinvec,hole)
        vals={
          m.GLOBAL_SLOT:pm,m.source.SCENE_STATIC:mgr,
          m.source.CONFIG_STATIC:config,mgr+0x18:5,
          config+0x94:4,config+0x98:hole,pm+0x334:record,pm+0x1c:2}
        r=m.bracketed_index(FakeRPC(vals),ident,"00"*12)
        self.assertEqual(r["index"],2)
        vals[m.GLOBAL_SLOT]=0
        with self.assertRaises(m.Abstain):
            m.bracketed_index(FakeRPC(vals),ident,"00"*12)

    def test_ball_moving_abstains(self):
        mgr,scene,config,field,pm,player,record,ball,nested,start,tee,pin,pinvec,hole=(
            0x80001000,0x90000000,0x90001000,0x90002000,0x90003000,0,
            0x90003004,0x90004000,0x90005000,0x90006000,0x90007000,
            0x90008000,0x90009000,3)
        ident=(mgr,scene,config,field,pm,player,record,ball,nested,start,tee,pin,pinvec,hole)
        vals={m.GLOBAL_SLOT:pm,m.source.SCENE_STATIC:mgr,
              m.source.CONFIG_STATIC:config,mgr+0x18:5,
              config+0x94:4,config+0x98:hole,pm+0x334:record,pm+0x1c:2}
        with self.assertRaises(m.Abstain):
            m.bracketed_index(FakeRPC(vals,ball="11"*12),ident,"00"*12)

    def test_no_unsafe_labels(self):
        with self.assertRaises(m.Abstain):
            m.correct_label("wood 3")
        self.assertEqual(m.correct_label(" Wedge "),"WEDGE")

if __name__=="__main__":
    unittest.main()
