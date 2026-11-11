#!/usr/bin/env python3
"""Original Wii Sports Golf tree firstword dispatch and Ball indirect calls.

READ ONLY original Rev1 seven-pair SHA/scene/source-gated capture. This
audits (a) all 94 source-owned 84-byte tree objects' common firstword as
a *potential* method-table address and (b) PPC branch-to-CTR callsite
source contexts in Ball, FieldManager, Simulation, Tree and collision
utility units. A same-address firstword and code-pointer-like table entries
are NOT proof of a vtable or of a ball-to-tree call; bctrl cannot be
resolved without proving the reaching definition of CTR and receiver.

All original RAM pointers and native code bytes remain operator-local.
Without --detail prints source-relative function-offset metadata only;
--detail prints at most 30 bounded local instruction windows. No new
captures, Dolphin, game writes, tree dimensions or training labels.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_ball_kcol_active_resource_private as active
import p0_tree_hitbox_source_callgraph_private as native
import p0_tree_hitbox_five_calls_private as decoder

MEM1=seven.roster.MEM1_BASE
SOURCE_UNITS=("Ball","FieldManager","Simulation","Tree",
              "CollisionChecker","CollisionModel")
METHOD_SLOTS=64
MAX_DETAIL_WINDOWS=30
MAX_DETAIL_PER_OWNER=8
PREVIOUS_WORDS=9
FOLLOWING_WORDS=2
MAX_SITE_SUMMARY_PER_UNIT=64


def inspect_tree_firstword(u32,tree_base,count,bank):
    if count!=94 or bank(tree_base,count*84)!="MEM2":
        raise ValueError("Original source-owned 94x84 objects absent")
    first={u32(tree_base+i*84) for i in range(count)}
    if len(first)!=1:
        raise ValueError("Original 94 tree firstwords no longer share identity")
    pointer=first.pop()
    if pointer%4 or bank(pointer,METHOD_SLOTS*4)!="MEM1":
        raise ValueError("Shared tree firstword is not a bounded MEM1 table")
    entries=[]
    buckets=Counter()
    for slot in range(METHOD_SLOTS):
        target=u32(pointer+slot*4)
        owner=native.source_unit(target)
        if owner:
            value=f"{owner}+0x{target-native.UNITS[owner][0]:04X}"
            entries.append({"slot":slot,"candidate_target":value,
                            "is_tree_method_proven":False})
            buckets[owner]+=1
        else:
            buckets["outside_selected_public_source_units"]+=1
    return {
        "source_tree_count":count,
        "source_tree_stride":84,
        "all_94_tree_firstwords_identical":True,
        "shared_firstword_bounded_MEM1":True,
        "table_slots_inspected":METHOD_SLOTS,
        "public_unit_target_counts":dict(sorted(buckets.items())),
        "source_relative_candidate_entries":entries,
        "firstword_is_vtable_proven":False,
        "candidate_target_is_tree_collision_handler_proven":False,
    }


def nearby_mtctr(read,pc,unit_lo):
    """Only identify syntax of an mtspr CTR instruction; no reaching definitions."""
    for lookback in range(1,PREVIOUS_WORDS+1):
        addr=pc-4*lookback
        if addr<unit_lo:
            break
        word=read(addr)
        if word>>26 != 31 or (word>>1)&1023 !=467:
            continue
        spr=((word>>16)&31)|(((word>>11)&31)<<5)
        if spr==9:  # CTR on PPC
            return f"-0x{lookback*4:02X}"
    return None


def inspect_indirect_calls(read,detail=False):
    result=[]
    used=0
    for owner in SOURCE_UNITS:
        lo,hi=native.UNITS[owner]
        sites=[]
        kinds=Counter()
        owner_detail=0
        for pc in range(lo,hi,4):
            kind=native.indirect_call(read(pc))
            if kind is None:
                continue
            kinds[kind]+=1
            if len(sites)>=MAX_SITE_SUMMARY_PER_UNIT:
                continue
            site={
                "source_relative_site":f"+0x{pc-lo:04X}",
                "dispatch_kind":kind,
                "nearby_mtctr_syntax_at_relative_site":nearby_mtctr(read,pc,lo),
                "CTR_reaching_target_or_tree_receiver_proven":False,
            }
            if (detail and used<MAX_DETAIL_WINDOWS
                    and owner_detail<MAX_DETAIL_PER_OWNER
                    and pc-PREVIOUS_WORDS*4>=lo
                    and pc+FOLLOWING_WORDS*4<hi):
                site["operator_local_original_code_context"]=[
                    f"{owner}+0x{p-lo:04X}  {read(p):08X}  {decoder.ppc(p,read(p))}"
                    for p in range(pc-PREVIOUS_WORDS*4,
                                   pc+(FOLLOWING_WORDS+1)*4,4)
                ]
                used+=1
                owner_detail+=1
            sites.append(site)
        result.append({
            "source_unit":owner,
            "indirect_call_total":sum(kinds.values()),
            "dispatch_kind_counts":dict(sorted(kinds.items())),
            "sites":sites,
            "site_list_truncated":len(sites)<sum(kinds.values()),
        })
    return {
        "source_units":list(SOURCE_UNITS),
        "per_unit":result,
        "operator_local_detail_windows":used,
        "known_tree_method_invoked_from_ball_proven":False,
        "indirect_tree_contact_handler_proven":False,
    }


def inspect(read,u32,tree_base,count,bank,detail=False):
    active.inspect_source(read)  # Exact 5+7 Ball-KCol/primitive producer gates.
    if not native.tree_loop_source_gated(read):
        raise ValueError("Original FieldManager tree loop PPC mismatch")
    first=inspect_tree_firstword(u32,tree_base,count,bank)
    indirect=inspect_indirect_calls(read,detail)
    return {
        "kind":"P0_TREE_FIRSTWORD_AND_BALL_INDIRECT_DISPATCH_SOURCE",
        "status":"SOURCE_BOUNDED_INDIRECT_DISPATCH_CENSUS",
        "original_native_ball_kcol_source_gates":True,
        "tree_firstword":first,
        "indirect":indirect,
        "tree_collision_receiver_proven":False,
        "tree_hitbox_geometry_proven":False,
        "ball_velocity_impulse_proven":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int,detail:bool=False):
    if capture not in range(1,8):
        raise ValueError("Only original source-qualified captures supported")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            handle=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        field=seven._get(rd)["field"]
        count=rd.u32(field+0x1C)
        tree_base=rd.u32(field+0x20)
        if count!=94 or seven.roster._bank(tree_base,count*84)!="MEM2":
            raise ValueError("Source 94x84 tree array changed")
        def read(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Source code read outside MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        def bank(address,size):
            return seven.roster._bank(address,size)
        report=inspect(read,rd.u32,tree_base,count,bank,detail)
    seven._check_archive(archive)
    return {
        "capture":capture,
        "original_archive_sha_scene_and_94_tree_stride_verified":True,
        **report,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    p.add_argument("--detail",action="store_true")
    a=p.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture,a.detail),
                         sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,IndexError,OverflowError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_TREE_INDIRECT_DISPATCH_SOURCE",'
              '"training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
