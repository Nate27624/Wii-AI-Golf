#!/usr/bin/env python3
"""OFFLINE repair of an already-recorded Wii Golf tree-contact session.

The first wood/leaves/near_miss recorder saved three private trial manifests
and raw streams, then crashed while assembling its aggregate summary because
it read record["kind"] instead of record["trial_intent"]. This tool recovers
the session *without* Dolphin, Felk RPC, controller inputs, RAM reads,
rewriting originals, or a new swing.

Validate private, original files against their SHA-256 manifests and sample
counts. Only the strict allowlisted operator-summary-SAFE.json is newly
created. It has no raw candidate words, addresses, coordinate guesses,
game bytes, or identifiable local filesystem paths. Human-reported contacts
are NEVER promoted to independently source-proven physical collisions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import p0_tree_contact_record_private as recorder

SESSION=re.compile(r"tree-contact-\d{8}T\d{6}Z-[0-9a-f]{8}-PRIVATE\Z",re.ASCII)
SUBDIR=re.compile(r"(wood|leaves|near_miss)-[0-9a-f]{8}-PRIVATE\Z",re.ASCII)
MAX_MANIFEST=65536
MAX_ROW_BYTES=100000
MAX_RAW_SIZE=300*1024*1024
MAX_PACKETS=3000


def regular(path,limit):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected regular unsymlinked private file")
    if path.stat().st_size<=0 or path.stat().st_size>limit:
        raise ValueError("Private source file exceeds expected size")
    return path


def qualified_session(path):
    """No traversal into Git, clouds, symlinks or unrelated local folders."""
    if not SESSION.fullmatch(path.name):
        raise ValueError("Expected an existing named original tree-contact session")
    folder=path.resolve(strict=True)
    if path.is_symlink() or not folder.is_dir():
        raise ValueError("Private session must be a regular directory")
    root=recorder.safe_private_root(folder.parent)
    if folder.parent!=root:
        raise ValueError("Unexpected private capture root")
    if "Wii-AI-Golf-Data" not in folder.parts:
        raise ValueError("Private session must remain in Wii-AI-Golf-Data")
    return folder


def inspect_raw(path,digest,expected_digest):
    if digest!=expected_digest:
        raise ValueError("Original raw candidate SHA differs from manifest")
    packets=0
    trees=0
    first_identity=None
    prior_end=None
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            if len(line)>MAX_ROW_BYTES:
                raise ValueError("Unexpected oversize private candidate row")
            record=json.loads(line)
            if type(record) is not dict or record.get("schema_version")!=1:
                raise ValueError("Unknown source candidate row schema")
            if record.get("sample_index")!=packets:
                raise ValueError("Missing/repeated/out-of-order source packet")
            if record.get("training_approved") is not False or (
                    record.get("contact_detected_by_memory") is not False):
                raise ValueError("Input falsely promotes training or native contact")
            if record.get("not_same_physics_frame_verified") is not True:
                raise ValueError("Missing multi-RPC non-atomicity qualification")
            identity=record.get("source_identity_digest")
            if not isinstance(identity,str) or len(identity)!=64 or any(
                    x not in "0123456789abcdef" for x in identity):
                raise ValueError("Source identity digest absent")
            if first_identity is None:
                first_identity=identity
            elif identity!=first_identity:
                raise ValueError("Mixed ball owners within trial")
            a=record.get("bridge_frame_count_start")
            b=record.get("bridge_frame_count_end")
            if (type(a) is not int or type(b) is not int or
                a<0 or b<a or (prior_end is not None and a<prior_end)):
                raise ValueError("Invalid bounded host/bridge order")
            prior_end=b
            expected={
                "ball_object_candidate_be_hex_PRIVATE":recorder.BALL_BYTES,
                "selected_record_be_hex_PRIVATE":recorder.RECORD_BYTES,
                "nested_translation_candidate_be_hex_PRIVATE":12,
            }
            for name,n in expected.items():
                value=record.get(name)
                if (not isinstance(value,str) or len(value)!=n*2):
                    raise ValueError("Original source object window missing")
                try:
                    bytes.fromhex(value)
                except ValueError as exc:
                    raise ValueError("Source candidate contains invalid native hex") from exc
            tree=record.get("all_94_tree_records_be_hex_PRIVATE")
            if tree is not None:
                if not isinstance(tree,str) or len(tree)!=recorder.TREE_BYTES*2:
                    raise ValueError("Source tree window invalid")
                try:
                    bytes.fromhex(tree)
                except ValueError as exc:
                    raise ValueError("Source tree native hex invalid") from exc
                trees+=1
            packets+=1
            if packets>MAX_PACKETS:
                raise ValueError("Unexpected oversized trial packet count")
    return packets,trees,first_identity


def recover(session):
    folder=qualified_session(session)
    candidates=[p for p in folder.iterdir() if p.is_dir()
                and SUBDIR.fullmatch(p.name)]
    if not 1<=len(candidates)<=3:
        raise ValueError("Expected 1 to 3 recorded private trial folders")
    found={}
    for trial_dir in candidates:
        if trial_dir.is_symlink():
            raise ValueError("Linked private trial directory not allowed")
        kind=SUBDIR.fullmatch(trial_dir.name).group(1)
        if kind in found:
            raise ValueError("Ambiguous duplicate trial intention")
        manifest_path=regular(trial_dir/"trial-summary-PRIVATE.json",MAX_MANIFEST)
        payload=json.loads(manifest_path.read_text(encoding="utf-8"))
        if (not isinstance(payload,dict) or
            payload.get("schema_version")!=1 or
            payload.get("trial_intent")!=kind or
            payload.get("source_owner_identity_checked") is not True or
            payload.get("training_approved") is not False or
            payload.get("trial_has_native_collision_contact_proof") is not False or
            payload.get("guest_physics_frame_atomicity_verified") is not False):
            raise ValueError("Original trial provenance missing or mislabelled")
        if payload.get("status") not in ("recorded","partial_or_abstained"):
            raise ValueError("Unknown original trial result")
        raw=regular(trial_dir/"candidate-stream-RAW-PRIVATE.jsonl",MAX_RAW_SIZE)
        files=payload.get("files_private")
        if not isinstance(files,list) or not files:
            raise ValueError("Original raw file hash manifest absent")
        entry=next((x for x in files if isinstance(x,dict)
                    and x.get("name")==raw.name),None)
        if entry is None:
            raise ValueError("Original raw candidate not inventoried")
        if type(entry.get("bytes")) is not int or entry["bytes"]!=raw.stat().st_size:
            raise ValueError("Original raw byte count changed")
        if not isinstance(entry.get("sha256"),str) or len(entry["sha256"])!=64:
            raise ValueError("Original raw SHA absent")
        digest=recorder.file_sha(raw)
        samples,tree_samples,identity=inspect_raw(raw,digest,entry["sha256"])
        if samples!=payload.get("sample_count") or tree_samples!=payload.get("tree_snapshot_count"):
            raise ValueError("Original sample and tree counts changed")
        if identity!=payload.get("source_identity_digest_PRIVATE"):
            raise ValueError("Original source instance mismatch")
        for item in files:
            if not isinstance(item,dict) or item.get("name") not in (
                    "candidate-stream-RAW-PRIVATE.jsonl","dolphin-window-PRIVATE.mp4"):
                raise ValueError("Unexpected private file manifest entry")
            f=regular(trial_dir/item["name"],MAX_RAW_SIZE*3)
            if (type(item.get("bytes")) is not int or item["bytes"]!=f.stat().st_size
                    or recorder.file_sha(f)!=item.get("sha256")):
                raise ValueError("Original private file changed after recording")
        found[kind]=payload
    order=[k for k in recorder.TYPES if k in found]
    summaries=[found[k] for k in order]
    compact=recorder.summarize_trials(summaries)
    compact["recovered_from_original_trial_manifests"]=True
    compact["original_private_raw_sha_and_sample_counts_verified"]=True
    compact["source_owner_identity_equal_across_trials"]=len(set(
        x["source_identity_digest_PRIVATE"] for x in summaries))==1
    compact["source_hole_raw_equal_across_trials"]=len(set(
        x["source_hole_raw"] for x in summaries))==1
    compact["same_launch_power_verified"]=False
    compact["same_pre_shot_savestate_verified"]=False
    compact["contact_impact_frame_verified"]=False
    compact["raw_native_bytes_exported"]=False
    return compact,folder


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        report,folder=recover(args.session)
        out=folder/"operator-summary-SAFE.json"
        # Preserve any manually edited prior summary, fail rather than overwrite.
        with out.open("x",encoding="utf-8") as f:
            json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
            f.write("\n")
        print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
        print("Recovered safe summary under existing private session:",out.name)
        return 0
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        print("ABSTAIN_RECOVER_TREE_CONTACT_ORIGINALS: "+str(exc),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
