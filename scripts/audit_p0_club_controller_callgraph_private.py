#!/usr/bin/env python3
"""Source-qualified static Golf function/caller trace from original private Rev1 MEM1.

Uses published, exact ogws function metadata plus the canonical original
seven-pair SHA gate. Reports public source-relative offsets and bounded
summaries only. Direct calls are *static edges*, not execution evidence.
"""
from __future__ import annotations
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from contextlib import closing
import json
import mmap
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_club_selection_code_private as base

FUNCS = ROOT / "research/source_maps/RSPE01_01_public_golf_controller_functions.json"
PLAYER = "Pack/RPSports/RPGolScene/RPGolPlayer.cpp"
CONFIG = "Pack/RPSports/RPGolScene/RPGolConfig.cpp"
GOLF_PREFIX = "Pack/RPSports/RPGolScene/"
INPUT_SOURCES = {
    "Pack/RPKernel/RPSysController.cpp",
    "Pack/RPKernel/RPSysControllerMgr.cpp",
    "egg/core/eggController.cpp",
    "revolution/KPAD/KPAD.c",
    "revolution/PAD/Pad.c",
    "revolution/WPAD/WPAD.c",
}
SENTINEL_FLAGS = {0x34, 0x35}
FLOAT_DERIVED = {0x94, 0x98, 0x9C, 0xA0, 0xA4, 0xA8,
                 0xAC, 0xB0, 0xB4, 0xB8, 0xBC, 0xC0}
MAX_CONTEXT_SITES = 28
MIN_FN = 0x8028DF74
END_FN = 0x802A3560

def parse_public_functions(payload, public_units):
    base.require(isinstance(payload, dict) and
        payload.get("kind") == "PUBLIC_OGWS_RSPE01_REV1_FUNCTION_SYMBOLS_FOCUSED"
        and payload.get("disc_id") == "RSPE01"
        and payload.get("revision") == 1
        and payload.get("upstream_git_blob_sha") ==
            "ec42efd5ef247dff7920e905f9004fc579dd3f74",
        "PUBLIC_FUNCTION_SYMBOLS_UNQUALIFIED")
    items = payload.get("functions")
    base.require(isinstance(items, list) and len(items) >= 400,
                 "PUBLIC_FUNCTION_SYMBOLS_INCOMPLETE")
    result = []
    previous_end = 0
    for item in items:
        base.require(isinstance(item, list) and len(item) == 3,
                     "PUBLIC_FUNCTION_ROW_INVALID")
        addr, n, label = item
        base.require(isinstance(addr, str) and addr.startswith("0x")
                     and type(n) is int and n > 0 and n % 4 == 0
                     and n <= 0x5000 and isinstance(label, str)
                     and 0 < len(label) <= 160,
                     "PUBLIC_FUNCTION_ROW_INVALID")
        try:
            pc = int(addr, 16)
        except ValueError:
            raise base.Abstain("PUBLIC_FUNCTION_ADDRESS_INVALID") from None
        owner = next((name for name, (lo, hi) in public_units.items()
                      if lo <= pc and pc+n <= hi), None)
        base.require(owner is not None and pc % 4 == 0
                     and pc >= previous_end,
                     "PUBLIC_FUNCTION_BOUNDARY_INVALID")
        result.append((pc, pc+n, label, owner))
        previous_end = pc+n
    base.require(any(a <= 0x8029E62C < b for a,b,_,_ in result)
                 and any(a <= 0x8029CA4C < b for a,b,_,_ in result),
                 "PUBLIC_FUNCTION_PLAYER_CONFIG_MISSING")
    return result

def source_owner(pc, spans):
    for name, (lo,hi) in spans.items():
        if lo <= pc < hi:
            return name
    return None

def format_site(pc, units):
    name = source_owner(pc, units)
    if name is None:
        return {"unit": "OUTSIDE_PUBLISHED_SOURCE", "source_offset": None}
    return {"unit": name,
            "source_offset": "+0x%05X" % (pc - units[name][0])}

def function_at(pc, funcs, starts=None):
    if starts is None:
        starts = [z[0] for z in funcs]
    i = bisect_right(starts, pc)-1
    if i < 0 or pc >= funcs[i][1]:
        return None
    return funcs[i]

