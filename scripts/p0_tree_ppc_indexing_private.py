#!/usr/bin/env python3
"""Source-bound PPC audit of original Wii Sports Golf tree object construction.

Reads original SHA-gated private Rev1 MEM1 code only from existing numbered
archive. Reports PUBLIC unit-relative PPC instruction offsets/imm magnitudes
and branch-target source classes, never raw words, runtime pointers, memory
addresses, game binaries, plaintext vectors, or unverified tree locations.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven

MEM1 = 0x80000000
# The existing public RSPE01_01 splits.txt source map (ogws) and symbol map
# (kiwi515/ogws_info RSPE_r1.map.csv) identify these Rev1 code regions.
UNITS = {
    "MapObjBase": (0x8028F9FC, 0x80290B44),
    "FieldManager": (0x80290B44, 0x80294184),
    "MapObjTree": (0x80296238, 0x80296EA8),
    "MapObjTreeWater": (0x80296EA8, 0x80296F50),
}
# PUBLIC symbols: PmpProc2 at 802917D4; Golf::PmpProc at 80291F34;
# Golf::LoadCurrentHoleResources at 80293008. Compiler units may contain
# multiple functions, so treat named intervals as investigation WINDOWS,
# not independently proved exact C++ function boundaries.
WINDOWS = {
    "field_initialization_and_pmp_proc2": (0x80290B44, 0x80291F34),
    "field_pmp_processing": (0x80291F34, 0x80293008),
    "field_load_hole_resources": (0x80293008, 0x80294184),
    "tree_object_code": UNITS["MapObjTree"],
    "tree_reflection_code": UNITS["MapObjTreeWater"],
    "base_object_code": UNITS["MapObjBase"],
}
FOCUS_SOURCE_OFFSETS = (0x18, 0x1C, 0x20, 0x24, 0x28, 0x30, 0x3C, 0x44, 0x4C)
D_FORM_LOADS_STORES = {32:"lwz",33:"lwzu",34:"lbz",35:"lbzu",
                        36:"stw",37:"stwu",38:"stb",39:"stbu",
                        40:"lhz",41:"lhzu",42:"lha",43:"lhau",
                        44:"sth",45:"sthu",46:"lmw",47:"stmw",
                        48:"lfs",49:"lfsu",50:"lfd",51:"lfdu",
                        52:"stfs",53:"stfsu",54:"stfd",55:"stfdu"}
MAX_ITEMS = 32


def signed16(value):
    return value - 65536 if value & 0x8000 else value


def decode_branch(pc, word):
    if word >> 26 != 18:
        return None
    delta = word & 0x03FFFFFC
    if delta & 0x02000000:
        delta -= 0x04000000
    target = delta if word & 2 else pc + delta
    return (target & 0xFFFFFFFF, bool(word & 1))


def classify_branch_target(target):
    for name, (lo, hi) in UNITS.items():
        if lo <= target < hi:
            return name, f"+0x{target-lo:04X}"
    return "outside_selected_tree_code_units", None


def decode_word(pc, word, window):
    """Only limited PPC forms; unknown opcode never guessed as tree stride."""
    op = word >> 26
    source_lo = WINDOWS[window][0]
    offset = pc-source_lo
    at = f"+0x{offset:04X}"
    r_dst = (word >> 21) & 31
    r_a = (word >> 16) & 31
    imm = signed16(word & 65535)
    records = []
    if op == 7 and 4 <= abs(imm) <= 0x400:
        records.append(("mulli",{
            "window_relative_offset":at,"immediate":imm,
            "destination_register":r_dst,"index_register":r_a}))
    elif op == 14 and 4 <= abs(imm) <= 0x400:
        records.append(("addi",{
            "window_relative_offset":at,"immediate":imm,
            "destination_register":r_dst,"base_register":r_a}))
    elif op == 21:
        sh=(word>>11)&31
        mb=(word>>6)&31
        me=(word>>1)&31
        if 1<=sh<=10 and mb==0 and me==31-sh:
            records.append(("slwi",{
                "window_relative_offset":at,"shift_bits":sh,
                "multiplier_power_of_two":1<<sh,
                "destination_register":r_a,"source_register":r_dst}))
    elif op==31 and ((word>>1)&1023)==235:
        records.append(("mullw",{"window_relative_offset":at,
                                 "destination_register":r_dst}))
    if op in D_FORM_LOADS_STORES and imm in FOCUS_SOURCE_OFFSETS:
        records.append(("member_access",{
            "window_relative_offset":at,
            "mnemonic":D_FORM_LOADS_STORES[op],
            "field_offset":f"+0x{imm:02X}",
            "base_register":r_a,"value_register":r_dst}))
    branch=decode_branch(pc,word)
    if branch:
        target,linked=branch
        kind,relative=classify_branch_target(target)
        if kind in ("MapObjTree","MapObjTreeWater","MapObjBase"):
            records.append(("tree_call_or_jump",{
                "window_relative_offset":at,"target_public_unit":kind,
                "target_unit_relative_offset":relative,
                "linked_call":linked}))
    return records


def analyze_bounded_ppc(read_u32):
    """Pure source-text static scan. Not source-level register dataflow."""
    results={}
    for label,(start,end) in WINDOWS.items():
        categorized={c:[] for c in
            ("mulli","addi","slwi","mullw","member_access","tree_call_or_jump")}
        for pc in range(start,end,4):
            for typ,row in decode_word(pc,read_u32(pc),label):
                categorized[typ].append(row)
        tally=Counter(r["immediate"] for r in categorized["mulli"])
        result={
            "public_source_window":label,
            "static_words_examined":(end-start)//4,
            "potential_index_multiplier_counts":[
                {"immediate":k,"count":v}
                for k,v in sorted(tally.items(),key=lambda kv:(-kv[1],kv[0]))[:32]],
            "mulli_sites":categorized["mulli"][:MAX_ITEMS],
            "slwi_sites":categorized["slwi"][:MAX_ITEMS],
            "mullw_sites":categorized["mullw"][:MAX_ITEMS],
            "field_offset_access_sites":categorized["member_access"][:MAX_ITEMS],
            "tree_code_direct_branch_sites":categorized["tree_call_or_jump"][:MAX_ITEMS],
            "addi_candidate_count":len(categorized["addi"]),
            "addi_small_immediate_candidates": [
                r for r in categorized["addi"] if r["immediate"] in
                {0x48,0x58,0x60,0x68,0x70,0x80,0x90,0xA0,0xB0,0xC0,
                 0x100,0x110,0x120,0x140,0x160,0x180,0x1A0,0x200}
            ][:MAX_ITEMS],
            "omitted_per_kind_counts":{
                c:max(0,len(rows)-MAX_ITEMS) for c,rows in categorized.items()
                if len(rows)>MAX_ITEMS},
            "actual_receiver_dataflow_verified":False,
            "object_stride_verified":False,
            "tree_positions_verified":False,
        }
        results[label]=result
    return results


def run(archive:Path,capture:int):
    if capture not in range(1,8):
        raise ValueError("invalid capture")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        path=seven.src._file(folders[capture],f"{capture}.1.raw",seven.SIZE[0])
        handle=stack.enter_context(path.open("rb"))
        raw=stack.enter_context(mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ))
        # Source chain also requires MEM2. Read it to enforce existing selected
        # Golf scene, tee and pin gates before native code can be interpreted.
        p2=seven.src._file(folders[capture],f"{capture}.2.raw",seven.SIZE[1])
        f2=stack.enter_context(p2.open("rb"))
        raw2=stack.enter_context(mmap.mmap(f2.fileno(),0,access=mmap.ACCESS_READ))
        reader=seven.roster.TwoBankReader(raw,raw2)
        selected=seven._get(reader)
        field=selected["field"]
        count=reader.u32(field+0x1C)
        array=reader.u32(field+0x20)
        if not 3<=count<=4096 or seven.roster._bank(array,4)!="MEM2":
            raise ValueError("source-owned tree array/count missing")
        def words(pc):
            if not (MEM1<=pc<=MEM1+len(raw)-4):
                raise ValueError("not native MEM1")
            return struct.unpack_from(">I",raw,pc-MEM1)[0]
        result=analyze_bounded_ppc(words)
    seven._check_archive(archive)
    return {
        "kind":"P0_GOLF_TREE_SOURCE_PPC_INDEXING_AUDIT",
        "status":"PUBLIC_SOURCE_WINDOW_STATIC_SCAN",
        "capture":capture,"source_tree_count":count,
        "private_original_archive_SHA_validated":True,
        "source_qualified":True,
        "analysis":result,
        "tree_object_contiguous_or_pointer_table_verified":False,
        "gameplay_tree_collision_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive",type=Path,required=True)
    ap.add_argument("--capture",type=int,choices=range(1,8),default=7)
    a=ap.parse_args(argv)
    try:
        print(json.dumps(run(a.archive,a.capture),indent=2,sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,IndexError,KeyError,OverflowError,struct.error):
        print(json.dumps({"kind":"P0_GOLF_TREE_SOURCE_PPC_INDEXING_AUDIT",
                          "status":"ABSTAIN_ARCHIVE_OR_SOURCE",
                          "training_approved":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
