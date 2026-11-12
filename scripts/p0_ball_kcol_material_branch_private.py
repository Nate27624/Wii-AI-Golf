#!/usr/bin/env python3
"""Original Wii Sports Golf Ball/KCol material dispatch and stored vector audit.

Read-only 7-pair SHA / selected scene / verified original 94x84 tree-array
PPC fingerprint; verifies all 5 original Ball->GolfKCol source callsites
and 7 reverse edges before any native source window is inspected.

Operator's original output established a loop at Ball+0x0B60 using a
16-bit hit classification; Ball+0x14D0 copies three query-output
float values to a Ball-object field conditional on another classification.
We trace those contexts, the post-branch handlers and matching member
field accesses. DO NOT infer a collider radius, tree hit, or velocity
semantics from a source-unit name or storage offset.

--detail prints bounded original PPC instructions locally only. All output
is source-unit relative, no private heap or per-tree coordinates, never
exports ROM/game code to Git. No training approval.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from collections import Counter
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_ball_kcol_postcall_context_private as previous
import p0_tree_hitbox_source_callgraph_private as units
import p0_tree_hitbox_five_calls_private as decode

MEM1=0x80000000
# Windows are fixed to observed original source-relative branches, including
# the paths beyond the earlier 36-word postcall excerpt.
WINDOWS=(
    ("ball_hit_mask_and_special_codes","Ball",0x0B4C,0x0BC0),
    ("ball_hit_accepted_branch","Ball",0x0BF4,0x0C98),
    ("ball_hit_dispatch_later","Ball",0x0D60,0x0E78),
    ("ball_surface_vector_copy","Ball",0x14B8,0x1530),
    ("ball_event_helper_entry","Ball",0x01B8,0x0248),
    ("kcol_query_hit_material_output","GolfKCol",0x0120,0x0250),
    ("kcol_narrowphase_classification","GolfKCol",0x2090,0x2240),
)
MAX_WORDS=420
assert sum((end-start)//4 for _,__,start,end in WINDOWS)<=MAX_WORDS

# Every word below was printed by the operator's original phase7 private
# SHA-qualified source trace. These anchors distinguish a return/status
# test from a generic memory reference or an unrelated source version.
ORIGINAL_ANCHORS={
    ("Ball",0x0B60):0x4800DD71,  # BL GolfKCol+0x1AC4
    ("Ball",0x0B64):0x2C030000,  # cmpwi r3,0 (result present)
    ("Ball",0x0B6C):0xA061000A,  # lhz r3,+0x0A(sp)
    ("Ball",0x0B78):0x7FC01830,  # slw r0,r30,r3
    ("Ball",0x0B7C):0x7C00E039,  # and. r0,r0,r28
    ("Ball",0x0B84):0x2C03000D,  # compare returned halfword to 13
    ("Ball",0x0B90):0x2C030007,  # compare returned halfword to 7
    ("Ball",0x0BA8):0x88170050,  # reads receiver byte
    ("Ball",0x14D0):0x4800B93D,  # BL GolfKCol+0x0000
    ("Ball",0x14D4):0x2C030000,  # result check
    ("Ball",0x14F0):0xA0010008,  # lhz r0,+0x08(sp)
    ("Ball",0x14F4):0x28000007,  # compare material to 7
    ("Ball",0x14FC):0x2800000C,  # compare material to 12
    ("Ball",0x1508):0xD01700AC,  # stfs f0,+0xAC(r23)
    ("Ball",0x1510):0xD01700B0,  # stfs f0,+0xB0(r23)
    ("Ball",0x1518):0xD01700B4,  # stfs f0,+0xB4(r23)
    ("GolfKCol",0x1AC4):0xC0230054, # wrapper +0x54
    ("GolfKCol",0x1AE4):0x480005AC, # b GolfKCol+0x2090
}
VECTOR_FIELDS=(0x00AC,0x00B0,0x00B4)
MATERIAL_CODES=(7,12,13)


def member_accesses(read,source_name="Ball",fields=VECTOR_FIELDS):
    """Syntactic field offsets only; no reaching-definition provenance."""
    lo,hi=units.UNITS[source_name]
    result=[]
    for pc in range(lo,hi,4):
        op=read(pc)
        if op>>26 not in (32,34,36,38,40,42,44,48,49,50,52,53,54):
            continue
        off=op&0xFFFF
        if off&0x8000:
            off-=0x10000
        if off not in fields:
            continue
        opname={32:"lwz",34:"lbz",36:"stw",38:"stb",40:"lhz",
                42:"lha",44:"sth",48:"lfs",49:"lfsu",50:"lfd",
                52:"stfs",53:"stfsu",54:"stfd"}[op>>26]
        result.append({
            "site":f"+0x{pc-lo:04X}",
            "op":opname,
            "base":f"r{(op>>16)&31}",
            "displacement_bytes":off,
            "is_ball_velocity_proven":False,
        })
    return result


def inspect(read,detail=False):
    # First verify exact 5+7 crosscalls and all five real BL offsets, not
    # only generic compiler source unit boundaries.
    upstream=previous.inspect(read,detail=False)
    if upstream["source_ball_to_kcol_call_count"]!=5:
        raise ValueError("Original Ball query count changed")
    for (owner,off),word in ORIGINAL_ANCHORS.items():
        if read(units.UNITS[owner][0]+off)!=word:
            raise ValueError("Original ball material/source word anchor mismatch")
    row=[]
    for name,owner,start,end in WINDOWS:
        lo,hi=units.UNITS[owner]
        if (start<0 or start%4 or end%4 or end<=start or lo+end>hi):
            raise ValueError("Native disassembly exceeds public source unit")
        summary=Counter()
        lines=[]
        for off in range(start,end,4):
            pc=lo+off
            word=read(pc)
            opc=word>>26
            if opc in (10,11):
                summary["integer_immediate_compares"]+=1
            if opc==16:
                summary["conditional_branches"]+=1
            if opc==18:
                summary["direct_branches_and_calls"]+=1
            if opc in (36,38,44,52,53):
                summary["stores"]+=1
            if opc in (40,42):
                summary["halfword_loads"]+=1
            if detail:
                lines.append(
                    f"{owner}+0x{off:04X}  {word:08X}  {decode.ppc(pc,word)}")
        item={
            "region":name,
            "source_unit":owner,
            "source_relative_span":f"+0x{start:04X}..+0x{end-4:04X}",
            "instruction_count":(end-start)//4,
            "syntax_counts":dict(sorted(summary.items())),
            "ball_object_or_tree_receiver_dataflow_proven":False,
        }
        if detail:
            item["original_source_words_local_only"]=lines
        row.append(item)
    accesses=member_accesses(read)
    return {
        "kind":"P0_NATIVE_BALL_KCOL_MATERIAL_DISPATCH_SOURCE",
        "status":"SOURCE_MATERIAL_BRANCH_AND_BALL_VECTOR_FIELDS",
        "original_five_ball_queries_exactly_qualified":True,
        "original_seven_kcol_inverse_calls_qualified":True,
        "native_ball_classification_halfwords_read_at_stack_offsets":
            ["+0x0008","+0x000A"],
        "candidate_hit_classifications_checked":[7,12,13],
        "observed_success_path_ball_member_float_stores":
            ["+0x00AC","+0x00B0","+0x00B4"],
        "all_ball_source_candidate_member_field_accesses":accesses[:180],
        "ball_member_field_access_count":len(accesses),
        "native_windows":row,
        "collision_status_or_material_semantic_proven":False,
        "ball_velocity_field_semantics_proven":False,
        "native_tree_contact_dispatch_proven":False,
        "tree_hitbox_geometry_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int,detail:bool):
    if capture not in range(1,8):
        raise ValueError("Original capture 1..7 only")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            file=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            handle=stack.enter_context(file.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        field=seven._get(rd)["field"]
        count=rd.u32(field+0x1C)
        ptr=rd.u32(field+0x20)
        if count!=94 or seven.roster._bank(ptr,count*84)!="MEM2":
            raise ValueError("Original source-owned tree array changed")
        def word(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Source code outside MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not units.tree_loop_source_gated(word):
            raise ValueError("Original FieldManager 94x84 PPC loop mismatch")
        report=inspect(word,detail)
    seven._check_archive(archive)
    return {
        "capture":capture,
        "source_trees":94,
        "original_archive_sha_scene_and_84_stride_verified":True,
        **report,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    p.add_argument("--detail",action="store_true")
    a=p.parse_args(argv)
    try:
        report=run(a.archive,a.capture,a.detail)
        if a.detail:
            print(json.dumps({k:v for k,v in report.items() if k!="native_windows"},
                             sort_keys=True,separators=(",",":")))
            for item in report["native_windows"]:
                print(f"===== {item['region']} {item['source_relative_span']} =====")
                print("\n".join(item["original_source_words_local_only"]))
            print("===== END MATERIAL DISPATCH SOURCE WINDOWS =====")
        else:
            print(json.dumps(report,sort_keys=True,separators=(",",":"),
                             allow_nan=False))
        return 0
    except (ValueError,OSError,IndexError,TypeError,OverflowError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_BALL_KCOL_MATERIAL_BRANCH","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
