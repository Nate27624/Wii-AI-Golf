"""Synthetic-only, no-Dolphin checks for S002 SHA-gated retrospective."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_a_motion_components_private as study

def event(phase, index, n, *, broken=False):
    motion = 1 if phase in ("M0","I1","M1") else 0
    x94 = 0x40000000 if phase in ("AH","AR") else 0x3f800000
    if broken and phase=="AR":
        x94=0x40010000
    fields={
        "selected_record_plus_0x30":[0x3f800000+motion,0,0],
        "selected_record_plus_0x90":[0x3eaa0000+n,x94,0x40000000],
        "aim_candidate_plus_0x3c":[0x3ff00000],
    }
    return {"phase":phase,"sample_index":index,
        "monotonic_start_ns":100000*n,
        "monotonic_end_ns":100000*n+50,
        "source_owner_pointer_digest_private":"same-fixture-owner",
        "candidate_words_private_be_u32_hex":{
            key:[f"{w:08x}" for w in values] for key,values in fields.items()}}
def fixture(folder):
    evs=[]
    for phase in study.PHASES:
        for i in range(8):
            evs.append(event(phase,i,len(evs)))
    for i in range(6):
        evs.append(event("M1",i,len(evs)))
    return store(folder,evs),evs
def store(folder,events):
    stream=folder/study.STREAM
    stream.write_text("\n".join(json.dumps(e) for e in events)+"\n",encoding="utf-8")
    digest=hashlib.sha256(stream.read_bytes()).hexdigest()
    (folder/study.MANIFEST).write_text(json.dumps({
        "status":"ABORTED","protocol":"manual-a-miss-v1",
        "run_samples":46,"private_sha256":digest,
        "training_approved":False}),encoding="utf-8")
    return digest

class RetrospectiveTests(unittest.TestCase):
    def test_good_source_controls_and_quarantined_hit(self):
        with tempfile.TemporaryDirectory() as temp:
            digest,_=fixture(Path(temp))
            events,sha=study.load(Path(temp),None,digest)
            report=study.analyze(events,sha)
            self.assertEqual(report["total_packets"],46)
            self.assertFalse(report["quarantined_M1"]["used_in_controls"])
            self.assertEqual(report["quarantined_M1"]["packets"],6)
            self.assertEqual(report["per_component"]["selected_record_plus_0x30"]
                ["record_plus_0x30"]["M0"]["different_from_I0_first_count"],8)
            self.assertEqual(report["per_component"]["selected_record_plus_0x90"]
                ["record_plus_0x90"]["I0"]["adjacent_word_transitions"],7)
            self.assertTrue(report["phase_boundary_equality"][0]["x94_changed_while_aim_same"])
            self.assertFalse(report["training_approved"])
    def test_sha_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture(Path(temp))
            with self.assertRaisesRegex(study.Abstain,"sha256"):
                study.load(Path(temp),None,"0"*64)
    def test_missing_sample_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            _,events=fixture(Path(temp))
            digest=store(Path(temp),events[:-1])
            with self.assertRaisesRegex(study.Abstain,"incorrect_packet_count"):
                study.load(Path(temp),None,digest)
    def test_source_identity_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            _,events=fixture(Path(temp))
            events[15]["source_owner_pointer_digest_private"]="changed"
            digest=store(Path(temp),events)
            with self.assertRaisesRegex(study.Abstain,"source_identity_changed"):
                study.load(Path(temp),None,digest)
    def test_exact_sha_selection_and_duplicate_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"p0-manual-a-fixture-1-PRIVATE"
            p.mkdir();digest,_=fixture(p)
            events,_=study.load(None,Path(temp),digest)
            self.assertEqual(len(events),46)
            q=Path(temp)/"p0-manual-a-fixture-2-PRIVATE"
            q.mkdir();fixture(q)
            with self.assertRaisesRegex(study.Abstain,"not_unique"):
                study.load(None,Path(temp),digest)
    def test_all_output_contains_no_raw_memory_or_M1_control(self):
        with tempfile.TemporaryDirectory() as temp:
            digest,_=fixture(Path(temp))
            evs,_=study.load(Path(temp),None,digest)
            report=study.analyze(evs,digest)
            self.assertNotIn("M1",report["per_component"]["selected_record_plus_0x30"]
                ["record_plus_0x30"])
            self.assertNotIn("candidate_words_private_be_u32_hex",json.dumps(report))
            self.assertEqual(len(report["phase_boundary_equality"]),4)
    def test_phase_swap_abstains_even_if_hash_recomputed(self):
        with tempfile.TemporaryDirectory() as temp:
            _,events=fixture(Path(temp))
            events[0]["phase"]="AH"
            digest=store(Path(temp),events)
            with self.assertRaisesRegex(study.Abstain,"unexpected_phase_order"):
                study.load(Path(temp),None,digest)
if __name__=="__main__":
    unittest.main()
