"""Synthetic-only original-live Ball+0x4C selfref test, no emulator."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"


def load(name,p):
    s=importlib.util.spec_from_file_location(name,p)
    mod=importlib.util.module_from_spec(s)
    s.loader.exec_module(mod)
    return mod


m=load("tree_original_selfref",SCRIPTS/"p0_tree_live_ball_selfref_private.py")
fixture=load("selfref_original_fixture",ROOT/"tests"/"test_recover_p0_tree_contact_record_private.py")


def rewrite_session_as_exact_selfref(session):
    for trial in session.glob("*-PRIVATE"):
        if not trial.is_dir():
            continue
        path=trial/"candidate-stream-RAW-PRIVATE.jsonl"
        manifest=trial/"trial-summary-PRIVATE.json"
        if not path.is_file() or not manifest.is_file():
            continue
        records=[json.loads(line) for line in path.read_text().splitlines()]
        for record in records:
            selected=bytes.fromhex(record["selected_record_be_hex_PRIVATE"])
            ball_addr=int.from_bytes(selected[0x88:0x8C],"big")
            ball=bytearray.fromhex(record["ball_object_candidate_be_hex_PRIVATE"])
            ball[0x4C:0x50]=(ball_addr+0x30).to_bytes(4,"big")
            record["ball_object_candidate_be_hex_PRIVATE"]=ball.hex()
        path.write_text("".join(json.dumps(x)+"\n" for x in records))
        item=json.loads(manifest.read_text())
        for file_entry in item["files_private"]:
            if file_entry["name"]==path.name:
                file_entry["bytes"]=path.stat().st_size
                file_entry["sha256"]=m.base.capture.file_sha(path)
        manifest.write_text(json.dumps(item))


class SelfReferenceSourceTests(unittest.TestCase):
    def test_qualified_original_source_selfref_matches_all_packet_pointers(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            rewrite_session_as_exact_selfref(session)
            verified,files=m.base.read_trials(session)
            output=m.analyze(verified,files)
            self.assertTrue(output["all_three_trials_ball_0x4C_exact_selfref_to_0x30"])
            self.assertTrue(output["source_selected_ball_identity_equal_across_trials"])
            self.assertTrue(output[
                "nested_triplet_source_address_is_same_as_ball_0x30_verified"])
            self.assertEqual(output["original_source_ball_packets"],9)
            self.assertFalse(output["training_approved"])

    def test_distinct_valid_nested_ptr_does_not_falsely_establish_selfref(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            recovered,files=m.base.read_trials(session)
            report=m.analyze(recovered,files)
            self.assertFalse(report["all_three_trials_ball_0x4C_exact_selfref_to_0x30"])
            self.assertFalse(report[
                "nested_triplet_source_address_is_same_as_ball_0x30_verified"])
            self.assertFalse(report["nested_is_a_distinct_allocated_position_object_proven"])

    def test_separate_rpc_read_temporally_distinct_is_not_other_object(self):
        ball=bytearray(m.base.capture.BALL_BYTES)
        ball[0x30:0x3C]=struct.pack(">fff",1.,2.,3.)
        target=0x90008000
        ball[0x4C:0x50]=(target+0x30).to_bytes(4,"big")
        record=bytearray(m.base.capture.RECORD_BYTES)
        record[0x88:0x8C]=target.to_bytes(4,"big")
        rows=[]
        for i in range(4):
            b=bytearray(ball)
            b[0x30:0x3C]=struct.pack(">fff",float(i),2.,3.)
            rows.append({
                "ball_object_candidate_be_hex_PRIVATE":b.hex(),
                "selected_record_be_hex_PRIVATE":record.hex(),
                "nested_translation_candidate_be_hex_PRIVATE":
                    struct.pack(">fff",float(i+1),2.,3.).hex(),
            })
        report=m.audit_trial(rows)
        self.assertTrue(report[
            "source_ball_0x4C_points_exactly_to_ball_0x30_all_original_packets"])
        self.assertEqual(report[
            "same_address_separate_rpc_nested_vs_ball_0x30_while_moving"][
                "active_exact_same_packet_matches"],0)
        self.assertFalse(report["ball_world_position_or_velocity_verified"])

    def test_corrupt_invalid_pointer_refuses(self):
        a=0x90008000
        self.assertTrue(m.pointer_gate(a,a+0x30))
        self.assertFalse(m.pointer_gate(a,a+0x40))
        with self.assertRaises(ValueError):
            m.pointer_gate(a,0x30000000)
        with self.assertRaises(ValueError):
            m.pointer_gate(0x30000000,a+0x30)

    def test_sha_mismatch_refuses_no_partial_safe_file(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            path=next(session.glob("wood-*/candidate-stream-RAW-PRIVATE.jsonl"))
            with path.open("a") as f:
                f.write("{}\n")
            self.assertEqual(m.main(["--session",str(session)]),2)
            self.assertFalse((session/"tree-contact-ball-selfref-SAFE.json").exists())

    def test_main_preserves_original_private_raw_files(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            rewrite_session_as_exact_selfref(session)
            originals={p:p.read_bytes() for p in session.rglob("*") if p.is_file()}
            self.assertEqual(m.main(["--session",str(session)]),0)
            safe=session/"tree-contact-ball-selfref-SAFE.json"
            self.assertTrue(safe.is_file())
            report=json.loads(safe.read_text())
            self.assertTrue(report["all_three_trials_ball_0x4C_exact_selfref_to_0x30"])
            self.assertEqual(originals,{p:p.read_bytes() for p in originals})
            self.assertEqual(m.main(["--session",str(session)]),2)

    def test_safe_report_never_exposes_original_address_or_native_word(self):
        with tempfile.TemporaryDirectory() as temp:
            session=fixture.synthetic_session(temp)
            rewrite_session_as_exact_selfref(session)
            verified,data=m.base.read_trials(session)
            text=json.dumps(m.analyze(verified,data))
            self.assertNotIn("0x90008000",text)
            self.assertNotIn("source_identity_digest_PRIVATE",text)
            self.assertNotIn(str(session),text)
            self.assertNotIn("candidate-stream-RAW-PRIVATE",text)

    def test_cache_lag_counts_only_dynamic_movement_samples(self):
        def t(n):return struct.pack(">fff",float(n),0.,0.)
        true=[t(i) for i in range(4)]
        lag=[t(0)]+true[:-1]
        r=m.consecutive_lag_stats(lag,true,{1,2,3})
        self.assertEqual(r["active_sample_count"],3)
        self.assertEqual(r["active_exact_same_packet_matches"],0)
        self.assertEqual(r["active_exact_matches_to_prior_ball_sample"],3)
        self.assertFalse("physics" in " ".join(r))

    def test_invalid_big_endian_member_span_refuses(self):
        with self.assertRaises(ValueError):
            m.word_at(b"\x00"*4,0x88)
        with self.assertRaises(ValueError):
            m.word_at(b"\x00"*16,1)


if __name__=="__main__":
    unittest.main()
