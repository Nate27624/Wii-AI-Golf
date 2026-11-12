#!/usr/bin/env python3
"""Strict original P0 Ball/KCol prism-halfword producer and resource-owner trace.

Read-only RSPE01 Rev1 seven-pair original archive/scene/SHA/94x84 tree-loop.
Reuses all exact Ball/KCol source gates from the prior two audits.
Proves *syntactic* return-buffer dataflow from KCL 16-byte prism +0x0E
into Ball's direct query output and follows wrapper/resource candidates.
Does not assert class 13 is present in the known terrain KCL, a tree hit,
or a ball velocity vector.

--detail emits only bounded source-relative native PPC to operator terminal;
never write original game data, private coordinates, assets, or code to Git.
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
import p0_ball_kcol_result_provenance_private as previous
import p0_tree_hitbox_source_callgraph_private as units
import p0_tree_hitbox_five_calls_private as decoder

MEM1=0x80000000

# owner, source offset, D-form opcode, destination/source register,
# base register, signed displacement. These are semantic expectations;
# no source executable byte sequences are stored in this repository.
EXPECTED_DFORM=(
    ("GolfKCol",0x0118,40,0,3,14),     # lhz r0,14(r3), prism+0x0E
    ("GolfKCol",0x011C,44,0,28,0),     # sth r0,0(r28), query out-class
    ("GolfKCol",0x22EC,40,3,27,14),   # narrowphase primitive classification
    ("GolfKCol",0x22F4,44,3,1,8),     # saved to narrowphase stack
    ("GolfKCol",0x2684,40,0,1,8),     # reload narrowphase saved class
    ("GolfKCol",0x2688,44,0,22,0),    # export to r22's output pointer
    ("Ball",0x14C4,14,7,1,8),        # r7 = &stack+8 in main query
    ("Ball",0x14F0,40,0,1,8),        # read exact returned stack+8
    ("Ball",0x3568,48,5,30,172),    # copy from object+AC
    ("Ball",0x356C,48,4,30,176),
    ("Ball",0x3570,48,3,30,180),
    ("Ball",0x358C,52,5,29,172),    # copy to other object+AC
    ("Ball",0x3590,52,4,29,176),
    ("Ball",0x3594,52,3,29,180),
)

# Target source context not covered by previous 592-word output.
WINDOWS=(
    ("ball_query_resource_owner","Ball",0x0920,0x0B60),
    ("kcol_wrapper_to_narrowphase","GolfKCol",0x1A90,0x1B20),
    ("kcol_secondary_result_callback","GolfKCol",0x1C24,0x1D10),
    ("ball_state_copy_function_context","Ball",0x34B0,0x34FC),
    ("ball_state_copy_tail","Ball",0x35C8,0x3640),
    ("kcol_narrowphase_output_forwarding","GolfKCol",0x2630,0x26B8),
)
MAX_NATIVE_WORDS=360
assert sum((end-start)//4 for _,_,start,end in WINDOWS)<=MAX_NATIVE_WORDS


def validate_dform(read,unit,off,opcode,rt,ra,disp):
    lo,hi=units.UNITS[unit]
    pc=lo+off
    if off%4 or not lo<=pc<hi:
        raise ValueError("Source word offset outside public code unit")
    op=read(pc)
    got=(op>>26,(op>>21)&31,(op>>16)&31,
         (op&0xFFFF)-0x10000 if op&0x8000 else op&0xFFFF)
    if got!=(opcode,rt,ra,disp):
        raise ValueError("Original KCL prism producer/receiver source changed")


def inspect(read,detail=False):
    prior=previous.inspect(read,detail=False)
    if not prior["earlier_exact_material_and_call_gates_passed"]:
        raise ValueError("Earlier native source provenance not passed")
    for fields in EXPECTED_DFORM:
        validate_dform(read,*fields)

    # Preserve direct-call identity rather than assuming source-unit names.
    blo=units.UNITS["Ball"][0]
    klo=units.UNITS["GolfKCol"][0]
    target=units.direct_b(blo+0x14D0,read(blo+0x14D0))
    if target!=(klo,True):
        raise ValueError("Main Ball KCol query does not call verified entry")

    rows=[]
    total=0
    for label,owner,start,end in WINDOWS:
        lo,hi=units.UNITS[owner]
        if start<0 or start%4 or end%4 or end<=start or lo+end>hi:
            raise ValueError("Native code window exceeds original source unit")
        count=(end-start)//4
        total+=count
        if total>MAX_NATIVE_WORDS:
            raise ValueError("Too many native source words")
        counter=Counter()
        code=[]
        for off in range(start,end,4):
            pc=lo+off
            word=read(pc)
            op=word>>26
            if op==16:counter["conditional_branches"]+=1
            elif op==18:counter["direct_branches"]+=1
            elif op in (40,42):counter["halfword_loads"]+=1
            elif op==44:counter["halfword_stores"]+=1
            elif op in (48,49):counter["float_loads"]+=1
            elif op in (52,53):counter["float_stores"]+=1
            if detail:
                code.append(f"{owner}+0x{off:04X}  {word:08X}  "
                            f"{decoder.ppc(pc,word)}")
        row={
            "region":label,"source_unit":owner,
            "relative_span":f"+0x{start:04X}..+0x{end-4:04X}",
            "instruction_count":count,
            "syntactic_counts":dict(sorted(counter.items())),
        }
        if detail:row["native_code_local_only"]=code
        rows.append(row)
    return {
        "kind":"P0_ORIGINAL_KCL_PRISM_TYPE_PRODUCER_AND_BALL_COPY",
        "status":"PRISM_HALFWORD_TO_QUERY_OUTPUT_VERIFIED",
        "original_source_gates_passed":True,
        "main_query_classification_from_prism_offset_0x0E":True,
        "narrowphase_classification_from_prism_offset_0x0E":True,
        "ball_0xAC_B0_B4_structural_state_copy_verified":True,
        "ball_0B60_wrapped_query_resource_owner_proven":False,
        "classification_13_tree_semantics_proven":False,
        "ball_velocity_semantics_proven":False,
        "native_tree_hitbox_proven":False,
        "training_approved":False,
        "native_source_words":total,"windows":rows,
    }


def run(archive:Path,capture:int,detail:bool):
    if capture not in range(1,8):
        raise ValueError("Only original seven capture phases supported")
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
        ptr=rd.u32(field+0x20)
        if count!=94 or seven.roster._bank(ptr,count*84)!="MEM2":
            raise ValueError("Original FieldManager 94x84 tree array changed")
        def read(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Native read outside original MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not units.tree_loop_source_gated(read):
            raise ValueError("Original source tree array PPC fingerprint changed")
        report=inspect(read,detail)
    seven._check_archive(archive)
    return {
        "capture":capture,"source_trees":94,
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
            print(json.dumps(
                {k:v for k,v in report.items() if k!="windows"},
                sort_keys=True,separators=(",",":")))
            for item in report["windows"]:
                print(f"===== {item['region']} {item['relative_span']} =====")
                print("\n".join(item["native_code_local_only"]))
            print("===== END PRISM PRODUCER AND RESOURCE OWNER WINDOWS =====")
        else:
            print(json.dumps(report,sort_keys=True,separators=(",",":"),
                             allow_nan=False))
        return 0
    except (ValueError,OSError,IndexError,TypeError,OverflowError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_KCL_PRISM_TYPE_PROVENANCE","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
