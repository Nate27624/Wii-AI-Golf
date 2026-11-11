#!/usr/bin/env python3
"""P0 original PPC Ball-cache function bounded static CFG reachability.

The prior SHA-qualified 2026-11-11 native source audit revealed an
UNCONDITIONAL b at Ball+0x2CCC -> Ball+0x2FB8 from the published
0x80299C70 function entry. That jump skips the previously identified
+0xCC writer and +0xFC copy if taken on first entry. Their original
machine-code existence does not establish whether this named function
can later reach them, or whether they live on another basic-block path.

This audit conservatively follows only direct source PPC b/bc edges,
conditional fallthrough, and call-return fallthrough for linked BL,
within the published BOUNDED FUNCTION WINDOW. It stops on recognized
indirect control and leaves those paths unresolved; do not interpret
a missing path as a proof of native unreachability. It does not use
native ROM bytes/PC words in its report, only published Ball source
unit-relative offsets and bounded counts.

Offline private original seven-capture SHA validation, native
scene 94-tree and Ball->KCol anchors re-gated. No emulator, video,
live memory, inputs, guest writes, generated replay, or training.
"""
from __future__ import annotations

import argparse
from collections import deque, Counter
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import p0_ball_cc_global_caller_source_private as old
import p0_ball_cc_fc_copy_receiver_private as source
import p0_ball_cache_r27_lineage_private as lineage
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1=0x80000000
BASE=lineage.SOURCE_BALL
LO=lineage.FN_START
HI=lineage.FN_END
ENTRY=LO
BRANCH_SKIP=BASE+0x2CCC
BRANCH_TARGET=BASE+0x2FB8
SOURCE_SITES=(
    0x2CB8,0x2CCC,0x2CD4,0x2CDC,0x2CEC,0x2CF4,
    0x2CF8,0x2CFC,0x2D00,0x2D04,0x2D14,
    0x2F64,0x2F6C,0x2F98,0x2FA8,0x2FB0,0x2FB8,
)
MAX_NODES=(HI-LO)//4
MAX_ROUTE=32
MAX_BRANCHES=24
MAX_INBOUND=24
MAX_EXIT=10


def src(pc):
    if not BASE <= pc < lineage.inventory.SOURCE_UNITS["Ball"][1] or pc%4:
        raise ValueError("Source site outside original Ball public unit")
    return f"Ball+0x{pc-BASE:04X}"


def signed(value,bits):
    return value-(1<<bits) if value&(1<<(bits-1)) else value


def decode_transfer(pc,w):
    op=w>>26
    if op==18:
        disp=signed(w&0x03FFFFFC,26)
        target=disp if w&2 else pc+disp
        return {"kind":"direct_bl_call" if w&1 else "unconditional_b",
                "target":target,"has_link":bool(w&1)}
    if op==16:
        disp=signed(w&0x0000FFFC,16)
        target=disp if w&2 else pc+disp
        return {"kind":"conditional_bc","target":target,
                "BO":(w>>21)&31,"BI":(w>>16)&31,
                "has_link":bool(w&1)}
    if op==19 and ((w>>1)&1023) in (16,528):
        bo=(w>>21)&31
        # BO=20 is conventional unconditional bclr/bcctr;
        # other BO values may fall through if condition fails.
        # Direct target remains UNKNOWN (LR/CTR source not resolved).
        return {"kind":"indirect_bclr_or_bcctr","target":None,
                "BO":bo,"conditional_fallthrough_possible":bo!=20,
                "has_link":bool(w&1)}
    if op==17:
        return {"kind":"system_call_unknown","target":None,
                "has_link":False}
    return {"kind":"linear_not_decoded_control","target":None,
            "has_link":False}


