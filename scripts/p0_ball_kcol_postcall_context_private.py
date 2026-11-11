#!/usr/bin/env python3
"""Original Wii Golf Ball -> GolfKCol return-value and state-write source triage.

Read-only ORIGINAL RSPE01 Rev1 7-pair SHA / scene / 94x84 FieldManager tree
source loop. Enumerate exactly five original native Ball->GolfKCol BL sites
and seven inverse calls; dump narrowly bounded Ball caller before+after
and the true GolfKCol target code to the OPERATOR's terminal only.

The relative source owner is a compilation unit, NOT proof of a contact
solver. Neither GPR/FPR post-call access nor code proximity alone proves
that the return is a collision result or that a store writes ball velocity.
No RAM pointers, XYZ, triangle vertices, captured game code or physics
labels are exported or committed. All outputs have training_approved=false.
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
import p0_tree_hitbox_source_callgraph_private as units
import p0_ball_kcol_twelve_calls_private as original
import p0_tree_hitbox_five_calls_private as decoder

MEM1=0x80000000
BEFORE=15
AFTER=36
TARGET=34
MAX_CALLS=5
# These original source-relative BL addresses/targets were already observed
# on the operator's SHA-qualified phase7 output, not inferred from counts.
EXPECTED_CALLS={
    0x05C0:0x0000,
    0x0AFC:0x1BB8,
    0x0B60:0x1AC4,
    0x14D0:0x0000,
    0x27B0:0x0000,
}
BASIC_OPS={32:"lwz",33:"lwzu",34:"lbz",36:"stw",37:"stwu",38:"stb",
           40:"lhz",42:"lha",44:"sth",48:"lfs",49:"lfsu",
           50:"lfd",52:"stfs",53:"stfsu",54:"stfd"}


def source_ref(addr):
    return decoder.source_label(addr)


def bounded_rows(read,owner,start,end,detail):
    lo,hi=units.UNITS[owner]
    if start<lo or end>hi or end<=start or any(x%4 for x in (start,end)):
        raise ValueError("Native source instruction span outside public unit")
    lines=[]
    summaries=[]
    for pc in range(start,end,4):
        op=read(pc)
        if detail:
            lines.append(
                f"{owner}+0x{pc-lo:04X}  {op:08X}  {decoder.ppc(pc,op)}")
        if op>>26 in BASIC_OPS:
            ra=(op>>16)&31
            word_disp=op&0xFFFF
            if word_disp&0x8000:
                word_disp-=0x10000
            summaries.append({
                "site":f"+0x{pc-lo:04X}",
                "opcode":BASIC_OPS[op>>26],
                "base_register":f"r{ra}",
                "displacement_bytes":word_disp,
            })
    return lines,summaries


def status_candidates(read,pc,limit=16):
    """Only local *syntax*, never assign result ownership or value.

    Return register r3 may be a callee return or a persistent object pointer;
    FPR f1 can also be a value unrelated to the BL. Abort local scan on an
    unconditional control flow transfer to avoid suggesting false straight
    line def-use through branch boundaries.
    """
    lo,hi=units.UNITS["Ball"]
    end=min(hi,pc+4*(limit+1))
    comparisons=[]
    branches=[]
    stores=[]
    for cur in range(pc+4,end,4):
        op=read(cur)
        opc=op>>26
        if opc in (10,11):
            comparisons.append({
                "site":f"+0x{cur-lo:04X}",
                "kind":"integer_immediate_comparison",
                "register":f"r{(op>>16)&31}",
            })
        if opc==31 and ((op>>1)&1023) in (0,32):
            comparisons.append({
                "site":f"+0x{cur-lo:04X}",
                "kind":"integer_register_comparison",
                "register":"untracked_operands",
            })
        if opc==63 and ((op>>1)&1023) in (0,32):
            comparisons.append({
                "site":f"+0x{cur-lo:04X}",
                "kind":"floating_comparison",
                "register":"untracked_operands",
            })
        if opc in (36,38,44,52,53,54):
            disp=op&0xFFFF
            if disp&0x8000:
                disp-=0x10000
            stores.append({
                "site":f"+0x{cur-lo:04X}",
                "op":BASIC_OPS.get(opc,"unknown"),
                "base_register":f"r{(op>>16)&31}",
                "displacement_bytes":disp,
                "object_owner_verified":False,
            })
        if opc in (16,18,19):
            dest=units.direct_b(cur,op) if opc==18 else None
            branches.append({
                "site":f"+0x{cur-lo:04X}",
                "class":"direct" if opc==18 else
                        "conditional" if opc==16 else "indirect",
                "source_target":source_ref(dest[0]) if dest else None,
                "is_linked_call":dest[1] if dest else None,
            })
            if opc==18 and not (op&1):
                break
            if opc==19 and ((op>>1)&1023) in (16,528) and not (op&1):
                break
    return {
        "post_call_syntactic_compares":comparisons[:12],
        "post_call_syntactic_stores":stores[:16],
        "post_call_branches":branches[:12],
        "return_value_dataflow_verified":False,
        "ball_velocity_store_verified":False,
        "tree_or_obstacle_collision_verified":False,
    }


def inspect(read,detail=False):
    # Full original call graph is a prerequisite: five direct Ball->GolfKCol
    # plus seven reverse. Decoys, unexpected calls or altered native binary
    # fail closed. The paired function must still live in correct source unit.
    gate=original.inspect(read,detail=False,strict=True)
    records=[entry for entry in gate["calls"]
             if entry["caller"]=="Ball" and entry["callee"]=="GolfKCol"]
    if len(records)!=MAX_CALLS:
        raise ValueError("Original Ball-to-KCol source call cardinality changed")
    actual={int(x["caller_site"],16):int(x["callee_site"],16)
            for x in records}
    if actual!=EXPECTED_CALLS:
        raise ValueError("Original five native BL site/target offsets changed")
    lo,hi=units.UNITS["Ball"]
    klo,khi=units.UNITS["GolfKCol"]
    output=[]
    for entry in records:
        pc=lo+int(entry["caller_site"],16)
        target=units.direct_b(pc,read(pc))
        if not target or not target[1] or not klo<=target[0]<khi:
            raise ValueError("Original native BL target no longer in GolfKCol")
        if pc-BEFORE*4<lo or pc+(AFTER+1)*4>hi or target[0]+TARGET*4>khi:
            raise ValueError("Source call or target outside bounded code context")
        before_lines,prior=bounded_rows(
            read,"Ball",pc-BEFORE*4,pc,detail)
        call_lines,after=bounded_rows(
            read,"Ball",pc,pc+(AFTER+1)*4,detail)
        target_lines,callee_member=bounded_rows(
            read,"GolfKCol",target[0],target[0]+TARGET*4,detail)
        out={
            "caller_site":entry["caller_site"],
            "callee_site":f"+0x{target[0]-klo:04X}",
            "source_code_context_before_words":BEFORE,
            "source_code_context_after_words":AFTER,
            "target_entry_words":TARGET,
            "caller_prior_accesses":prior[:15],
            "caller_after_accesses":after[:24],
            "callee_entry_accesses":callee_member[:24],
            "post_call_status_syntax":status_candidates(read,pc),
            "callee_source_owner_is_collision_proof":False,
            "return_type_proven":False,
            "ball_velocity_mutation_proven":False,
            "tree_collision_geometry_verified":False,
        }
        if detail:
            out["local_caller_code_lines"]=[*before_lines,*call_lines]
            out["local_callee_code_lines"]=target_lines
        output.append(out)
    return {
        "kind":"P0_OGWS_BALL_GOLFKCOL_FIVE_SOURCE_CALL_RETURNS",
        "status":"ORIGINAL_BALL_KCOL_POSTCALL_CONTEXT",
        "native_direct_call_gate":gate["pair_counts"],
        "source_ball_to_kcol_call_count":len(output),
        "distinct_kcol_target_function_entry_offsets":
            sorted({x["callee_site"] for x in output}),
        "call_contexts":output,
        "native_kcl_resource_used_by_ball_verified":False,
        "tree_hitbox_or_collision_shape_verified":False,
        "ball_contact_response_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int,detail:bool):
    if capture not in range(1,8):
        raise ValueError("Unknown capture")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            path=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            handle=stack.enter_context(path.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*banks)
        field=seven._get(reader)["field"]
        count=reader.u32(field+0x1C)
        base=reader.u32(field+0x20)
        if count!=94 or seven.roster._bank(base,count*84)!="MEM2":
            raise ValueError("Original field tree source count/stride mismatch")
        def read(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Native source code outside MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not units.tree_loop_source_gated(read):
            raise ValueError("Original source 94-tree loop PPC mismatch")
        report=inspect(read,detail)
    seven._check_archive(archive)
    return {
        "capture":capture,
        "source_trees":94,
        "original_sha_scene_and_source_tree_loop_gated":True,
        **report,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    p.add_argument("--detail",action="store_true",
                   help="Print bounded original code ONLY to operator local console")
    args=p.parse_args(argv)
    try:
        report=run(args.archive,args.capture,args.detail)
        if args.detail:
            print(json.dumps({k:v for k,v in report.items() if k!="call_contexts"},
                             sort_keys=True,separators=(",",":")))
            for item in report["call_contexts"]:
                print(f"===== Ball{item['caller_site']} -> GolfKCol{item['callee_site']} =====")
                print("-- BALL SOURCE BEFORE + POSTCALL --")
                print("\n".join(item["local_caller_code_lines"]))
                print("-- KCOL TARGET ENTRY --")
                print("\n".join(item["local_callee_code_lines"]))
            print("===== END FIVE ORIGINAL BALL/KCOL RETURN CONTEXTS =====")
        else:
            print(json.dumps(report,sort_keys=True,separators=(",",":"),
                             allow_nan=False))
        return 0
    except (OSError,ValueError,IndexError,TypeError,OverflowError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_BALL_KCOL_POSTCALL_SOURCE","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
