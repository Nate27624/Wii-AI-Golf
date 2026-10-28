"""Entirely synthetic post-shot SETTLED/RESULT validation and privacy."""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_golf_postshot_followup_private as follow
import audit_golf_two_bank_roster_private as roster


def u32(x):
    return int.from_bytes(struct.pack(">f", float(x)), "big")


def sample(x=0., *, owner=(10,20,30,40,50), hole=1, start=0.):
    return {"source_gates": True, "owner": owner, "slot": 0, "hole": hole,
            "ball_words": (u32(x),u32(0),u32(0)),
            "record_words": (u32(x),u32(0),u32(0)),
            "start_words": (u32(start),u32(0),u32(0))}


def doc(*, settled=True, result=True, distance=None):
    hashes={"MEM1":"0"*64, "MEM2":"1"*64}
    checkpoints={}
    if settled:
        checkpoints["SETTLED"]={
            "phase_operator_label":"settled_before_reset",
            "operator_reports_gui_paused":True,
            "operator_reports_both_exports_same_pause":True,
            "operator_reports_ball_visibly_stopped":True,
            "operator_reports_no_hole_or_reset_transition":True,
            "sha256":hashes,
        }
    if result:
        checkpoints["RESULT"]={
            "phase_operator_label":"visible_results_screen",
            "operator_reports_gui_paused":True,
            "operator_reports_both_exports_same_pause":True,
            "operator_reports_result_screen_visible":True,
            "sha256":hashes,
        }
    return {"kind":follow.KIND,"schema_version":1,
            "operator_reports_same_dolphin_process":True,
            "operator_reports_same_one_shot":True,
            "checkpoints":checkpoints,
            "human_displayed_result_distance":distance}


BASE={"source_gates_verified_both_phases":True}