def edges(pc,read,lo=LO,hi=HI):
    if pc%4 or not lo<=pc<hi:
        raise ValueError("Invalid source CFG site")
    transfer=decode_transfer(pc,read(pc))
    kind=transfer["kind"]
    nex=pc+4
    if kind=="unconditional_b":
        successors=[transfer["target"]]
    elif kind=="conditional_bc":
        # An over-approximation of conditional branch possibilities.
        successors=[transfer["target"],nex]
    elif kind=="direct_bl_call":
        # Calls to other routines are assumed to return here.
        # Do not claim this represents true guest call/return behavior.
        successors=[nex]
    elif kind=="indirect_bclr_or_bcctr":
        successors=[nex] if transfer["conditional_fallthrough_possible"] else []
    elif kind=="system_call_unknown":
        successors=[]
    else:
        successors=[nex]
    bounded=[x for x in successors if lo<=x<hi and x%4==0]
    external=[x for x in successors if not(lo<=x<hi and x%4==0)]
    return bounded,external,transfer


def explore(read,lo=LO,hi=HI,entry=ENTRY):
    if lo%4 or hi%4 or lo>=hi or (hi-lo)//4>4096 or not lo<=entry<hi:
        raise ValueError("Unbounded/incorrect original PPC source CFG")
    q=deque([entry])
    parent={entry:None}
    branch_count=Counter()
    external=[]
    unknown=[]
    inbound=Counter()
    while q:
        pc=q.popleft()
        if len(parent)>(hi-lo)//4:
            raise ValueError("CFG source site exceeds bounded native interval")
        nxt,ext,desc=edges(pc,read,lo,hi)
        branch_count[desc["kind"]]+=1
        if desc["kind"] in ("indirect_bclr_or_bcctr","system_call_unknown"):
            unknown.append(pc)
        if ext:
            external.append((pc,desc["kind"],len(ext)))
        for dest in nxt:
            inbound[dest]+=1
            if dest not in parent:
                parent[dest]=pc
                q.append(dest)
    return {
        "parent":parent,
        "inbound":inbound,
        "branch_count":branch_count,
        "external":external,
        "unknown":unknown,
    }


def route(parent,pc):
    if pc not in parent:
        return None
    output=[]
    seen=set()
    while pc is not None:
        if pc in seen:
            raise ValueError("Corrupted bounded CFG predecessor chain")
        seen.add(pc)
        output.append(pc)
        pc=parent[pc]
    return list(reversed(output))


def nearby_public_branches(read,lo,hi,targets):
    # Counts only static *DIRECT* edges; no resolved LR/CTR targets.
    count={site:[] for site in targets}
    for pc in range(lo,hi,4):
        w=read(pc)
        t=decode_transfer(pc,w)
        if t["kind"] in ("unconditional_b","conditional_bc","direct_bl_call"):
            target=t["target"]
            if target in count:
                count[target].append({
                    "original_Ball_source_relative_site":src(pc),
                    "source_branch_kind":t["kind"],
                    "static_branch_is_observed_dynamic_executed":False,
                })
    return {
        src(target):{
            "direct_branch_source_count":len(items),
            "bounded_original_direct_predecessor_sites":items[:MAX_INBOUND],
            "other_direct_sources_not_displayed":max(0,len(items)-MAX_INBOUND),
            "indirect_predecessors_exhausted":False,
        } for target,items in count.items()
    }