def static_instruction_records(bank, units, funcs):
    """Scan only executable published Golf functions; do not scan heap bytes."""
    records = []
    entry_golf = [f for f in funcs if f[3].startswith(GOLF_PREFIX)]
    for start, end, label, owner in entry_golf:
        offset = start-base.MEM1
        base.require(0 <= offset < offset+(end-start) <= len(bank),
                     "GOLF_SOURCE_TEXT_OUTSIDE_MEM1")
        words = struct.unpack_from(">"+("I"*((end-start)//4)), bank, offset)
        calls = []
        stores = []
        small_cmp = 0
        bit_tests = 0
        branches = 0
        for j, w in enumerate(words):
            pc = start+4*j
            branch = base.decode_branch(pc,w)
            if branch is not None:
                if branch["link"] and branch["target"] >= base.MEM1:
                    calls.append((pc,branch["target"]))
                elif not branch["link"]:
                    branches+=1
            if base.op(w) == 16:
                branches+=1
            if base.op(w) in (28,29):
                bit_tests+=1
            if base.op(w) in (10,11) and -1 <= base.signed16(w) <= 16:
                small_cmp+=1
            a = base.decode_access(w)
            if (a and a["op"] in ("stb","sth","stw")
                    and a["base"] not in (0,1)
                    and 0 <= a["disp"] <= 0x240):
                stores.append((pc,a))
        records.append({"start":start,"end":end,"name":label,
                        "owner":owner,"calls":calls,"stores":stores,
                        "small_comparisons":small_cmp,
                        "bit_tests":bit_tests,"branches":branches})
    return records

def analyze(records, funcs, units, *, limit=24):
    base.require(type(limit) is int and 1 <= limit <= 50,
                 "BAD_REPORT_LIMIT")
    starts = [f[0] for f in funcs]
    by_start = {r["start"]:r for r in records}
    direct_edges = []
    incoming = defaultdict(set)
    input_calls = []
    for src in records:
        for call_pc, dst_pc in src["calls"]:
            dest_fn=function_at(dst_pc,funcs,starts)
            dst_name = source_owner(dst_pc,units)
            if dest_fn:
                incoming[dest_fn[0]].add(src["start"])
            edge={"caller":src["start"],"call_pc":call_pc,
                  "destination":dest_fn[0] if dest_fn else None,
                  "destination_source":dst_name}
            direct_edges.append(edge)
            if dst_name in INPUT_SOURCES:
                input_calls.append(edge)
    def public_fn(pc):
        f=function_at(pc,funcs,starts)
        if f is None:
            return None
        return {"public_function":f[2],
                **format_site(f[0],units),
                "function_bytes":f[1]-f[0]}
    def caller_descendants(seed, depth=2):
        layers=[]
        visited={seed}
        current={seed}
        for _ in range(depth):
            nxt=set()
            for f in current:
                nxt.update(incoming.get(f,()))
            nxt.difference_update(visited)
            layers.append([public_fn(x) for x in sorted(nxt)][:16])
            visited.update(nxt)
            current=nxt
        return layers
    wanted=[]
    for record in records:
        if record["owner"] != PLAYER:
            continue
        for pc, a in record["stores"]:
            if a["op"]=="stb" and a["disp"] in SENTINEL_FLAGS:
                wanted.append((record,pc,a))
    anchors=[]
    for record,pc,a in wanted:
        if a["disp"] != 0x34:
            continue
        store35=any(store["op"]=="stb" and store["disp"]==0x35
                    and store["base"]==a["base"] and abs(at-pc)<=20
                    for at,store in record["stores"])
        calls = []
        for _cp,dest in record["calls"]:
            f=function_at(dest,funcs,starts)
            calls.append(public_fn(f[0]) if f else {
                "destination_code_unit":source_owner(dest,units)
                or "OUTSIDE_PUBLISHED_SOURCE"})
        anchors.append({
            "instruction":format_site(pc,units),
            "enclosing_function":public_fn(record["start"]),
            "source_pair_plus_35_nearby":store35,
            "same_function_source_calls":calls[:8],
            "direct_callers_depth1_depth2":caller_descendants(record["start"]),
            "all_callers_may_be_indirect":True,
            "selected_player_receiver_proven":False,
            "club_switch_execution_proven":False,
        })
    ranked=[]
    for r in records:
        if r["owner"] not in (PLAYER,CONFIG,
                            "Pack/RPSports/RPGolScene/RPGolPlayerManager.cpp",
                            "Pack/RPSports/RPGolScene/RPGolMain.cpp"):
            continue
        byte_stores=[(p,a) for p,a in r["stores"]
                     if a["op"] in ("stb","sth")]
        if not byte_stores:
            continue
        touches34=any(a["disp"] in SENTINEL_FLAGS
                      for _,a in byte_stores)
        incoming_count=len(incoming.get(r["start"],()))
        direct_input_calls=sum(source_owner(dst,units) in INPUT_SOURCES
                               for _,dst in r["calls"])
        score=(6*int(touches34)+3*min(r["bit_tests"],3)
               +2*min(r["small_comparisons"],3)
               +2*min(direct_input_calls,3)
               +int(incoming_count>0))
        if score < 3:
            continue
        ranked.append({
            "function":public_fn(r["start"]),
            "rank_not_proof":score,
            "source_byte_halfword_stores":len(byte_stores),
            "touches_displacement_34_or_35":touches34,
            "small_integer_comparisons":r["small_comparisons"],
            "andi_bit_test_shapes":r["bit_tests"],
            "direct_input_unit_calls":direct_input_calls,
            "in_scope_static_direct_caller_count":incoming_count,
            "possible_club_selection_only":True,
        })
    ranked.sort(key=lambda x:(-x["rank_not_proof"],
        x["function"]["unit"],x["function"]["source_offset"]))
    return {
        "kind":"P0_OFFLINE_SOURCE_FUNCTION_CALLGRAPH_CLUB_TRIAGE",
        "status":"STATIC_PUBLIC_FUNCTION_BOUNDED",
        "game_id":"RSPE01","revision":1,
        "original_archive_sha_preflight_passed":True,
        "function_metadata_source":"public_doldecomp_ogws_RSPE01_01_symbols",
        "public_golf_functions_scanned":len(records),
        "static_direct_calls_from_golf":len(direct_edges),
        "direct_golf_to_input_unit_calls":len(input_calls),
        "golf_to_input_callsite_examples":[{
            "caller":public_fn(x["caller"]),
            "callsite":format_site(x["call_pc"],units),
            "destination_source":x["destination_source"],
            "destination_public_function":public_fn(x["destination"])
            if x["destination"] is not None else None
        } for x in input_calls[:limit]],
        "player_34_writer_function_anchors":anchors[:16],
        "candidate_function_ranking":ranked[:limit],
        "ranked_candidates_omitted":max(0,len(ranked)-limit),
        "dpad_input_bit_semantics_verified":False,
        "direct_calls_miss_indirect_dispatch":True,
        "selected_club_variable_verified":False,
        "game_executed_function_verified":False,
        "training_approved":False,
    }

def analyze_original(archive, capture, limit):
    bank_file=base.sealed_bank(archive,capture)
    units=base.source_units(json.loads(base.INDEX.read_text("utf-8")))
    funcs=parse_public_functions(json.loads(FUNCS.read_text("utf-8")),units)
    with bank_file.open("rb") as fh, closing(
            mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)) as mm:
        records=static_instruction_records(mm,units,funcs)
    return analyze(records,funcs,units,limit=limit)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path)
    p.add_argument("--capture",type=int,default=5,choices=range(1,8))
    p.add_argument("--limit",type=int,default=20)
    p.add_argument("--selftest",action="store_true")
    args=p.parse_args(argv)
    if args.selftest:
        tiny=[{"start":0x8029E62C,"end":0x8029E63C,
               "name":"fn_8029E62C","owner":PLAYER,
               "calls":[],"stores":[(0x8029E630,{
                   "op":"stb","base":3,"reg":4,"disp":0x34}),
                   (0x8029E634,{"op":"stb","base":3,"reg":0,"disp":0x35})],
               "small_comparisons":1,"bit_tests":0,"branches":0}]
        f=[(0x8029E62C,0x8029E63C,"fn_8029E62C",PLAYER)]
        u={PLAYER:(0x8029E62C,0x802A2210)}
        result=analyze(tiny,f,u,limit=5)
        base.require(result["player_34_writer_function_anchors"][0]
                     ["source_pair_plus_35_nearby"],"SYNTHETIC_SELFTEST_FAILURE")
        print(json.dumps({"status":"SELFTEST_PASS","native_ram_used":False}))
        return 0
    if args.archive is None or not 1<=args.limit<=50:
        print(json.dumps({"status":"ABSTAIN_ARGS","training_approved":False}))
        return 2
    try:
        r=analyze_original(args.archive,args.capture,args.limit)
        print(json.dumps(r,indent=2,sort_keys=True))
        return 0
    except (base.Abstain,ValueError,KeyError,TypeError,IndexError,
            OSError,ImportError,struct.error,OverflowError):
        print(json.dumps({"status":"ABSTAIN_SOURCE_BOUNDARIES_OR_ARCHIVE",
                          "training_approved":False}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
