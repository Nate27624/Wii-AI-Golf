#!/usr/bin/env python3
"""Resume a single SHA-sealed aborted source-rooted Wii Golf club validation.

Original local private stream is NEVER changed. Resume only original 12-phase
prefix that abstained at T1_DRIVER because visible club was IRON, not DRIVER.
Require same running Dolphin, observed frame continuity, matching source
selector pointer, unchanged scene/hole/ball, and operator attestation.
No memory writes, controller injection, A, swing, menu navigation, or savestate.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
import p0_live_club_selector_global_private as live

STUDY_PROTOCOL="p0-four-state-live-v1"
RESUME_PROTOCOL="p0-four-state-live-resume-v1"
PREVIOUS_STATUS="ABSTAIN_OPERATOR_VISIBLE_CLUB_MISMATCH"
PREVIOUS_COUNT=12
LAST_PHASE="T1_IRON"
MAX_PRIVATE_BYTES=100_000


def require(ok,code):
    live.require(ok,code)


def load_prior(folder:Path):
    """Reject modified, truncated, wrong study, cross-branch, or bad phases."""
    folder=folder.resolve()
    require(folder.is_dir() and folder.name.endswith("-PRIVATE"),
            "PRIVATE_PRIOR_STUDY_FOLDER_INVALID")
    require(not folder.is_relative_to(ROOT.resolve()),
            "PRIOR_RECORD_MUST_NOT_BE_IN_GIT")
    manifest_file=folder/"manifest-PRIVATE.json"
    event_file=folder/"events-PRIVATE.jsonl"
    require(manifest_file.is_file() and event_file.is_file(),
            "PRIOR_PRIVATE_RECORD_MISSING")
    raw=event_file.read_bytes()
    require(0<len(raw)<=MAX_PRIVATE_BYTES,"PRIOR_EVENT_SIZE_INVALID")
    manifest=json.loads(manifest_file.read_text("utf-8"))
    require(type(manifest) is dict
            and manifest.get("protocol")==STUDY_PROTOCOL
            and manifest.get("source_global_slot")==hex(live.GLOBAL_SLOT)
            and manifest.get("original_source_public_function")=="fn_802A9BC8"
            and manifest.get("number_of_phases_completed")==PREVIOUS_COUNT
            and manifest.get("result",{}).get("status")==PREVIOUS_STATUS
            and manifest.get("training_approved") is False,
            "PRIOR_MANIFEST_NOT_APPROVED_FOR_RESUME")
    digest=sha256(raw).hexdigest()
    require(manifest.get("private_event_sha256")==digest,
            "PRIOR_PRIVATE_SHA_MISMATCH")
    lines=raw.decode("utf-8").splitlines()
    require(len(lines)==PREVIOUS_COUNT,"PRIOR_EVENT_COUNT_MISMATCH")
    events=[json.loads(line) for line in lines]
    stages=live.stages()
    require([e.get("phase") for e in events]==
            [p for p,_,_ in stages[:PREVIOUS_COUNT]],
            "PRIOR_PHASE_PREFIX_MISMATCH")
    owner=None
    end=-1
    for e,(_,target,_) in zip(events,stages):
        require(type(e) is dict and set(("phase","club","index",
                                         "selector_owner","frame_start",
                                         "frame_end")).issubset(e),
                "PRIOR_ROW_SCHEMA_INVALID")
        club=e["club"]
        require(type(club) is str and club in live.CLUBS
                and (target is None or target==club),
                "PRIOR_VISIBLE_CLUB_LABEL_INVALID")
        index=e["index"]
        p=e["selector_owner"]
        require(type(index) is int and 0<=index<=3
                and type(p) is int and live.source.in_bank(p,0x20)
                and p!=0,
                "PRIOR_INDEX_OR_RECEIVER_INVALID")
        if owner is None:owner=p
        require(p==owner,"PRIOR_SOURCE_RECEIVER_CHANGED")
        start=e["frame_start"]
        stop=e["frame_end"]
        require(type(start) is int and type(stop) is int
                and end<start<=stop,"PRIOR_FRAME_SEQUENCE_INVALID")
        end=stop
    require(events[-1]["phase"]==LAST_PHASE
            and events[-1]["club"]=="IRON",
            "PRIOR_ABORT_CHECKPOINT_NOT_IRON")
    quick=live.analyze_quick(events[:5])
    require(quick["status"]=="QUICK_DPAD_FOUR_STATE_CANDIDATE_SUPPORTED",
            "PRIOR_QUICK_CONTROLS_NOT_SUPPORTED")
    training={}
    for e in events:
        if e["phase"].startswith("T0_"):
            training[e["club"]]=e["index"]
    require(set(training)==set(live.CLUBS)
            and set(training.values())==set(range(4)),
            "PRIOR_TRAINING_MAP_NOT_FOUR_UNIQUE")
    for e in events:
        if e["phase"].startswith("T1_"):
            require(training[e["club"]]==e["index"],
                    "PRIOR_SECOND_PASS_MISMATCH")
    require(events[-1]["index"]==training["IRON"],
            "PRIOR_LAST_CLUB_NOT_IRON")
    return events,manifest,digest,training


def finalize(prior,extra,prior_sha):
    require([e["phase"] for e in extra]==
            [phase for phase,_,_ in live.stages()[PREVIOUS_COUNT:]],
            "RESUMED_PHASE_SUFFIX_MISMATCH")
    combined=prior+extra
    result=live.analyze(combined)
    result["operator_attested_same_dolphin_session"]=True
    result["session_continuity_checked_by_frame_and_pointer"]=True
    result["exact_session_identity_not_native_verified"]=True
    result["prior_sha256"]=prior_sha
    result["original_mismatch_record_preserved"]=True
    result["heldout_predictions_before_operator_reveal"]=True
    result["game_club_id_verified"]=False
    result["training_approved"]=False
    return result


def run(args,rpc_class=None):
    from contextlib import nullcontext
    if rpc_class is None:
        from wii_ai_golf.integration.rpc import FelkRPC
        rpc_class=FelkRPC
    prior,old_manifest,prior_sha,training=load_prior(args.resume)
    folder=args.private_root.resolve()
    require(not folder.is_relative_to(ROOT.resolve()) and
            folder!=args.resume.resolve(),"PRIVATE_OUTPUT_ROOT_UNSAFE")
    folder=folder/("p0-club-four-state-resume-"+
                   datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                   +"-"+uuid.uuid4().hex[:8]+"-PRIVATE")
    folder.mkdir(mode=0o700,parents=True,exist_ok=False)
    # Keep original evidence intact, and copy the *validated* prefix
    # to a new append-only evidence stream.
    event_path=folder/"events-PRIVATE.jsonl"
    extra=[]
    result={"status":"ABSTAIN_NOT_STARTED","training_approved":False}
    with event_path.open("x",encoding="utf-8") as out:
        for e in prior:
            out.write(json.dumps(e,separators=(",",":"))+"\n")
        out.flush()
        try:
            print("RESUMING ONLY T1_DRIVER + FOUR HELDOUT PHASES.")
            print("This requires the SAME Dolphin session and same Golf hole.")
            print("Do not load states, press A or swing. No automated input.")
            ready=input("Dolphin unchanged since abort? Current club IRON visible? Type SAME: ")
            require(ready.strip().upper()=="SAME",
                    "OPERATOR_DID_NOT_ATTEST_SAME_SESSION")
            with rpc_class(port=args.port,timeout_s=15.0) as rpc:
                pong=rpc.call("bridge.ping",[])
                require(isinstance(pong,dict)
                        and isinstance(pong.get("bridge_version"),str),
                        "BRIDGE_PING_INVALID")
                snap=live.source.take_snapshot(rpc)
                identity=snap["identity"]
                ball=rpc.call("memory.read_bytes",[identity[7]+0x30,12])
                require(type(ball) is str and len(ball)==24,
                        "LIVE_BALL_BASELINE_INVALID")
                owner=prior[0]["selector_owner"]
                check=live.bracketed_index(rpc,identity,ball,
                                          expected_owner=owner)
                require(check["index"]==training["IRON"],
                        "CURRENT_CLUB_NOT_LAST_PRIOR_IRON")
                require(check["frame_start"]>prior[-1]["frame_end"],
                        "DOLPHIN_FRAME_DID_NOT_ADVANCE")
                last_frame=check["frame_end"]
                for phase,target,instruction in live.stages()[PREVIOUS_COUNT:]:
                    print("\n"+phase+": "+instruction)
                    if target is not None:
                        print("Select visible "+target+" with D-pad, NO A/swing.")
                    else:
                        print("Secretly select one of DRIVER / IRON / WEDGE / PUTTER.")
                        print("Write down the actual club; reveal it AFTER prediction.")
                    arm=input("Once ready, type READY (or STOP): ")
                    require(arm.strip().upper()=="READY",
                            "OPERATOR_CANCELLED")
                    if target is not None:
                        label=live.correct_label(input("Confirm ACTUALLY visible club: "))
                        require(label==target,
                                "OPERATOR_VISIBLE_CLUB_MISMATCH")
                    sample=live.bracketed_index(
                        rpc,identity,ball,expected_owner=owner)
                    require(sample["frame_start"]>last_frame,
                            "RESUME_FRAME_ORDER_INVALID")
                    last_frame=sample["frame_end"]
                    if target is None:
                        prediction=next(
                            (c for c,v in training.items() if v==sample["index"]),
                            "UNKNOWN")
                        print("READ-ONLY INDEX:",sample["index"],
                              "PREDICTED CLUB:",prediction)
                        label=live.correct_label(
                            input("Reveal club you wrote down BEFORE prediction: "))
                    event={"phase":phase,"club":label,**sample}
                    extra.append(event)
                    out.write(json.dumps(event,separators=(",",":"))+"\n")
                    out.flush()
                    print("Saved phase "+phase+" index "+str(sample["index"]))
            result=finalize(prior,extra,prior_sha)
        except (live.Abstain,OSError,ValueError,RuntimeError,TimeoutError,
                EOFError,TypeError,KeyError,IndexError) as e:
            reason=str(e) if isinstance(e,live.Abstain) else type(e).__name__
            result={"status":"ABSTAIN_"+reason,
                    "prior_sha256":prior_sha,
                    "completed_new_phases":len(extra),
                    "game_club_id_verified":False,
                    "training_approved":False}
    manifest={
        "protocol":RESUME_PROTOCOL,
        "original_prior_folder":str(args.resume.resolve()),
        "original_prior_sha256":prior_sha,
        "source_global_slot":hex(live.GLOBAL_SLOT),
        "number_of_prior_phases":len(prior),
        "number_of_new_phases":len(extra),
        "number_of_combined_phases":len(prior)+len(extra),
        "event_sha256":sha256(event_path.read_bytes()).hexdigest(),
        "result":result,
        "training_approved":False,
    }
    (folder/"manifest-PRIVATE.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    print("New private evidence folder:",folder)
    return 0 if result["status"]=="LIVE_FOUR_STATE_CANDIDATE_VALIDATED" else 3


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--resume",type=Path)
    p.add_argument("--private-root",type=Path)
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--selftest",action="store_true")
    a=p.parse_args(argv)
    if a.selftest:
        require(PREVIOUS_COUNT==12 and LAST_PHASE=="T1_IRON"
                and len(live.stages())==17
                and live.GLOBAL_SLOT==0x804BF900,
                "SELFTEST_FAILED")
        print(json.dumps({"status":"SELFTEST_PASS",
                          "native_dolphin_contacted":False,
                          "training_approved":False}))
        return 0
    if a.resume is None or a.private_root is None:
        p.error("--resume PRIVATE_FOLDER and --private-root PATH required")
    try:
        return run(a)
    except (live.Abstain,OSError,ValueError,RuntimeError,TimeoutError,
            EOFError,TypeError,KeyError,IndexError) as e:
        reason=str(e) if isinstance(e,live.Abstain) else type(e).__name__
        print(json.dumps({"status":"ABSTAIN_"+reason,
                          "training_approved":False}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