class PostshotFollowupPrivateTests(unittest.TestCase):
    def test_settled_approaches_pin_without_yards_claim(self):
        pin=(u32(10),u32(0),u32(0))
        status=follow.evaluate_settled(sample(0),sample(3),sample(7),pin,pin,pin)
        self.assertEqual(status["candidate_component_0_2_gap_to_pin_trend"],
                         "closer_candidate")
        self.assertTrue(status["source_start_translation_unchanged"])
        self.assertFalse(status["game_coordinate_axes_or_distance_units_verified"])

    def test_settled_moves_away_and_source_geometry_remains_hypothesis(self):
        pin=(u32(10),u32(0),u32(0))
        status=follow.evaluate_settled(sample(0),sample(3),sample(-4),pin,pin,pin)
        self.assertEqual(status["candidate_component_0_2_gap_to_pin_trend"],
                         "farther_candidate")

    def test_unstable_pin_or_start_suppresses_gap_trend(self):
        pin=(u32(10),u32(0),u32(0))
        status=follow.evaluate_settled(
            sample(), sample(3), sample(7),
            pin, pin, (u32(11),u32(0),u32(0)))
        self.assertEqual(status["candidate_component_0_2_gap_to_pin_trend"],
                         "unavailable")
        self.assertFalse(status["source_pin_translation_unchanged"])
        status=follow.evaluate_settled(
            sample(),sample(3),sample(7,start=1),pin,pin,pin)
        self.assertEqual(status["candidate_component_0_2_gap_to_pin_trend"],
                         "unavailable")

    def test_player_or_hole_switch_rejected(self):
        pin=(u32(10),u32(0),u32(0))
        with self.assertRaisesRegex(ValueError, "identity"):
            follow.evaluate_settled(sample(),sample(2),
                                    sample(3,owner=(10,20,99,40,50)),
                                    pin,pin,pin)
        with self.assertRaisesRegex(ValueError, "identity"):
            follow.evaluate_settled(sample(),sample(2),sample(3,hole=2),
                                    pin,pin,pin)

    def test_valid_ui_distance_is_human_label_only_not_decoded(self):
        d=doc(settled=False, result=True, distance={"value":12.5,"unit":"feet"})
        out=follow.assemble(BASE,d,result_bank_changed=True)
        self.assertTrue(out["operator_entered_ui_distance_private"])
        self.assertEqual(out["operator_entered_ui_distance_unit"],"feet")
        self.assertFalse(out["physical_distance_to_hole_verified"])
        self.assertFalse(out["result_screen_ball_pointer_validated"])
        self.assertFalse(out["game_result_distance_decoded_from_ram"])
        self.assertFalse(out["approved_for_model_training"])
        self.assertNotIn("12.5",json.dumps(out))

    def test_result_snapshot_independent_of_settled_memory(self):
        d=doc(settled=False,result=True)
        out=follow.assemble(BASE,d,result_bank_changed=False)
        self.assertFalse(out["result_bank_change_observed"])
        self.assertEqual(out["candidate_component_0_2_gap_to_pin_trend"],"unavailable")

    def test_settled_only_requires_source_triads(self):
        d=doc(settled=True,result=False)
        p=(u32(10),u32(0),u32(0))
        out=follow.assemble(BASE,d,settled=(sample(0),sample(3),sample(8)),
                             pins=(p,p,p))
        self.assertTrue(out["settled_memory_pair_hash_verified"])
        self.assertFalse(out["results_screen_memory_pair_hash_verified"])
        self.assertEqual(out["candidate_component_0_2_gap_to_pin_trend"],
                         "closer_candidate")

    def test_wrong_phase_and_missing_result_ui_provenance_rejected(self):
        d=doc(settled=True,result=True)
        d["checkpoints"]["SETTLED"]["operator_reports_ball_visibly_stopped"]=False
        with self.assertRaises(ValueError):
            follow.validate_followup(d)
        d=doc(settled=False,result=True)
        d["checkpoints"]["RESULT"]["operator_reports_result_screen_visible"]=False
        with self.assertRaises(ValueError):
            follow.validate_followup(d)

    def test_bad_distance_nan_unknown_unit_or_fake_flag_rejected(self):
        for dist in ({"value":float("nan"),"unit":"feet"},
                     {"value":-2,"unit":"feet"},
                     {"value":5,"unit":"game units"},
                     {"value":5,"unit":"yards","verified":True},
                     {"value":10001,"unit":"feet"}):
            with self.subTest(dist=dist):
                with self.assertRaises(ValueError):
                    follow.validate_followup(doc(distance=dist))

    def test_empty_manifest_and_unverified_prepost_rejected(self):
        with self.assertRaises(ValueError):
            follow.validate_followup(doc(settled=False,result=False))
        with self.assertRaises(ValueError):
            follow.assemble({"source_gates_verified_both_phases":False},
                             doc(settled=False,result=True),
                             result_bank_changed=True)

    def test_pointer_read_uses_field_manager_pin_chain_not_generic_scan(self):
        field=0x90010000
        pinobj=0x90011000
        vec=pinobj+0x30
        mem={roster.GOLF_FIELD_STATIC:field,
             field+0x44:pinobj,
             pinobj+0x4C:vec,
             vec:u32(2),vec+4:u32(1),vec+8:u32(4)}
        self.assertEqual(follow.pin_words(mem.__getitem__),
                         (u32(2),u32(1),u32(4)))
        mem[pinobj+0x4C]=0
        with self.assertRaises(ValueError):
            follow.pin_words(mem.__getitem__)

    def test_nonfinite_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            follow._f32(0x7F800000)
        with self.assertRaises(ValueError):
            follow._f32(0x7FC00000)
        with self.assertRaises(ValueError):
            follow._f32(-1)

    def test_summary_never_exposes_private_raw_coordinates_or_ui_number(self):
        d=doc(distance={"value":789.5,"unit":"yards"})
        p=(u32(10),u32(0),u32(0))
        report=follow.assemble(BASE,d,settled=(sample(0),sample(3),sample(7)),
                               pins=(p,p,p),result_bank_changed=True)
        raw=json.dumps(report)
        for private in ("789.5","0x900", "record_words","ball_words","10.0"):
            self.assertNotIn(private,raw)
        self.assertFalse(report["allowed_to_publish"])

    def test_cli_fail_closed_private_path_redaction(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"SECRET-RAM-0x90000000"
            buf=StringIO()
            with redirect_stderr(buf):
                code=follow.main(["--private-root",str(path)])
            self.assertEqual(code,1)
            self.assertNotIn(t,buf.getvalue())
            self.assertNotIn("SECRET-RAM",buf.getvalue())


if __name__=="__main__":
    unittest.main()
