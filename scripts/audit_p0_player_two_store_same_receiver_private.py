"""Original-B0 source-only possible same-object link: +0x30(r30) to +0x90(r31).

Checks Player +0x2008 stfs f0,+0x30(r30), +0x201C mr r3,r30, exact
BL +0x2024 -> +0x1BD4, whose callee source copy and +0x90 store
are separately validated by #244. Branch-possible != runtime execution.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

import audit_ball_xyz_source_callers_private as owner
import audit_p0_r31_qualified_local_paths_private as callee
import audit_p0_player_r31_two_callsite_r3_private as caller
import audit_p0_r31_local_cfg_private as flow

BASE=callee.START
BEGIN=BASE+0x2008
CALL=BASE+0x2024
COUNT=(CALL-BEGIN)//4+1
TARGET=BASE+0x1BD4


def _relative(pc:int)->str:
    return f"+0x{pc-BASE:04X}"


def _write_r30(word:int)->str:
    """Known r30 writers, possible r30 writers, otherwise no recognized writer."""
    op=word>>26
    rt=(word>>21)&31
    ra=(word>>16)&31
    xo=(word>>1)&1023
    if op==31:
        if xo==444: return "definite" if ra==30 else "none"
        return "unknown" if rt==30 or ra==30 else "none"
    if op in (7,8,12,13,14,15,32,34,40,42):
        return "definite" if rt==30 else "none"
    if op in (20,21,22,23,24,25,26,27,28,29):
        return "definite" if ra==30 else "none"
    if op in (33,35,41,43):
        return "definite" if rt==30 or ra==30 else "none"
    if op in (37,39,45,49,51,53,55):
        return "definite" if ra==30 else "none"
    if op==46:
        return "definite" if rt<=30 else "none"
    if op in (4,10,11,16,17,18,19,36,38,44,47,48,50,52,54,59,63):
        return "none"
    return "unknown"


def _mr_r3_r30(word:int)->bool:
    return (word>>26==31 and ((word>>1)&1023)==444 and
            ((word>>21)&31)==30 and ((word>>16)&31)==3 and
            ((word>>11)&31)==30 and word&1==0)


def analyze(data:bytes)->dict:
    if type(data) is not bytes or len(data)!=COUNT*4:
        raise ValueError("wrong caller source code length")
    words={BEGIN+i*4:struct.unpack_from(">I",data,i*4)[0]
           for i in range(COUNT)}
    if not (words[BEGIN]>>26==52 and
            ((words[BEGIN]>>21)&31)==0 and
            ((words[BEGIN]>>16)&31)==30 and
            (words[BEGIN]&65535)==0x30):
        raise ValueError("exact float store absent")
    if not _mr_r3_r30(words[BASE+0x201C]):
        raise ValueError("exact r30->r3 copy absent")
    if caller.prior.bl_target(CALL,words[CALL])!=TARGET:
        raise ValueError("direct call target drift")
    stack=[(BEGIN+4,"intact","other")]
    visited=set()
    reached=set()
    reasons=set()
    edges=set()
    while stack:
        pc,r30,r3=stack.pop()
        if (pc,r30,r3) in visited:continue
        visited.add((pc,r30,r3))
        if len(visited)>160:
            raise ValueError("local path state budget exceeded")
        if pc==CALL:
            reached.add((r30,r3))
            continue
        if pc not in words:
            reasons.add("local_branch_exits_window")
            continue
        word=words[pc]
        branch=flow._branch(pc,word)
        if branch:
            kind,dest=branch
            edges.add((_relative(pc),kind,
                       _relative(dest) if dest in words else None))
            if kind=="conditional_branch":
                stack.extend(((pc+4,r30,r3),(dest,r30,r3)))
            elif kind=="unconditional_branch":
                stack.append((dest,r30,r3))
            elif kind in ("linked_call","linked_conditional_call"):
                reasons.add("unverified_intervening_call_effect")
                stack.append((pc+4,"unknown","unknown"))
                if kind=="linked_conditional_call":
                    stack.append((pc+4,r30,r3))
            else:
                reasons.add("indirect_or_system_control")
            continue
        effect=_write_r30(word)
        if effect=="definite":
            r30="changed"
        elif effect=="unknown":
            r30="unknown"
            reasons.add("unrecognized_possible_r30_write")
        if _mr_r3_r30(word):
            r3=("same_as_prior_store_base" if r30=="intact" else "unknown")
        else:
            e=caller.r3_event(word)
            if e is not None:
                r3=("other" if e["definite_r3_write"] else "unknown")
                if not e["definite_r3_write"]:
                    reasons.add("unrecognized_possible_r3_write")
        stack.append((pc+4,r30,r3))
    return {
        "kind":"S002-P0-PLAYER-TWO-FLOAT-STORE-SAME-RECEIVER-LOCAL-POSSIBILITY",
        "player_source_first_store":"+0x2008",
        "first_store_syntax":"stfs f0,+0x30(r30)",
        "caller_r30_to_r3_copy_site":"+0x201C",
        "caller_direct_BL_site":"+0x2024",
        "callee_candidate_entry":"+0x1BD4",
        "caller_local_path_reaches_BL":bool(reached),
        "caller_path_forwards_original_r30_to_callee_possible":
            any(r3=="same_as_prior_store_base" for _,r3 in reached),
        "caller_path_has_unresolved_r3_or_r30_possible":
            any(r3=="unknown" or r30=="unknown" for r30,r3 in reached),
        "caller_path_r30_changed_before_call_possible":
            any(r30=="changed" for r30,_ in reached),
        "caller_branch_edges":[{
            "source_site":pc,"kind":kind,"target_within_slice":dst}
            for pc,kind,dst in sorted(edges)],
        "caller_incomplete_reasons":sorted(reasons),
        "callee_local_path_must_be_checked_separately":True,
        "same_object_runtime_write_proven":False,
        "true_function_boundary_or_typed_receiver_verified":False,
        "store_executed_in_same_shot_verified":False,
        "physical_xyz_velocity_power_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }


def audit(session:Path,data_root:Path)->dict:
    # Both previous source audits verify exact immutable original B0 bytes
    # and direct/callee PPC sites before accessing this tiny caller window.
    called=callee.audit(session,data_root)
    two=caller.audit(session,data_root)
    if len(two["source_calls"])!=2 or not called["source_exact_copy_store_verified"]:
        raise ValueError("source provenance changed")
    source=owner.checked_private_b0(session,data_root)
    with source.open("rb") as fp:
        fp.seek(BEGIN-owner.MEM1_START)
        block=fp.read(COUNT*4)
    if owner.checked_private_b0(session,data_root)!=source:
        raise ValueError("source memory changed")
    out=analyze(block)
    downstream=called["no_callee_preservation_assumed"]
    out["callee_local_source_path_preserves_copy_possible"] = bool(
        downstream["store_path_with_copy_still_intact_possible"])
    out["joined_two_store_source_possible_only"] = bool(
        out["caller_path_forwards_original_r30_to_callee_possible"] and
        out["callee_local_source_path_preserves_copy_possible"])
    out["original_B0_SHA_and_Rev1_verified_before_after"]=True
    return out


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    default=Path(__file__).resolve().parents[2]/"Wii-AI-Golf-Data"
    p.add_argument("--data-root",type=Path,default=default)
    p.add_argument("--private-session",type=Path)
    args=p.parse_args(argv)
    try:
        out=audit(args.private_session or args.data_root/"ball-study-20261027-212633",
                  args.data_root)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,AttributeError,
            owner.UntrustedInput,struct.error):
        print("P0 two Player store link ABSTAIN: original B0 SHA or source/CFG gate failed; no private data disclosed.",file=sys.stderr)
        return 2
    print(json.dumps(out,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
