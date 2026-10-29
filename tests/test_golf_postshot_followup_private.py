"""Entirely synthetic post-shot SETTLED/RESULT validation and privacy."""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
import hashlib
import os
import stat
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_golf_postshot_followup_private as follow
import audit_golf_two_bank_roster_private as roster


def u32(x):
    return int.from_bytes(struct.pack(">f", float(x)), "big")


def sample(x=0., *, owner=(10,20,30,40,50), hole=1, start=0.,
           pin_object=0x90011000):
    return {"source_gates": True, "owner": owner, "slot": 0, "hole": hole,
            "pin_object": pin_object,
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

    def test_pin_object_switch_rejected_even_when_pin_vector_identical(self):
        pin=(u32(10),u32(0),u32(0))
        # The old code compared only three coordinate words; a source PIN
        # pointer switch would have been silently accepted as same geometry.
        with self.assertRaisesRegex(ValueError, "PIN object identity"):
            follow.evaluate_settled(sample(0),sample(3),
                                    sample(7,pin_object=0x90012000),
                                    pin,pin,pin)
        with self.assertRaisesRegex(ValueError, "PIN object identity"):
            follow.evaluate_settled(sample(0),sample(3),
                                    sample(7,pin_object=None),
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
        # In-bounds but redirected: a foreign MEM2 vector is not a PIN.
        alternate_vec=0x90012000
        mem[pinobj+0x4C]=alternate_vec
        mem[alternate_vec]=u32(8)
        mem[alternate_vec+4]=u32(9)
        mem[alternate_vec+8]=u32(10)
        with self.assertRaisesRegex(ValueError, "selfref"):
            follow.pin_words(mem.__getitem__)
        # Invalid/out-of-bank pointer remains rejected as well.
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

    def test_phase_read_rejects_bank_overwrite_between_initial_hash_and_map(self):
        # A valid pre-read SHA alone can admit a later same-sized overwrite.
        # Use small *fabricated* files, never real Wii RAM.
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)
            p1=folder/"RESULT-MEM1.bin"
            p2=folder/"RESULT-MEM2.bin"
            p1.write_bytes(b"A"*64)
            p2.write_bytes(b"B"*96)
            hashes={"MEM1":hashlib.sha256(b"A"*64).hexdigest(),
                    "MEM2":hashlib.sha256(b"B"*96).hexdigest()}
            real_hash=follow._hash
            changed=False

            def overwrite_after_initial_hash(path):
                nonlocal changed
                digest=real_hash(path)
                if not changed and path==p1:
                    changed=True
                    p1.write_bytes(b"Z"*64)
                return digest

            with patch.dict(follow.SIZES,{"MEM1":64,"MEM2":96},clear=True), \
                    patch.object(follow,"_hash",side_effect=overwrite_after_initial_hash):
                with self.assertRaisesRegex(ValueError, "changed during offline"):
                    follow._phase_read(folder,"RESULT",hashes,source=False)
            self.assertTrue(changed)

    def test_same_sha_replaced_inode_before_map_rejected(self):
        # In the old implementation a same-content rename between
        # pathname SHA and mmap passed both SHA tests but switched objects.
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)
            mem1=folder/"RESULT-MEM1.bin"
            mem2=folder/"RESULT-MEM2.bin"
            replacement=folder/"private-replacement.tmp"
            mem1.write_bytes(b"A"*64)
            mem2.write_bytes(b"B"*96)
            replacement.write_bytes(b"A"*64)  # identical content, new inode
            original_inode=follow._file_identity(mem1,64)
            hashes={"MEM1":hashlib.sha256(b"A"*64).hexdigest(),
                    "MEM2":hashlib.sha256(b"B"*96).hexdigest()}
            true_hash=follow._hash
            swapped=False

            def swap_after_sha(path):
                nonlocal swapped
                digest=true_hash(path)
                if path==mem1 and not swapped:
                    os.replace(replacement,mem1)
                    swapped=True
                return digest

            with patch.dict(follow.SIZES,{"MEM1":64,"MEM2":96},clear=True), \
                    patch.object(follow,"_hash",side_effect=swap_after_sha):
                with self.assertRaisesRegex(ValueError,"changed during offline"):
                    follow._phase_read(folder,"RESULT",hashes,source=False)
            self.assertTrue(swapped)
            self.assertNotEqual(original_inode,follow._file_identity(mem1,64))

    def test_private_bank_symlink_identity_rejected_without_following_link(self):
        # Portable across Windows where creating test symlinks may need
        # administrative privileges: the no-follow stat mode is simulated.
        fake=type("FakeStat",(),{"st_mode":stat.S_IFLNK|0o777,
                                "st_size":64,"st_dev":1,"st_ino":123})()
        with patch.object(follow.os,"stat",return_value=fake) as spy:
            with self.assertRaisesRegex(ValueError,"changed during offline"):
                follow._file_identity(Path("PRIVATE-NO-FOLLOW-SENTINEL"),64)
            self.assertEqual(spy.call_args.kwargs,{"follow_symlinks":False})

    def test_terminal_rehash_rejects_pre_bank_changed_after_base_audit(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            folder=root/"SHOT-synthetic-PRIVATE"
            folder.mkdir()
            hashes={}
            for phase in ("PRE","POST","RESULT"):
                hashes[phase]={}
                for name,size,byte in (("MEM1",64,b"A"),("MEM2",96,b"B")):
                    raw=byte*size
                    (folder/f"{phase}-{name}.bin").write_bytes(raw)
                    hashes[phase][name]=hashlib.sha256(raw).hexdigest()
            typed=doc(settled=False,result=True)
            typed["checkpoints"]["RESULT"]["sha256"]=hashes["RESULT"]
            (folder/follow.MANIFEST).write_text(json.dumps(typed),encoding="utf-8")
            original={"PRE":{"sha256":hashes["PRE"]},
                      "POST":{"sha256":hashes["POST"]}}

            def fake_result_phase(_folder,phase,hashset,*,source):
                self.assertEqual(phase,"RESULT")
                self.assertFalse(source)
                # Earlier PRE audit succeeded, then a same-sized private
                # bank was replaced before the final report was returned.
                (folder/"PRE-MEM1.bin").write_bytes(b"X"*64)
                return None,None,hashset

            with patch.dict(follow.SIZES,{"MEM1":64,"MEM2":96},clear=True), \
                    patch.object(follow.selected,"DATA_ROOT",root), \
                    patch.object(follow.prepost,"run_local",return_value=BASE), \
                    patch.object(follow.prepost,"_manifest",return_value=original), \
                    patch.object(follow,"_phase_read",side_effect=fake_result_phase):
                with self.assertRaisesRegex(ValueError,"changed during offline"):
                    follow.run_local(folder)

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
