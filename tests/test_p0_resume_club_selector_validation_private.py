"""Synthetic, file-local tests for resuming one partial P0 four-state study."""
from __future__ import annotations
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
script=ROOT/"scripts"/"p0_resume_club_selector_validation_private.py"
spec=importlib.util.spec_from_file_location("resume_club_selector",script)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

MAP={"DRIVER":0,"IRON":1,"WEDGE":2,"PUTTER":3}
FIRST={"B0":"WEDGE","IDLE":"WEDGE","UP":"IRON",
       "DOWN":"WEDGE","AIM":"WEDGE"}


def valid_events():
    records=[]
    for i,(phase,target,_) in enumerate(m.live.stages()[:12]):
        club=target or FIRST[phase]
        records.append({
            "phase":phase,"club":club,"index":MAP[club],
            "frame_start":100+i*20,
            "frame_end":110+i*20,
            "selector_owner":0x9000B000,
            "rejected_player_manager_index":0})
    return records


def write_archive(folder,records,manifest_edits=None):
    folder.mkdir(exist_ok=True)
    raw=("".join(json.dumps(e,separators=(",",":"))+"\n" for e in records)).encode()
    (folder/"events-PRIVATE.jsonl").write_bytes(raw)
    manifest={
        "protocol":m.STUDY_PROTOCOL,
        "original_source_public_function":"fn_802A9BC8",
        "source_global_slot":"0x804bf900",
        "number_of_phases_completed":12,
        "private_event_sha256":sha256(raw).hexdigest(),
        "result":{"status":m.PREVIOUS_STATUS,"training_approved":False},
        "training_approved":False,
    }
    manifest.update(manifest_edits or {})
    (folder/"manifest-PRIVATE.json").write_text(
        json.dumps(manifest)+"\n",encoding="utf-8")
    return sha256(raw).hexdigest()


class TestResumeP0Club(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)/"previous-PRIVATE"
        self.records=valid_events()
        self.original_sha=write_archive(self.folder,self.records)

    def test_valid_partial_archive_admitted_without_modification(self):
        prior,manifest,digest,training=m.load_prior(self.folder)
        self.assertEqual(digest,self.original_sha)
        self.assertEqual(len(prior),12)
        self.assertEqual(training,MAP)
        self.assertEqual(prior[-1]["phase"],"T1_IRON")
        self.assertEqual(sha256((self.folder/"events-PRIVATE.jsonl").read_bytes()).hexdigest(),
                         self.original_sha)

    def test_t1_driver_and_four_hidden_trials_finish(self):
        prior,_,digest,_=m.load_prior(self.folder)
        suffix=[]
        for i,(phase,target,_) in enumerate(m.live.stages()[12:]):
            club=target or ("PUTTER","IRON","DRIVER","WEDGE")[i-1]
            suffix.append({
                "phase":phase,"club":club,"index":MAP[club],
                "selector_owner":0x9000B000,
                "frame_start":400+i*20,
                "frame_end":410+i*20,
            })
        r=m.finalize(prior,suffix,digest)
        self.assertEqual(r["status"],"LIVE_FOUR_STATE_CANDIDATE_VALIDATED")
        self.assertEqual(r["operator_index_map"],MAP)
        self.assertTrue(r["heldout_predictions_before_operator_reveal"])
        self.assertFalse(r["game_club_id_verified"])
        self.assertFalse(r["training_approved"])

    def test_prior_sha_tamper_rejected(self):
        path=self.folder/"events-PRIVATE.jsonl"
        path.write_bytes(path.read_bytes()+b"\n")
        with self.assertRaises(m.live.Abstain):
            m.load_prior(self.folder)

    def test_prior_wrong_abort_reason_rejected(self):
        write_archive(self.folder,self.records,
                      {"result":{"status":"COMPLETE"}})
        with self.assertRaises(m.live.Abstain):
            m.load_prior(self.folder)

    def test_wrong_phase_order_rejected_even_if_sha_updated(self):
        r=valid_events()
        r[7],r[8]=r[8],r[7]
        write_archive(self.folder,r)
        with self.assertRaises(m.live.Abstain):
            m.load_prior(self.folder)

    def test_requested_club_mismatch_rejected_even_if_sha_updated(self):
        r=valid_events()
        r[5]["club"]="IRON"  # T0_DRIVER must be actually Driver
        write_archive(self.folder,r)
        with self.assertRaises(m.live.Abstain):
            m.load_prior(self.folder)

    def test_different_selector_pointer_rejected(self):
        r=valid_events()
        r[8]["selector_owner"]=0x9000C000
        write_archive(self.folder,r)
        with self.assertRaises(m.live.Abstain):
            m.load_prior(self.folder)

    def test_clock_reset_rejected(self):
        r=valid_events()
        r[11]["frame_start"]=1
        r[11]["frame_end"]=2
        write_archive(self.folder,r)
        with self.assertRaises(m.live.Abstain):
            m.load_prior(self.folder)

    def test_positive_prefix_must_have_four_unique_clubs(self):
        r=valid_events()
        r[6]["index"]=0  # T0_IRON equals T0_DRIVER
        write_archive(self.folder,r)
        with self.assertRaises(m.live.Abstain):
            m.load_prior(self.folder)

    def test_invalid_original_source_global_rejected(self):
        write_archive(self.folder,self.records,
                      {"source_global_slot":"0x804bf8d0"})
        with self.assertRaises(m.live.Abstain):
            m.load_prior(self.folder)

    def test_incomplete_suffix_rejected(self):
        prior,_,digest,_=m.load_prior(self.folder)
        with self.assertRaises(m.live.Abstain):
            m.finalize(prior,[],digest)


if __name__=="__main__":
    unittest.main()
