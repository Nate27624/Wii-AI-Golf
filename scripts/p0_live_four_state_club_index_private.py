#!/usr/bin/env python3
"""P0 live selected-club FOUR-STATE index validation, operator-controlled.

Read-only Felk RPC, rev1 Hitting-the-Green source-gated PlayerManager pointer.
This is NOT native r13 register access: the independent existing validated
global slot PLAYER_MANAGER_STATIC=0x804BF8D0 is the SOURCE-CANDIDATE for
r13-0x5A80. No native pointer root/visible-club promotion without live tests.
No Dolphin launch, button injection, A press, swing, savestate, or RAM write.
Private event stream stays outside git; stdout exposes labels/index only.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import p0_live_no_contact_compare as source

CLUBS = ("DRIVER", "IRON", "WEDGE", "PUTTER")
FIELD_OFFSET = 0x1C
GLOBAL_SLOT = source.PLAYER_MANAGER_STATIC
INFERRED_R13_IF_ROOT_MATCHES = GLOBAL_SLOT + 0x5A80

class Abstain(RuntimeError):
    pass

def require(ok: bool, reason: str):
    if not ok:
        raise Abstain(reason)

def word(rpc, addr):
    require(source.in_bank(addr), "UNQUALIFIED_READ_ADDRESS")
    v = rpc.call("memory.read_u32", [addr])
    require(type(v) is int and 0 <= v <= 0xFFFFFFFF, "UNTYPED_MEMORY_READ")
    return v

def correct_label(raw):
    label = raw.strip().upper()
    require(label in CLUBS, "INVALID_OR_UNKNOWN_VISIBLE_CLUB")
    return label

def bracketed_index(rpc, identity, initial_ball):
    mgr, scene, config, field, pm, player, record, ball, nested, start, tee, pin, pinvec, hole = identity
    before = rpc.call("frame.get_count", [])
    require(type(before) is int and before >= 0, "INVALID_START_FRAME")
    # Crucial: the already source-gated PlayerManager static slot, NOT an
    # arbitrary MEM2 offset chosen from correlation.
    require(word(rpc, GLOBAL_SLOT) == pm, "PLAYER_MANAGER_GLOBAL_ROOT_CHANGED")
    require(word(rpc, source.SCENE_STATIC) == mgr, "GOLF_SCENE_ROOT_CHANGED")
    require(word(rpc, source.CONFIG_STATIC) == config, "CONFIG_ROOT_CHANGED")
    require(word(rpc, mgr+0x18) == 5 and word(rpc, config+0x94) == 4
            and word(rpc, config+0x98) == hole, "GAME_MODE_OR_HOLE_CHANGED")
    require(word(rpc, pm+0x334) == record, "SELECTED_PLAYER_CHANGED")
    # Two samples are sequential, not frame atomic.
    a = word(rpc, pm+FIELD_OFFSET)
    b = word(rpc, pm+FIELD_OFFSET)
    require(a == b, "CLUB_INDEX_UNSTABLE_INSIDE_SAMPLE")
    require(0 <= a <= 3, "CLUB_INDEX_OUTSIDE_SOURCE_BOUNDS")
    raw_ball = rpc.call("memory.read_bytes", [ball+0x30, 12])
    require(isinstance(raw_ball, str) and len(raw_ball)==24
            and raw_ball == initial_ball, "BALL_MOVED_OR_BAD_BYTES")
    require(word(rpc, GLOBAL_SLOT) == pm and
            word(rpc, source.SCENE_STATIC) == mgr and
            word(rpc, config+0x98) == hole, "SOURCE_EPOCH_CHANGED")
    after = rpc.call("frame.get_count", [])
    require(type(after) is int and after >= before, "FRAME_REVERSED")
    return {"index":a,"frame_start":before,"frame_end":after}

def stages():
    result=[("B0",None,"baseline visible club, no input"),
            ("IDLE",None,"no input, no aim change, same club"),
            ("UP",None,"press D-pad UP exactly once; no A/swing"),
            ("DOWN",None,"press D-pad DOWN exactly once; no A/swing"),
            ("AIM",None,"aim ONLY left/right, keep SAME visible club; no A/swing")]
    result += [("T0_"+c,c,"training pass 1") for c in CLUBS]
    result += [("T1_"+c,c,"training pass 2") for c in reversed(CLUBS)]
    result += [("V"+str(i),None,"secret heldout: choose ANY club, do not reveal until AFTER read")
               for i in range(4)]
    return result

def analyze_quick(events):
    require([e["phase"] for e in events]==["B0","IDLE","UP","DOWN","AIM"],
            "QUICK_PHASES_INVALID")
    b0,idle,up,down,aim=events
    checks={
        "idle_same_club_and_index":idle["club"]==b0["club"] and idle["index"]==b0["index"],
        "up_decrements_one_or_stays_at_zero":up["index"]==max(0,idle["index"]-1),
        "down_increments_one_or_stays_at_three":down["index"]==min(3,up["index"]+1),
        "aim_only_same_club_and_index":aim["club"]==down["club"] and aim["index"]==down["index"],
        "up_visible_change_agrees_with_index_change":(
            (up["club"] != idle["club"]) == (up["index"] != idle["index"])),
        "down_visible_change_agrees_with_index_change":(
            (down["club"] != up["club"]) == (down["index"] != up["index"])),
        "at_least_one_direction_changed_the_visible_club":(
            up["club"] != idle["club"] or down["club"] != up["club"]),
    }
    good=all(checks.values())
    return {
        "status":"QUICK_DPAD_FOUR_STATE_CANDIDATE_SUPPORTED" if good else
                 "QUICK_DPAD_FOUR_STATE_CANDIDATE_NOT_SUPPORTED",
        "observed": [{"phase":e["phase"],"club":e["club"],"index":e["index"]}
                     for e in events],
        "controls":checks,
        "quick_test_not_full_four_club_mapping":True,
        "same_live_receiver_as_existing_validated_player_manager":True,
        "native_r13_register_verified":False,
        "game_club_id_verified":False,
        "training_approved":False,
    }


def analyze(events):
    byphase={e["phase"]:e for e in events}
    require(len(byphase)==len(events),"DUPLICATE_PHASE")
    require(set(byphase)=={x[0] for x in stages()},"MISSING_PHASES")
    flags={}
    b0,idle,up,down,aim=(byphase[x] for x in ("B0","IDLE","UP","DOWN","AIM"))
    flags["idle_same_index_and_club"] = (idle["index"]==b0["index"]
                                            and idle["club"]==b0["club"])
    flags["up_one_step_or_bound"] = (up["index"] == max(0,idle["index"]-1))
    flags["down_one_step_or_bound"] = (down["index"] == min(3,up["index"]+1))
    flags["aim_same_index_and_club"] = (aim["index"]==down["index"]
                                            and aim["club"]==down["club"])
    candidate={}
    for c in CLUBS:
        a,b=byphase["T0_"+c],byphase["T1_"+c]
        if a["index"]!=b["index"] or a["club"]!=c or b["club"]!=c:
            flags["two_pass_club_consistency"]=False
            break
        candidate[c]=a["index"]
    else:
        flags["two_pass_club_consistency"]=True
    flags["four_unique_index_values"]=(len(candidate)==4
                                        and set(candidate.values())==set(range(4)))
    flags["up_and_down_visible_labels_consistent"]=(
        up["club"]==next((c for c,v in candidate.items() if v==up["index"]),None)
        and down["club"]==next((c for c,v in candidate.items() if v==down["index"]),None)
    )
    flags["baseline_label_consistent"]=(
        b0["club"]==next((c for c,v in candidate.items() if v==b0["index"]),None)
    )
    verification=[]
    for i in range(4):
        e=byphase["V"+str(i)]
        predicted=next((c for c,v in candidate.items() if v==e["index"]),None)
        verification.append({
            "phase":e["phase"],"predicted_club":predicted,
            "operator_visible_club":e["club"],"pass":predicted==e["club"]
        })
    flags["heldout_four_correct"]=all(v["pass"] for v in verification)
    all_pass=all(flags.values())
    return {
        "status":"LIVE_FOUR_STATE_CANDIDATE_VALIDATED" if all_pass else
                 "LIVE_FOUR_STATE_CANDIDATE_NOT_VALIDATED",
        "source_code_four_state_writer_proven_separately":True,
        "global_slot":hex(GLOBAL_SLOT),
        "r13_inferred_only_not_register_read":hex(INFERRED_R13_IF_ROOT_MATCHES),
        "field_offset":hex(FIELD_OFFSET),
        "operator_index_map":candidate,
        "control_and_holdout_checks":flags,
        "heldout_checks":verification,
        "observed_live_club_index_consistent":all_pass,
        "full_native_register_and_object_identity_proven":False,
        "training_approved":False,
    }

def run(args,rpc_class=None):
    if rpc_class is None:
        from wii_ai_golf.integration.rpc import FelkRPC
        rpc_class=FelkRPC
    require(not args.private_root.resolve().is_relative_to(ROOT.resolve()),
            "PRIVATE_ROOT_MUST_BE_OUTSIDE_REPO")
    folder=args.private_root/("p0-club-four-state-live-"+
         datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")+
         "-"+uuid.uuid4().hex[:8]+"-PRIVATE")
    events=[]
    result={"status":"ABSTAIN_NO_STUDY","training_approved":False}
    reason=""
    stream=folder/"events-PRIVATE.jsonl"
    folder.mkdir(mode=0o700,parents=True)
    print("P0 FOUR-STATE LIVE TEST: operator controls D-pad. NO A/SWING.")
    print("Change clubs in Dolphin, then return to PowerShell for each READY.")
    print("If no valid club change is possible in current mode, type STOP.")
    try:
        with rpc_class(port=args.port,timeout_s=15.0) as rpc:
            info=rpc.call("bridge.ping",[])
            require(isinstance(info,dict) and
                    isinstance(info.get("bridge_version"),str),
                    "BRIDGE_PING_NOT_CONFIRMED")
            require(input("Hitting the Green ready, no ball motion, A RELEASED? Type READY: ").strip().upper()=="READY",
                    "OPERATOR_CANCELLED")
            ref=source.take_snapshot(rpc)
            ident=ref["identity"]
            pm=ident[4]
            require(word(rpc,GLOBAL_SLOT)==pm,"SOURCE_GLOBAL_NOT_PLAYER_MANAGER")
            # Sourced static candidate matches original compiled small-data slot.
            initial_ball=rpc.call("memory.read_bytes",[ident[7]+0x30,12])
            require(isinstance(initial_ball,str) and len(initial_ball)==24,
                    "BAD_SOURCE_BALL_BASELINE")
            require(0<=word(rpc,pm+FIELD_OFFSET)<=3,
                    "SOURCE_INDEX_OUTSIDE_FOUR_STATE")
            with stream.open("x",encoding="utf-8") as out:
                previous_club=None
                for phase,target,instruction in (stages()[:5] if args.quick else stages()):
                    print("\n"+phase+": "+instruction)
                    if target is not None:
                        print("Manually SELECT visible "+target+" by D-pad. NO A.")
                    else:
                        print("Do the described action, then check the visible club.")
                    require(input("Type READY after action (or STOP): ").strip().upper()=="READY",
                            "OPERATOR_CANCELLED")
                    if target is not None:
                        club=correct_label(input("Confirm visible club name: "))
                        require(club==target,"OPERATOR_VISIBLE_CLUB_MISMATCH")
                    else:
                        club=correct_label(input("Type ACTUALLY VISIBLE club now: "))
                    if phase=="IDLE":
                        require(previous_club==club,"IDLE_OPERATOR_CLUB_CHANGED")
                    if phase=="AIM":
                        require(previous_club==club,"AIM_OPERATOR_CLUB_CHANGED")
                    p=bracketed_index(rpc,ident,initial_ball)
                    event={"phase":phase,"club":club,**p}
                    events.append(event)
                    out.write(json.dumps(event,separators=(",",":"))+"\n")
                    out.flush()
                    print("Observed index:",p["index"],"frames:",
                          p["frame_start"],"-",p["frame_end"])
                    previous_club=club
        result=analyze_quick(events) if args.quick else analyze(events)
    except (Abstain,OSError,ValueError,RuntimeError,TimeoutError,
            EOFError,TypeError,KeyError,IndexError) as exc:
        reason=str(exc) if isinstance(exc,Abstain) else type(exc).__name__
        result={"status":"ABSTAIN_"+reason,"training_approved":False}
    finally:
        digest=sha256(stream.read_bytes()).hexdigest() if stream.exists() else None
        manifest={"protocol":"p0-four-state-live-v1",
                  "original_source_public_function":"fn_802A9BC8",
                  "source_global_slot":hex(GLOBAL_SLOT),
                  "private_event_sha256":digest,
                  "number_of_phases_completed":len(events),
                  "result":result,
                  "training_approved":False}
        (folder/"manifest-PRIVATE.json").write_text(
            json.dumps(manifest,indent=2,sort_keys=True)+"\n",
            encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    print("Private archive stored outside Git:",folder)
    return 0 if result.get("status") in (
        "LIVE_FOUR_STATE_CANDIDATE_VALIDATED",
        "QUICK_DPAD_FOUR_STATE_CANDIDATE_SUPPORTED") else 3

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port",type=int,default=55355)
    parser.add_argument("--private-root",type=Path)
    parser.add_argument("--selftest",action="store_true")
    parser.add_argument("--quick",action="store_true",help="Five-phase operator Up/Down/idle/aim smoke test")
    a=parser.parse_args()
    if a.selftest:
        fake=[]
        for phase,club,inst in stages():
            fake.append({"phase":phase,"club":club or "DRIVER","index":0})
        require(len(fake)==17 and FIELD_OFFSET==0x1c and
                GLOBAL_SLOT==0x804BF8D0,"SELFTEST_FAILED")
        print(json.dumps({"status":"SELFTEST_PASS","rpc_used":False,
                          "training_approved":False}))
        return 0
    if a.private_root is None:
        parser.error("--private-root required for live test")
    return run(a)

if __name__=="__main__":
    raise SystemExit(main())
