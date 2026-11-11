#!/usr/bin/env python3
"""Bounded Rev1 PowerPC source window for tree r28 receiver triage.

Operator-only, SHA/source-gated, read-only. Prints at most 96 public CODE
instructions around FieldManager source window +0x06BC r28<-r3 and +0x06E8,
+0x06FC loads. Optional raw code WORDS are not published, committed, or
used as training labels. Never dumps runtime heap data, tree coordinates,
native capture paths, or an entire source unit.
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
import p0_tree_ppc_indexing_private as src

MEM1=0x80000000
BASE=src.WINDOWS["field_load_hole_resources"][0]
START=0x05D0
END=0x0750
MAX_WORDS=(END-START)//4
assert MAX_WORDS==96
ANCHORS={
    0x06BC:"r28 <- r3 (latest observed)",
    0x06E8:"candidate +0x20(r28) read",
    0x06FC:"candidate +0x1C(r28) read",
}
D_OP={32:"lwz",33:"lwzu",34:"lbz",35:"lbzu",36:"stw",37:"stwu",
      38:"stb",39:"stbu",40:"lhz",42:"lha",44:"sth",48:"lfs",
      50:"lfd",52:"stfs",54:"stfd"}


def reg(n):
    return "r"+str(n)


def signed16(i):
    return i-65536 if i&0x8000 else i


def branch_label(dst):
    for name,(lo,hi) in src.UNITS.items():
        if lo<=dst<hi:
            return name+"+0x"+format(dst-lo,"04X")
    if src.UNITS["FieldManager"][0]<=dst<src.UNITS["FieldManager"][1]:
        return "FieldManager+0x"+format(dst-src.UNITS["FieldManager"][0],"04X")
    return "outside-bounded-golf-source-units"


def decode(pc, word):
    op=word>>26
    rt=(word>>21)&31
    ra=(word>>16)&31
    rb=(word>>11)&31
    imm=signed16(word&0xFFFF)
    if op in D_OP:
        return f"{D_OP[op]} {reg(rt)},{imm:+d}({reg(ra)})"
    if op in (14,15,7):
        return f"{ {14:'addi',15:'addis',7:'mulli'}[op] } {reg(rt)},{reg(ra)},{imm:+d}"
    if op in (24,25):
        return f"{ {24:'ori',25:'oris'}[op] } {reg(ra)},{reg(rt)},0x{word&0xFFFF:04X}"
    if op in (10,11):
        return f"{'cmplwi' if op==10 else 'cmpwi'} {reg(ra)},{imm:+d}"
    if op==18:
        result=src.decode_branch(pc,word)
        if result:
            dst,link=result
            return ("bl " if link else "b ")+branch_label(dst)
    if op==16:
        d=word&0xFFFC
        if d&0x8000:
            d-=0x10000
        dst=(d if word&2 else pc+d)&0xFFFFFFFF
        return f"bc BO={(word>>21)&31} BI={(word>>16)&31} -> {branch_label(dst)}"
    if op==19:
        xo=(word>>1)&1023
        if xo in (16,528):
            return "blr/bclr" if xo==16 else "bctr/bcctr"
    if op==21:
        sh=(word>>11)&31
        mb=(word>>6)&31
        me=(word>>1)&31
        if mb==0 and me==31-sh and 1<=sh<=10:
            return f"slwi {reg(ra)},{reg(rt)},{sh}"
        return f"rlwinm {reg(ra)},{reg(rt)},SH={sh},MB={mb},ME={me}"
    if op==31:
        xo=(word>>1)&1023
        if xo==444:
            return (f"mr {reg(ra)},{reg(rt)}" if rt==rb
                    else f"or {reg(ra)},{reg(rt)},{reg(rb)}")
        if xo==266:
            return f"add {reg(rt)},{reg(ra)},{reg(rb)}"
        if xo==235:
            return f"mullw {reg(rt)},{reg(ra)},{reg(rb)}"
        if xo==23:
            return f"lwzx {reg(rt)},{reg(ra)},{reg(rb)}"
        if xo==151:
            return f"stwx {reg(rt)},{reg(ra)},{reg(rb)}"
        if xo in (339,467):
            spr=((word>>16)&31)|(((word>>11)&31)<<5)
            suffix={8:"lr",9:"ctr"}.get(spr,"other_spr")
            return ("mf" if xo==339 else "mt")+suffix+" "+reg(rt)
        if xo==28:
            return f"and {reg(ra)},{reg(rt)},{reg(rb)}"
    return f"op{op}/undecoded"


def build_lines(words, start=START):
    if len(words)!=MAX_WORDS:
        raise ValueError("exact public code window required")
    out=[]
    for index,word in enumerate(words):
        off=start+4*index
        at=BASE+off
        marker=ANCHORS.get(off)
        text=f"+0x{off:04X}  {word:08X}  {decode(at,word)}"
        if marker:
            text+="   *** "+marker
        out.append(text)
    return out


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("Invalid capture")
    roots=seven._check_archive(archive)
    with ExitStack() as stack:
        m=[]
        for bank,size in enumerate(seven.SIZE,1):
            file=seven.src._file(roots[capture],f"{capture}.{bank}.raw",size)
            handle=stack.enter_context(file.open("rb"))
            m.append(stack.enter_context(mmap.mmap(
                handle.fileno(),0,access=mmap.ACCESS_READ)))
        reader=seven.roster.TwoBankReader(*m)
        sample=seven._get(reader)
        field=sample["field"]
        count=reader.u32(field+0x1C)
        array=reader.u32(field+0x20)
        if not 3<=count<=4096 or seven.roster._bank(array,4)!="MEM2":
            raise ValueError("source tree owner unqualified")
        words=struct.unpack_from(">"+("I"*MAX_WORDS),m[0],BASE+START-MEM1)
        if decode(BASE+0x06BC,words[(0x06BC-START)//4])!="mr r28,r3":
            raise ValueError("r28 source anchor changed")
        for off,delta in ((0x06E8,0x20),(0x06FC,0x1C)):
            word=words[(off-START)//4]
            if word>>26!=32 or ((word>>16)&31)!=28 or (word&0xFFFF)!=delta:
                raise ValueError("tree-load source anchor changed")
        lines=build_lines(words)
    seven._check_archive(archive)
    return {"capture":capture,"source_tree_count":count,
            "status":"BOUNDED_PPC_R28_SOURCE_DISASSEMBLY",
            "public_window":"RPGolFieldManager / load-hole resource",
            "public_relative_range":"+0x05D0..+0x074C",
            "instruction_count":len(lines),"receiver_proven":False,
            "tree_layout_proven":False,"training_approved":False},lines


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=parser.parse_args(argv)
    try:
        report,lines=run(a.archive,a.capture)
    except (OSError,ValueError,OverflowError,TypeError,IndexError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_SOURCE_BOUNDARY","training_approved":false}')
        return 2
    print(json.dumps(report,sort_keys=True,separators=(",",":")))
    print("---- BEGIN 96 BOUNDED SOURCE INSTRUCTIONS ----")
    print("\n".join(lines))
    print("---- END ----")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
