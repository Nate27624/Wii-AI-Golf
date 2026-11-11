#!/usr/bin/env python3
"""Compact source-gated Rev1 PPC receiver provenance at two tree-field-like loads.

Read only original seven-pair SHA archive and source-qualified scene.
Emit a handful of public CODE-relative site labels, never RAM addresses,
instruction words, per-tree XYZ, meshes, or runtime gameplay claims.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_tree_ppc_indexing_private as earlier

MEM1=0x80000000
BASE,END=earlier.WINDOWS["field_load_hole_resources"]
FIELD_LO,FIELD_HI=earlier.UNITS["FieldManager"]
READ_SITES=((0x06E8,0x20),(0x06FC,0x1C))
MAX_CANDIDATES=3


def dform(word):
    op=word>>26
    if op not in (32,33,36,37):  # bounded lwz/lwzu/stw/stwu only
        return None
    return ("load" if op in (32,33) else "store",
            (word>>21)&31,(word>>16)&31,
            earlier.signed16(word&0xFFFF))


def r28_set(word):
    """Only syntactically recognizable integer register r28 assignments."""
    op=word>>26
    rt=(word>>21)&31
    ra=(word>>16)&31
    if op in (14,15,7) and rt==28:
        return {14:"addi",15:"addis",7:"mulli"}[op], ("r"+str(ra) if op!=15 else "immediate")
    if op in (32,33,34,35,40,42) and rt==28:
        return {32:"lwz",33:"lwzu",34:"lbz",35:"lbzu",
                40:"lhz",42:"lha"}[op], "r"+str(ra)
    if op==31:
        xo=(word>>1)&1023
        if xo==444 and ra==28 and rt==((word>>11)&31):
            return "mr", "r"+str(rt)
        if xo in (266,40,235) and rt==28:
            return {266:"add",40:"subf",235:"mullw"}[xo], "registers_unresolved"
    if op==21 and ra==28:
        return "rlwinm", "r"+str(rt)
    return None


def control(word):
    op=word>>26
    return op in (16,17,18) or (
        op==19 and ((word>>1)&1023) in (16,50,528))


def inspect(read):
    output=[]
    for site,member in READ_SITES:
        pc=BASE+site
        original=dform(read(pc))
        if original is None or original[0]!="load" or original[3]!=member:
            raise ValueError("Source opcode at anchor changed")
        reg=original[2]
        # No 'FieldManager' receiver claim: r28 may point to any structure.
        lookback=max(BASE,pc-0x600)
        writes=[]
        for addr in range(lookback,pc,4):
            decoded=r28_set(read(addr)) if reg==28 else None
            if decoded:
                hazard=sum(control(read(a)) for a in range(addr+4,pc,4))
                writes.append({
                    "source_relative_site":f"+0x{addr-BASE:04X}",
                    "assignment":decoded[0],
                    "from":decoded[1],
                    "distance_bytes":pc-addr,
                    "control_transfers_between":hazard,
                })
        output.append({
            "source_relative_load":f"+0x{site:04X}",
            "member_offset":f"+0x{member:02X}",
            "receiver_register":f"r{reg}",
            "candidate_receiver_assignments":writes[-MAX_CANDIDATES:],
            "receiver_identity_proven":False,
        })
    # Correlate source-only +1c and +20 words, ignoring stack-frame accesses.
    pairs=[]
    prior={}
    for pc in range(FIELD_LO,FIELD_HI,4):
        op=dform(read(pc))
        if op is None or op[3] not in (0x1C,0x20) or op[2]==1:
            continue
        kind,val,reg,displacement=op
        for other in prior.get((reg,0x3C-displacement),[]):
            if abs(pc-other[0])<=0x90 and pc != other[0]:
                if pc<FIELD_LO or other[0]<FIELD_LO:
                    continue
                pairs.append({
                    "source_unit_relative_sites":[
                        f"+0x{min(pc,other[0])-FIELD_LO:04X}",
                        f"+0x{max(pc,other[0])-FIELD_LO:04X}"],
                    "shared_base_register":f"r{reg}",
                    "site_kinds":sorted([kind,other[1]]),
                    "source_owner_verified":False,
                })
        prior.setdefault((reg,displacement),[]).append((pc,kind))
    pairs=pairs[:6]
    return {
        "status":"TREE_FIELD_RECEIVER_STATIC_CONTEXT",
        "field_window_loads":output,
        "nearest_nonstack_field_offset_pairs":pairs,
        "stack_r1_writes_excluded":True,
        "receiver_dataflow_proven":False,
        "tree_layout_verified":False,
        "training_approved":False,
    }


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Invalid capture")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            f=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            handle=stack.enter_context(f.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*banks)
        src=seven._get(reader)
        field=src["field"]
        count=reader.u32(field+0x1C)
        arr=reader.u32(field+0x20)
        if not 3<=count<=4096 or seven.roster._bank(arr,4)!="MEM2":
            raise ValueError("tree source unqualified")
        def word(pc):
            if not MEM1<=pc<=MEM1+len(banks[0])-4:
                raise ValueError("not source MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        result=inspect(word)
    seven._check_archive(archive)
    return {"capture":capture,"source_tree_count":count,**result}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive",type=Path,required=True)
    ap.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=ap.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),sort_keys=True,separators=(",",":")))
        return 0
    except (ValueError,OSError,TypeError,KeyError,OverflowError,
            IndexError,AttributeError,struct.error):
        print('{"status":"ABSTAIN_SOURCE_RECEIVER","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