def inspect(read):
    # Qualify the exact control claim surfaced by original report.
    skip=decode_transfer(BRANCH_SKIP,read(BRANCH_SKIP))
    if skip["kind"]!="unconditional_b" or skip["target"]!=BRANCH_TARGET:
        raise ValueError("Native Ball+0x2CCC no longer unconditional skip")
    if BRANCH_TARGET<=BASE+0x2FB0:
        raise ValueError("Native branch not past CC and FC source copy")
    # Guard the two true local native copy sequences from earlier audits.
    cc=source.check_first_copy(read)
    fc=source.check_second_copy(read)
    if not cc["exact_consecutive_native_lfs_stfs_triplet"] or not fc[
            "native_static_copy_of_CC_to_FC_verified"]:
        raise ValueError("Original source exact local copies changed")
    cfg=explore(read)
    p=cfg["parent"]
    sites={}
    for off in SOURCE_SITES:
        pc=BASE+off
        path=route(p,pc)
        edges_with_control=[]
        if path is not None:
            for previous in path:
                kind=decode_transfer(previous,read(previous))["kind"]
                if kind in ("unconditional_b","conditional_bc","direct_bl_call"):
                    edges_with_control.append({
                        "source_site":src(previous),
                        "transfer_kind":kind,
                    })
        sites[f"Ball+0x{off:04X}"]={
            "possible_reach_from_published_80299C70_entry_under_bounded_model":
                path is not None,
            "sample_static_branch_route_from_entry":edges_with_control[:MAX_ROUTE],
            "static_route_instruction_count":len(path)-1 if path else None,
            "actual_guest_execution_proven":False,
            "bounded_no_path_proves_true_unreachability":False,
        }
    return {
        "kind":"P0_ORIGINAL_BALL_CACHE_ENTRY_BRANCH_REACHABILITY_V1",
        "status":"ORIGINAL_SOURCE_SHA_QUALIFIED_BOUNDED_PPC_CFG",
        "source_entry":src(ENTRY),
        "bounded_published_source_window_last_included":src(HI-4),
        "qualified_unconditional_skip":{
            "source_site":src(BRANCH_SKIP),
            "destination_site":src(BRANCH_TARGET),
            "falls_through_into_earlier_CC_copy":False,
            "skips_all_original_CC_and_FC_copy_sites":True,
        },
        "bounded_static_graph_reachable_instruction_count":len(p),
        "bounded_static_graph_branch_syntax_counts":dict(cfg["branch_count"]),
        "bounded_static_graph_unknown_indirect_transfer_count":len(cfg["unknown"]),
        "bounded_static_graph_unknown_indirect_sites":[src(pc) for pc in cfg["unknown"][:MAX_EXIT]],
        "bounded_static_graph_external_exit_count":len(cfg["external"]),
        "bounded_static_graph_external_exit_sites":[{
            "source_site":src(pc),"branch_kind":kind,
            "bounded_external_successor_count":n
        } for pc,kind,n in cfg["external"][:MAX_EXIT]],
        "original_key_native_source_site_reachability":sites,
        "direct_native_inbound_static_predecessor_census":
            nearby_public_branches(read,*lineage.inventory.SOURCE_UNITS["Ball"],
                                   (BASE+0x2CD4,BASE+0x2CF8,
                                    BASE+0x2D00,BASE+0x2F98,
                                    BASE+0x2FB8)),
        "function_window_is_exact_whole_CFG_proven":False,
        "indirect_calls_or_dynamic_branch_paths_exhausted":False,
        "selected_Ball_receiver_or_source_object_verified":False,
        "native_tree_collision_material_code_proven":False,
        "original_guest_impact_frame_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    prior=old.run(archive,capture)
    if not prior["original_seven_pair_sha_and_scene_gates_passed"] or (
            prior["original_verified_capture_number"]!=capture):
        raise ValueError("Prior original native SHA gates not met")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for index,size in enumerate(seven.SIZE,1):
            f=seven.src._file(roots[capture],f"{capture}.{index}.raw",size)
            h=stack.enter_context(f.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(h.fileno(),0,access=mmap.ACCESS_READ)))
        def read(pc):
            if pc%4 or pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Out of original source MEM1 native code")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        out=inspect(read)
    seven._check_archive(archive)
    return {**out,"original_seven_pair_sha_and_scene_gates_passed":True,
            "original_verified_capture_number":capture}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",required=True,type=Path)
    parser.add_argument("--capture",type=int,choices=range(1,8),default=7)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(run(args.archive,args.capture),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,IndexError,
            OverflowError,TypeError,AttributeError,struct.error):
        print(json.dumps({
            "kind":"P0_ORIGINAL_BALL_CACHE_ENTRY_BRANCH_REACHABILITY_V1",
            "status":"ABSTAIN_NATIVE_SHA_SOURCE_OR_CFG",
            "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
