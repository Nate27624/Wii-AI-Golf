#!/usr/bin/env python3
"""Read-only manual club discovery, Rev1 Golf Hitting the Green.

No game input, swing, memory write, native club-ID proof or training. The
operator changes visible clubs via D-pad if the current game mode permits it.
All source-gated sample reads are sequential and NOT guest-frame atomic.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
import p0_live_directional_aim_series as source
import p0_live_no_contact_compare as base

LAYOUT={"selected_player":(6,51,"MEM2"),
        "golf_config":(2,39,"MEM2"),
        "golf_main":(0,32,"MEM1")}
CLUB_NAMES=("DRIVER","IRON","WEDGE","PUTTER")

class Abstain(RuntimeError): pass
def require(ok,code):
    if not ok:raise Abstain(code)

def labels_from_prompt(answer):
    names=tuple(x.strip().upper() for x in answer.split(","))
    require(2<=len(names)<=4 and len(set(names))==len(names),"NEED_TWO_TO_FOUR_DIFFERENT_CLUBS")
    require(all(x in CLUB_NAMES for x in names),"UNKNOWN_VISIBLE_CLUB_NAME")
    return names

def read_window(rpc,phase,index,*,identity=None,initial_ball=None):
    event=source.packet(rpc,phase,index)
    owner=event["identity"]
    require(identity is None or identity==owner,"SOURCE_IDENTITY_CHANGED")
    ball=event["words"]["selected_ball_plus_0x30"]
    require(initial_ball is None or initial_ball==ball,"SELECTED_BALL_MOVED_STOP")
    groups={}
    for label,(position,n,bank) in LAYOUT.items():
        addr=owner[position]
        require(base.in_bank(addr,4*n,bank),"UNQUALIFIED_"+label.upper())
        values=[]
        for j in range(n):
            val=rpc.call("memory.read_u32",[addr+4*j])
            require(type(val) is int and 0<=val<=0xffffffff,"BAD_READ_"+label.upper())
            values.append(val)
        groups[label]=tuple(values)
    require(source.end_epoch_matches(rpc,owner),"SOURCE_EPOCH_CHANGED")
    return {"phase":phase,"index":index,"identity":owner,"ball":ball,
            "aim":event["words"]["aim_candidate_plus_0x3c"][0],
            "start_ns":event["start_ns"],"end_ns":time.monotonic_ns(),
            "bridge_bracket_NOT_GUEST_PHYSICS":event["frame_bracket"],
            "groups":groups}

def serialize_packet(sample):
    return {"kind":"club_candidate_sample","phase":sample["phase"],
        "sample_index":sample["index"],"start_monotonic_ns":sample["start_ns"],
        "end_monotonic_ns":sample["end_ns"],
        "source_identity_digest_private":sha256(str(sample["identity"]).encode()).hexdigest(),
        "aim_candidate_raw_BE32":f'{sample["aim"]:08x}',
        "bridge_bracket_NOT_GUEST_PHYSICS":sample["bridge_bracket_NOT_GUEST_PHYSICS"],
        "candidate_words_private_be_u32_hex":{
            k:[f'{v:08x}' for v in words] for k,words in sample["groups"].items()},
        "game_club_id_verified":False,"training_approved":False}

def signature(samples):
    require(len(samples)>=2,"WINDOW_TOO_SHORT")
    result={}
    for group,(_,n,_) in LAYOUT.items():
        rows=[sample["groups"][group] for sample in samples]
        require(all(len(x)==n for x in rows),"BAD_SOURCE_WORD_COUNT")
        result[group]=tuple(rows[0][j] if all(x[j]==rows[0][j] for x in rows)
                            else None for j in range(n))
    return result

def train(windows,labels):
    require(len(labels)>=2 and len(set(labels))==len(labels),"INVALID_LABELS")
    fit={}
    for i,label in enumerate(labels):
        require(f"T0_{i}" in windows and f"T1_{i}" in windows,"MISSING_TRAIN_WINDOW")
        fit[label]=(signature(windows[f"T0_{i}"]),signature(windows[f"T1_{i}"]))
    model=[]
    for group,(_,n,_) in LAYOUT.items():
        for j in range(n):
            classes={}
            for label in labels:
                a,b=(s[group][j] for s in fit[label])
                if a is None or b is None or a!=b:break
                classes[label]=a
            if len(classes)==len(labels) and len(set(classes.values()))==len(labels):
                model.append((group,j,classes))
    return model

def filter_aim_confound(model,original,altered):
    a,b=signature(original),signature(altered)
    return [(g,i,patterns) for g,i,patterns in model
            if a[g][i] is not None and b[g][i] is not None and a[g][i]==b[g][i]]

def predict(samples,model):
    if not model:return "UNKNOWN"
    observed=signature(samples)
    votes=[]
    for group,index,patterns in model:
        v=observed[group][index]
        matches=[name for name,bits in patterns.items() if v is not None and v==bits]
        votes.append(matches[0] if len(matches)==1 else "UNKNOWN")
    return votes[0] if len(set(votes))==1 and votes[0]!="UNKNOWN" else "UNKNOWN"

def evaluate(windows,labels):
    model=train(windows,labels)
    require("AIM0" in windows,"AIM_CONTROL_MISSING")
    require(windows["T0_0"][-1]["aim"]!=windows["AIM0"][0]["aim"],
            "AIM_CONTROL_UNCHANGED")
    model=filter_aim_confound(model,windows["T0_0"],windows["AIM0"])
    results={}
    for i,label in enumerate(labels):
        phase=f"V_{i}"
        require(phase in windows,"MISSING_HELDOUT_WINDOW")
        results[label]=predict(windows[phase],model)
    passing=bool(model) and all(results[x]==x for x in labels)
    return (model if passing else []),{
        "aim_control_changed":True,
        "candidate_locations":[f"{g}+0x{i*4:02X}" for g,i,_ in model],
        "heldout_predictions":results,"heldout_pass":passing,
        "inference_enabled":passing,
        "reason":"HELDOUT_PASS_CANDIDATE_ONLY" if passing else
                 "NO_UNCONFOUNDED_CLUB_DISCRIMINATOR"}

def private_folder(root):
    folder=root.resolve(strict=True);repo=ROOT.resolve()
    require(folder.is_dir() and not folder.is_symlink()
            and folder!=repo and repo not in folder.parents,"PRIVATE_ROOT_UNSAFE")
    require(not any(x in str(folder).lower() for x in
                    ("onedrive","dropbox","google drive")),"SYNCED_PRIVATE_ROOT_UNSAFE")
    return folder/("p0-club-blind-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                   +"-"+uuid.uuid4().hex[:8]+"-PRIVATE")

def run(args,rpc_class=None,sleep=time.sleep):
    if rpc_class is None:
        from wii_ai_golf.integration.rpc import FelkRPC
        rpc_class=FelkRPC
    folder=private_folder(args.private_root)
    folder.mkdir(mode=0o700)
    stream=folder/"candidate-events-PRIVATE.jsonl"
    manifest=folder/"manifest-PRIVATE.json"
    status="ABORTED";reason="NOT_STARTED";count=0
    windows={};blind_predictions={};blind_truth={}
    model=[];calibration={"inference_enabled":False,"reason":"NOT_STARTED"}
    labels=();owner=None;ball=None
    print("WII SPORTS CLUB RECOGNITION — NO A, NO SWING, NO AUTOMATED INPUT.")
    print("Rev1 Hitting the Green only. Change clubs with D-pad UP/DOWN IF available.")
    print("If club changes are locked in this training mode, type STOP.")
    try:
        with stream.open("x",encoding="utf-8") as out, rpc_class(port=args.port,timeout_s=15.0) as rpc:
            info=rpc.call("bridge.ping",[])
            require(isinstance(info,dict) and isinstance(info.get("bridge_version"),str),
                    "BRIDGE_PING_FAILED")
            require(input("Ready-to-hit Golf visible, A RELEASED, no swing? Type READY: ").strip()=="READY",
                    "OPERATOR_CANCELLED")
            raw=input("Enter 2-4 visibly selectable clubs (e.g. Wedge,Iron); STOP if locked: ").strip()
            require(raw.upper()!="STOP","NO_SELECTABLE_CLUB_CONTRAST_IN_MODE4")
            labels=labels_from_prompt(raw)
            stages=[]
            for i,c in enumerate(labels):stages.append((f"T0_{i}",c,"training first pass"))
            for i in reversed(range(len(labels))):stages.append((f"T1_{i}",labels[i],"training reverse pass"))
            stages.append(("AIM0",labels[0],"aim-only negative control"))
            for i,c in enumerate(labels):stages.append((f"V_{i}",c,"withheld verification"))
            for i in range(args.blind_windows):stages.append((f"B_{i}",None,"blind"))
            for phase,club,kind in stages:
                if phase=="AIM0":
                    print("\nAIM0: select "+labels[0]+", change AIM left or right while KEEPING same club; NO A/SWING.")
                elif club is None:
                    print("\n"+phase+": SECRETLY select one of "+", ".join(labels)+". Do NOT reveal it yet.")
                else:
                    print("\n"+phase+" ["+kind+"]: SELECT "+club+" manually by D-pad UP/DOWN.")
                print("After YES, switch to Dolphin and select BEFORE HIGH beep. Hold same club HIGH-to-LOW.")
                require(input("Type YES to arm (anything else aborts): ").strip()=="YES","OPERATOR_CANCELLED")
                print("Focus Dolphin now: "+str(args.focus_seconds)+" seconds BEFORE HIGH beep.",flush=True)
                sleep(args.focus_seconds)
                try:
                    import winsound
                    winsound.Beep(1100,250)
                except (ImportError,OSError,RuntimeError):
                    print("HIGH BEEP / START",flush=True)
                windows[phase]=[]
                try:
                    for j in range(args.samples_per_window):
                        e=read_window(rpc,phase,j,identity=owner,initial_ball=ball)
                        if owner is None:owner=e["identity"];ball=e["ball"]
                        windows[phase].append(e)
                        out.write(json.dumps(serialize_packet(e),separators=(",",":"))+"\n")
                        out.flush();count+=1
                finally:
                    try:
                        import winsound
                        winsound.Beep(480,250)
                    except (ImportError,OSError,RuntimeError):
                        print("LOW BEEP / STOP",flush=True)
                print("Captured "+phase+": "+str(len(windows[phase]))+" samples.",flush=True)
                if club is not None:
                    confirmed=input("Which club WAS VISIBLE? Type "+club+" to verify or STOP to abort: ").strip().upper()
                    require(confirmed==club,"OPERATOR_VISIBLE_CLUB_MISMATCH")
                if phase==f"V_{len(labels)-1}":
                    model,calibration=evaluate(windows,labels)
                    print("CALIBRATION",json.dumps(calibration,sort_keys=True),flush=True)
                if club is None:
                    result=predict(windows[phase],model)
                    blind_predictions[phase]=result
                    print("BLIND CLUB PREDICTION "+phase+": "+result,flush=True)
                    truth=input("NOW reveal actual visible club ["+"/".join(labels)+"/UNKNOWN]: ").strip().upper()
                    blind_truth[phase]=truth if truth in labels else "UNKNOWN"
        status="COMPLETE";reason="STUDY_COMPLETED"
    except (Abstain,OSError,ValueError,RuntimeError,TimeoutError,EOFError,TypeError,KeyError,IndexError) as e:
        reason=str(e) if isinstance(e,Abstain) else type(e).__name__
        print("ABSTAIN "+reason,flush=True)
    finally:
        if stream.exists():
            manifest.write_text(json.dumps({"protocol":"p0-club-blind-v1","status":status,
                "reason_code":reason,"sample_packets":count,
                "sha256":sha256(stream.read_bytes()).hexdigest(),"tested_labels":labels,
                "calibration":calibration,"blind_predictions":blind_predictions,
                "blind_truth":blind_truth,"game_club_id_verified":False,
                "guest_physics_step_verified":False,"training_approved":False},indent=2)+"\n",
                encoding="utf-8")
    good=sum(blind_predictions.get(k)==v for k,v in blind_truth.items() if v in labels)
    total=sum(v in labels for v in blind_truth.values())
    print(json.dumps({"status":status,"reason_code":reason,"protocol":"p0-club-blind-v1",
        "samples":count,"tested_labels":labels,"calibration":calibration,
        "blind_predictions":blind_predictions,"blind_truth":blind_truth,
        "blind_correct":good,"blind_labeled":total,
        "game_club_id_verified":False,"training_approved":False},indent=2,sort_keys=True))
    return 0 if status=="COMPLETE" else 3

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root",required=True,type=Path)
    parser.add_argument("--port",type=int,default=55355)
    parser.add_argument("--samples-per-window",type=int,choices=range(2,5),default=2)
    parser.add_argument("--blind-windows",type=int,choices=range(1,9),default=4)
    parser.add_argument("--focus-seconds",type=int,choices=range(5,13),default=8)
    return run(parser.parse_args())

if __name__=="__main__":
    raise SystemExit(main())
