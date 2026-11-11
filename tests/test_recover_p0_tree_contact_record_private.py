"""Offline-only regression for recovery of already completed tree-contact shots."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


recovery=load("recover_p0_tree_shots",SCRIPTS/"recover_p0_tree_contact_record_private.py")
base=load("test_record_fixture",ROOT/"tests"/"test_p0_tree_contact_record_private.py")
m=recovery.recorder


def synthetic_session(tmp,include=("wood","leaves","near_miss")):
    private=Path(tmp)/"Wii-AI-Golf-Data"/"captures"
    private.mkdir(parents=True)
    session=private/"tree-contact-20261111T042646Z-64fb3def-PRIVATE"
    session.mkdir()
    observed={
        "wood":("leaves","yes",45,6),
        "leaves":("wood","yes",39,5),
        "near_miss":("none","no",26,4),
    }
    for i,kind in enumerate(include):
        contact,changed,reported_samples,reported_trees=observed[kind]
        folder=session/f"{kind}-{i+1:08x}-PRIVATE"
        folder.mkdir()
        rpc=base.MockFelkRPC()
        identity=m.preflight(rpc)
        samples=[]
        for j in range(3):
            samples.append(m.sample(rpc,identity,j,2))
        raw=folder/"candidate-stream-RAW-PRIVATE.jsonl"
        raw.write_text("".join(json.dumps(s)+"\n" for s in samples),
                       encoding="utf-8")
        manifest={
            "schema_version":1,
            "status":"recorded",
            "trial_intent":kind,
            "operator_observed_contact_region":contact,
            "operator_observed_trajectory_changed":changed,
            "operator_note":"driver" if kind!="wood" else "",
            "trial_has_native_collision_contact_proof":False,
            "guest_physics_frame_atomicity_verified":False,
            "training_approved":False,
            "source_owner_identity_checked":True,
            "source_identity_digest_PRIVATE":identity["source_identity_digest"],
            "source_hole_raw":2,
            "sample_count":3,"tree_snapshot_count":2,
            "video_created":False,"screenshot_count":0,
            "files_private":[{"name":raw.name,
                             "bytes":raw.stat().st_size,
                             "sha256":m.file_sha(raw)}],
        }
        (folder/"trial-summary-PRIVATE.json").write_text(
            json.dumps(manifest),encoding="utf-8")
    return session


class TreeContactRecoveryTests(unittest.TestCase):
    def test_regression_real_trial_intent_wood_leaves_swapped(self):
        records=[
            {"trial_intent":"wood","status":"recorded","sample_count":45,
             "tree_snapshot_count":6,"operator_observed_contact_region":"leaves",
             "operator_observed_trajectory_changed":"yes"},
            {"trial_intent":"leaves","status":"recorded","sample_count":39,
             "tree_snapshot_count":5,"operator_observed_contact_region":"wood",
             "operator_observed_trajectory_changed":"yes"},
            {"trial_intent":"near_miss","status":"recorded","sample_count":26,
             "tree_snapshot_count":4,"operator_observed_contact_region":"none",
             "operator_observed_trajectory_changed":"no"},
        ]
        out=m.summarize_trials(records)
        self.assertEqual(out["trial_intents"],["wood","leaves","near_miss"])
        self.assertEqual(out["total_source_packets"],110)
        self.assertEqual(out["total_94_tree_snapshots"],15)
        self.assertEqual([x["observed_contact_region"] for x in out["trials"]],
                         ["leaves","wood","none"])
        self.assertFalse(out["contact_verified_by_native_code"])
        self.assertFalse(out["training_approved"])

    def test_three_existing_sha_verified_trial_manifests_recover(self):
        with tempfile.TemporaryDirectory() as temp:
            session=synthetic_session(temp)
            report,folder=recovery.recover(session)
            self.assertTrue(folder.samefile(session))
            self.assertTrue(report["recovered_from_original_trial_manifests"])
            self.assertTrue(report["original_private_raw_sha_and_sample_counts_verified"])
            self.assertEqual(report["total_source_packets"],9)
            self.assertEqual(report["total_94_tree_snapshots"],6)
            self.assertEqual(report["recording_session_status"],"complete")
            self.assertEqual(report["trial_intents"],list(m.TYPES))
            self.assertTrue(report["source_owner_identity_equal_across_trials"])
            self.assertFalse(report["contact_impact_frame_verified"])
            self.assertFalse(report["training_approved"])
            self.assertFalse((session/"operator-summary-SAFE.json").exists())

    def test_actual_cli_recovers_once_without_rewriting_originals(self):
        with tempfile.TemporaryDirectory() as temp:
            session=synthetic_session(temp)
            original={p:p.read_bytes() for p in session.rglob("*")
                      if p.is_file()}
            self.assertEqual(recovery.main(["--session",str(session)]),0)
            safe=session/"operator-summary-SAFE.json"
            summary=json.loads(safe.read_text())
            self.assertEqual(len(summary["trials"]),3)
            self.assertFalse(summary["raw_native_bytes_exported"])
            self.assertFalse(summary["contact_verified_by_native_code"])
            self.assertEqual(original,{p:p.read_bytes() for p in original})
            # Never overwrite an already-existing safe summary.
            self.assertEqual(recovery.main(["--session",str(session)]),2)

    def test_corrupt_raw_hash_fails_closed_and_does_not_write_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            session=synthetic_session(temp)
            raw=next(session.glob("wood-*/candidate-stream-RAW-PRIVATE.jsonl"))
            with raw.open("a",encoding="utf-8") as fh:
                fh.write("{}\n")
            with self.assertRaises(ValueError):
                recovery.recover(session)
            self.assertFalse((session/"operator-summary-SAFE.json").exists())

    def test_corrupt_observation_or_training_provenance_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            session=synthetic_session(temp)
            path=next(session.glob("wood-*/trial-summary-PRIVATE.json"))
            record=json.loads(path.read_text())
            record["training_approved"]=True
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                recovery.recover(session)

    def test_incomplete_manifest_count_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            session=synthetic_session(temp)
            path=next(session.glob("leaves-*/trial-summary-PRIVATE.json"))
            record=json.loads(path.read_text())
            record["sample_count"]=10
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                recovery.recover(session)

    def test_unknown_trial_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            session=synthetic_session(temp)
            (session/"extra-deadbeef-PRIVATE").mkdir()
            self.assertEqual(recovery.recover(session)[0]["total_source_packets"],9)
            with self.assertRaises(ValueError):
                m.summarize_trials([{"trial_intent":"tree",
                                     "status":"recorded","sample_count":2,
                                     "tree_snapshot_count":1}])

    def test_recovery_refuses_git_folder_and_cloud_sync(self):
        with self.assertRaises(ValueError):
            recovery.qualified_session(ROOT)
        with tempfile.TemporaryDirectory(prefix="OneDrive-private-") as temp:
            session=synthetic_session(temp)
            with self.assertRaises(ValueError):
                recovery.recover(session)

    def test_recovery_never_uses_live_rpc(self):
        import inspect
        source_text=inspect.getsource(recovery)
        self.assertNotIn("FelkRPC(",source_text)
        self.assertNotIn("memory.read_bytes",source_text)
        self.assertNotIn("trace.submit",source_text)

    def test_partial_one_or_two_trial_session_is_recoverable(self):
        with tempfile.TemporaryDirectory() as temp:
            session=synthetic_session(temp,include=("wood","leaves"))
            r,_=recovery.recover(session)
            self.assertEqual(r["trial_intents"],["wood","leaves"])
            self.assertEqual(r["total_source_packets"],6)


if __name__=="__main__":
    unittest.main()
