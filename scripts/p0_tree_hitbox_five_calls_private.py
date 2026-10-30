#!/usr/bin/env python3
"""Focused static Wii Sports Golf tree collision callsite/target disassembly.

Read-only original RSPE01 Rev1 7-pair SHA/source/scene qualified. It prints
at most 5 precisely selected public code-unit-relative caller windows and
their true target Tree function entry windows. Optional code WORDS printed to
the OPERATOR LOCAL terminal only. No tree/ball RAM data or native executable
committed, and no collision physics claims without receiver/dataflow proof.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_tree_hitbox_source_callgraph_private as links

MEM1=0x80000000
FOCUSED_SITES={
    "Ball":(0x025C,0x02C0,0x231C),
    "GolfKCol":(0x1FC8,0x21D4),
}
CALLER_BEFORE=12
CALLER_AFTER=8
TARGET_WORDS=18
MAX_OUTPUT_LINES=5*(CALLER_BEFORE+1+CALLER_AFTER+TARGET_WORDS+4)


def s16(x):
    x&=0xFFFF
    return x-0x10000 if x&0x8000 else x


def source_label(pc):
    unit=links.source_unit(pc)
    if unit:
        return f"{unit}+0x{pc-links.UNITS[unit][0]:04X}"
    return "outside_public_relevant_units"


def branch16(pc,w):
    raw=w&0xFFFC
    delta=s16(raw)
    target=(raw if w&2 else pc+delta)&0xFFFFFFFF
    return target


def ppc(pc,w):
    """Partial source PPC decoder; undecoded opcodes are never guessed."""
    op=w>>26
    rt=(w>>21)&31
    ra=(w>>16)&31
    rb=(w>>11)&31
    imm=s16(w)
    loads={
        32:"lwz",33:"lwzu",34:"lbz",35:"lbzu",36:"stw",37:"stwu",
        38:"stb",39:"stbu",40:"lhz",42:"lha",44:"sth",
        48:"lfs",49:"lfsu",50:"lfd",52:"stfs",53:"stfsu",54:"stfd"}
    if op in loads:
        suffix="f" if op in (48,49,50,52,53,54) else "r"
        return f"{loads[op]} {suffix}{rt},{imm:+d}(r{ra})"
    if op in (14,15,7):
        return f"{ {14:'addi',15:'addis',7:'mulli'}[op] } r{rt},r{ra},{imm:+d}"
    if op in (24,25):
        return f"{'ori' if op==24 else 'oris'} r{ra},r{rt},0x{w&65535:04X}"
    if op==18:
        direct=links.direct_b(pc,w)
        if direct:
            target,lk=direct
            return f"{'bl' if lk else 'b'} {source_label(target)}"
    if op==16:
        target=branch16(pc,w)
        return f"bc BO={(w>>21)&31},BI={(w>>16)&31} -> {source_label(target)}"
    if op==19:
        xo=(w>>1)&1023
        if xo in (16,528):
            return ("bclr" if xo==16 else "bcctr")+(" LK" if w&1 else "")
    if op in (10,11):
        return f"{'cmplwi' if op==10 else 'cmpwi'} r{ra},{imm:+d}"
    if op==21:
        sh=(w>>11)&31
        mb=(w>>6)&31
        me=(w>>1)&31
        if mb==0 and me==31-sh and 1<=sh<=10:
            return f"slwi r{ra},r{rt},{sh}"
        return f"rlwinm r{ra},r{rt},{sh},{mb},{me}"
    if op==31:
        xo=(w>>1)&1023
        if xo==444:
            return f"mr r{ra},r{rt}" if rt==rb else f"or r{ra},r{rt},r{rb}"
        if xo in (266,40,235,23,151,0,32,339,467):
            return {
                266:f"add r{rt},r{ra},r{rb}",
                40:f"subf r{rt},r{ra},r{rb}",
                235:f"mullw r{rt},r{ra},r{rb}",
                23:f"lwzx r{rt},r{ra},r{rb}",
                151:f"stwx r{rt},r{ra},r{rb}",
                0:f"cmpw r{ra},r{rb}",
                32:f"cmplw r{ra},r{rb}",
                339:f"mfspr r{rt}",
                467:f"mtspr r{rt}",
            }[xo]
    if op in (59,63):
        xo=(w>>1)&1023
        if op==63 and xo in (0,32):
            return ("fcmpu" if xo==0 else "fcmpo")+f" f{ra},f{rb}"
        if op==63 and xo in (18,20,21,22,25,40,72):
            return {18:"fdiv",20:"fsub",21:"fadd",22:"fsqrt",
                    25:"fmul",40:"fneg",72:"fmr"}[xo]+f" f{rt},f{ra},f{rb}"
        # Single-precision arithmetic uses 5-bit opcode extension.
        low=(w>>1)&31
        if op==59 and low in (18,20,21,25,28,29,30,31):
            return {18:"fdivs",20:"fsubs",21:"fadds",25:"fmuls",
                    28:"fmsubs",29:"fmadds",30:"fnmsubs",31:"fnmadds"}[low]+f" f{rt},f{ra},f{rb}"
    return f"op{op}/undecoded"


def inspect(read):
    """Exact five real callsite source offsets; never resolve speculative edges."""
    output=[]
    for caller, offsets in FOCUSED_SITES.items():
        lo,hi=links.UNITS[caller]
        for off in offsets:
            pc=lo+off
            target=links.direct_b(pc,read(pc))
            if not target or not target[1] or links.source_unit(target[0])!="Tree":
                raise ValueError("Real source Ball/KCol-to-Tree edge not found")
            callee=target[0]
            before=max(lo,pc-CALLER_BEFORE*4)
            after=min(hi,pc+(CALLER_AFTER+1)*4)
            if before!=pc-CALLER_BEFORE*4 or after!=pc+(CALLER_AFTER+1)*4:
                raise ValueError("Unbounded caller context")
            if callee + TARGET_WORDS*4 > links.UNITS["Tree"][1]:
                raise ValueError("Tree target outside source unit")
            def disas(addrs,mark=None):
                return [
                    f"{source_label(a)}  {read(a):08X}  {ppc(a,read(a))}"
                    +("   *** call to "+source_label(callee) if a==mark else "")
                    for a in addrs]
            output.append({
                "caller":caller,
                "caller_source_site":f"+0x{off:04X}",
                "tree_source_target":source_label(callee),
                "caller_instructions":disas(range(before,after,4),pc),
                "target_entry_instructions":disas(range(callee,callee+TARGET_WORDS*4,4)),
                "hitbox_semantics_verified":False,
            })
    return output


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Unsupported source capture")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            file=seven.src._file(roots[capture],f"{capture}.{i}.raw",size)
            handle=stack.enter_context(file.open("rb"))
            banks.append(stack.enter_context(mmap.mmap(
                handle.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        sample=seven._get(rd)
        field=sample["field"]
        count=rd.u32(field+0x1C)
        arr=rd.u32(field+0x20)
        if count!=94 or seven.roster._bank(arr,count*84)!="MEM2":
            raise ValueError("Source-owned tree array or count changed")
        def read(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("PPC address out of selected source")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
        if not links.tree_loop_source_gated(read):
            raise ValueError("Original tree-owner loop failed")
        result=inspect(read)
    seven._check_archive(archive)
    return {
        "kind":"P0_TREE_HITBOX_FIVE_CALLSITE_SOURCE_CONTEXT",
        "status":"BOUNDED_SOURCE_CALLS_TO_TREE",
        "capture":capture,"source_tree_count":count,
        "targets":result,
        "source_hitboxes_verified":False,
        "velocity_response_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=p.parse_args(argv)
    try:
        report=run(a.archive,a.capture)
        print(json.dumps({k:v for k,v in report.items() if k!="targets"},
                         sort_keys=True,separators=(",",":")))
        for target in report["targets"]:
            print(f"===== {target['caller']} {target['caller_source_site']} -> {target['tree_source_target']} =====")
            print("-- CALLER --")
            print("\n".join(target["caller_instructions"]))
            print("-- TREE TARGET --")
            print("\n".join(target["target_entry_instructions"]))
        print("===== END FIVE SOURCE CALLS =====")
        return 0
    except (OSError,ValueError,IndexError,KeyError,OverflowError,
            TypeError,AttributeError,struct.error):
        print('{"status":"ABSTAIN_TREE_SOURCE_CALLSITE","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
