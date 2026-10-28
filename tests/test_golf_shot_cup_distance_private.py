"""Entirely fabricated PRE/POST/RESULT capture and distance tests. No ROM/RAM."""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import preserve_golf_shot_distance_checkpoint_private as keeper
import audit_golf_shot_cup_distance_private as distance
import audit_selected_ball_prepost_shot_private as shot


def vec(*v):
    return tuple(struct.unpack(">I",struct.pack(">f",float(w)))[0] for w in v)


def snap(ball=(0,0,0),record=(0,0,0)):
    return {
        "source_gates":True,"slot":0,"hole":1,
        "owner":(1,2,3,4,5),"map_owners":(6,7,8),
        "ball_words":vec(*ball),"record_words":vec(*record),
        "start_words":vec(0,0,0),
        "cup_words":vec(3,4,4),"pin_words":vec(3,5,4)
    }


class ShotCupDistanceSynthetic(unittest.TestCase):
    def test_valid_shot_distance_before_and_after_both_metrics(self):
        a=snap()
        b=snap(ball=(3,0,0),record=(3,0,0))
        z=distance.summarize(a,b,distinct_bank_mem1=True,
                             distinct_bank_mem2=True,
                             result_metadata={"ui_displayed_distance_value":10.0,
                                              "ui_displayed_distance_unit":"ft"},
                             result_native_present=True,
                             result_source_valid=False)
        self.assertEqual(z["selected_nested_ball_changed_components"],1)
        self.assertAlmostEqual(z["candidate_ball_to_cup_planar_after_game_units"],4)
        self.assertAlmostEqual(z["candidate_ball_to_cup_3d_after_game_units"],math.sqrt(32),places=5)
        self.assertAlmostEqual(z["candidate_pre_to_post_displacement_planar_game_units"],3)
        self.assertAlmostEqual(z["exploratory_display_units_per_game_unit_ratio"],2.5)
        self.assertEqual(z["candidate_ball_to_pin_planar_after_game_units"],4)
        self.assertFalse(z["game_unit_scale_verified"])
        self.assertFalse(z["ball_world_xyz_verified"])
        self.assertFalse(z["training_allowed"])

    def test_cup_move_refuses_even_if_ball_changes(self):
        a=snap()
        b=snap(ball=(3,0,0),record=(3,0,0))
        b["cup_words"]=vec(3,3,4)
        with self.assertRaisesRegex(ValueError,"Start/cup/pin"):
            distance.summarize(a,b,distinct_bank_mem1=True,distinct_bank_mem2=True)

    def test_selected_slot_hole_or_pointer_move_refused(self):
        for field, altered in (("slot",1),("hole",2),("owner",(9,2,3,4,5)),
                               ("map_owners",(6,7,9))):
            a=snap()
            b=snap(ball=(1,1,1))
            b[field]=altered
            with self.subTest(field=field),self.assertRaises(ValueError):
                distance.summarize(a,b,distinct_bank_mem1=True,distinct_bank_mem2=True)

    def test_same_ball_is_inconclusive_not_motion(self):
        z=distance.summarize(snap(),snap(),
                             distinct_bank_mem1=False,distinct_bank_mem2=True)
        self.assertFalse(z["candidate_ball_moved_between_pre_and_post"])
        self.assertFalse(z["observed_gameplay_hit_independently_verified"])
        self.assertFalse(z["training_allowed"])

    def test_false_or_unavailable_result_does_not_fabricate_ui(self):
        z=distance.summarize(snap(),snap(ball=(2,0,1)),
                             distinct_bank_mem1=False,distinct_bank_mem2=True,
                             result_native_present=False)
        self.assertIsNone(z["operator_typed_result_ui_distance"])
        self.assertNotIn("exploratory_display_units_per_game_unit_ratio",z)
        self.assertIsNone(z["result_golf_source_chain_still_valid"])

    def test_output_redacts_pointer_and_float_vectors(self):
        a=snap()
        b=snap(ball=(3,1,0),record=(3,1,0))
        out=distance.summarize(a,b,distinct_bank_mem1=False,
                               distinct_bank_mem2=True)
        j=json.dumps(out)
        for bad in ('"ball_words"','"start_words"','"cup_words"','"pin_words"',
                    '"owner"', '"map_owners"', "0x90000000", "Dolphin Emulator",
                    "mem1.raw","PRE-MEM2.bin"):
            self.assertNotIn(bad,j)
        self.assertFalse(out["allowed_to_publish"])

    def test_nonfinite_words_fail_closed(self):
        a=snap()
        a["ball_words"]=(0x7FC00000,0,0)
        with self.assertRaises(ValueError):
            distance.summarize(a,snap(),
                               distinct_bank_mem1=True,distinct_bank_mem2=True)

    def test_prepost_manifest_valid_for_upstream_reader(self):
        m={"checkpoints":{
            "PRE":{"sha256":{"MEM1":"a"*64,"MEM2":"b"*64}},
            "POST":{"sha256":{"MEM1":"c"*64,"MEM2":"d"*64}}
        }}
        result=keeper._prepost_manifest(m)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/shot.MANIFEST_NAME
            p.write_text(json.dumps(result))
            parsed=shot._manifest(Path(d))
        self.assertEqual(parsed["PRE"]["sha256"]["MEM1"],"a"*64)

    def test_sequence_stale_and_no_shot_attestation_fail(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"Wii-AI-Golf-Data"
            sess=root/"captures"/"case"
            sess.mkdir(parents=True)
            src=Path(t)/"Dump"
            src.mkdir()
            m1=src/"mem1.raw";m2=src/"mem2.raw"
            m1.write_bytes(b"RSPE01\x00\x01"+bytes(56))
            m2.write_bytes(bytes(128))
            with (patch.object(keeper.shot.roster,"MEM1_SIZE",64),
                  patch.object(keeper.shot.roster,"MEM2_SIZE",128)):
                with self.assertRaises(ValueError):
                    keeper.preserve(private_root=sess,mem1_source=m1,
                                    mem2_source=m2,checkpoint="POST",
                                    paused_confirmed=True,
                                    shot_observed=True,
                                    same_process_confirmed=True,
                                    same_hole_confirmed=True,
                                    trusted_root=root)
                # Explicitly order file times so MEM2 export is later.
                now=2_000_000_000
                os.utime(m1,ns=(now,now))
                os.utime(m2,ns=(now+1000,now+1000))
                saved=keeper.preserve(private_root=sess,mem1_source=m1,
                                      mem2_source=m2,checkpoint="PRE",
                                      paused_confirmed=True,trusted_root=root)
                self.assertEqual(saved["preserved_native_banks"],2)
                self.assertTrue((sess/"PRE-MEM1.bin").exists())
                with self.assertRaises(ValueError):
                    keeper.preserve(private_root=sess,mem1_source=m1,
                                    mem2_source=m2,checkpoint="POST",
                                    paused_confirmed=True,shot_observed=True,
                                    same_process_confirmed=True,
                                    same_hole_confirmed=True,
                                    trusted_root=root)

    def test_valid_post_creates_upstream_compatible_pair_and_result_stage(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"Wii-AI-Golf-Data"
            sess=root/"captures"/"case"
            sess.mkdir(parents=True)
            src=Path(t)/"Dump"
            src.mkdir()
            m1=src/"mem1.raw";m2=src/"mem2.raw"
            with (patch.object(keeper.shot.roster,"MEM1_SIZE",64),
                  patch.object(keeper.shot.roster,"MEM2_SIZE",128)):
                for step,phase in enumerate(("PRE","POST","RESULT")):
                    m1.write_bytes(b"RSPE01\x00\x01"+bytes([step])*56)
                    m2.write_bytes(bytes([step])*128)
                    mt=5_000_000_000+step*1_000_000
                    os.utime(m1,ns=(mt,mt))
                    os.utime(m2,ns=(mt+1000,mt+1000))
                    args={"private_root":sess,"mem1_source":m1,
                          "mem2_source":m2,"checkpoint":phase,
                          "paused_confirmed":True,"trusted_root":root}
                    if phase=="POST":
                        args.update(shot_observed=True,
                                    same_process_confirmed=True,
                                    same_hole_confirmed=True)
                    if phase=="RESULT":
                        args.update(result_visible=True,
                                    displayed_distance=4.5,ui_unit="ft")
                    out=keeper.preserve(**args)
                self.assertEqual(out["total_phases_preserved"],3)
                self.assertTrue((sess/"RESULT-MEM2.bin").exists())
                parsed=shot._manifest(sess)
                self.assertEqual(len(parsed),2)
                extra=keeper._read_manifest(sess/keeper.NAME)
                self.assertEqual(extra["checkpoints"]["RESULT"][
                    "ui_displayed_distance_value"],4.5)

    def test_ui_distance_validation_and_no_false_observation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for pair in [(None,"ft"),(2.0,None),(-5.0,"yd"),(2.0,"miles")]:
                with self.subTest(pair=pair),self.assertRaises(ValueError):
                    keeper.preserve(private_root=p,
                                    mem1_source=p/"mem1.raw",
                                    mem2_source=p/"mem2.raw",
                                    checkpoint="RESULT",
                                    paused_confirmed=True,result_visible=True,
                                    displayed_distance=pair[0],ui_unit=pair[1])
            with self.assertRaises(ValueError):
                keeper.preserve(private_root=p,mem1_source=p/"mem1.raw",
                                mem2_source=p/"mem2.raw",
                                checkpoint="RESULT",paused_confirmed=True,
                                result_visible=False)

    def test_failed_cli_redacts_paths(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"DO-NOT-PRINT-THIS-PATH"
            err=StringIO()
            with redirect_stderr(err):
                result=keeper.main([
                    "--private-root",str(p),"--mem1-source",str(p/"mem1.raw"),
                    "--mem2-source",str(p/"mem2.raw"),
                    "--checkpoint","PRE","--paused-confirmed"])
            self.assertEqual(result,1)
            self.assertNotIn(str(p),err.getvalue())

if __name__=="__main__":
    unittest.main()
