#!/usr/bin/env python3
"""Offline, source-qualified Wii Remote D-pad integer selector triage.

Original RSPE01 Rev1 seven-pair archive SHA gate; public ogws function map.
Looks for code patterns involving published EGG/WPAD UP=0x0008 DOWN=0x0004
button bits, integer +/-1 steps, small comparisons, and non-stack integer
writes. Instructions, function membership and branch proximity do not prove
club-selection semantics or receiver ownership. Never connects to Dolphin.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import json
import mmap
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_club_controller_callgraph_private as graph
import audit_p0_club_selection_code_private as source
import audit_p0_club_player_byte_source_private as dec

UP=0x8
DOWN=0x4
MOTION_ONLY={0x802B4794,0x802B439C,0x802B4474}
MAX_FN=0x5000
MAX_CONTEXT=6

def rotate_mask(mb,me):
    """PPC MB/ME are counted MSB-first, inclusive, wrapping."""
    value=0
    i=mb
    while True:
        value |= 1 << (31-i)
        if i==me:
            break
        i=(i+1)%32
    return value

def _ror32(value, amount):
    amount %= 32
    if amount==0:
        return value & 0xffffffff
    return ((value>>amount)|(value<<(32-amount)))&0xffffffff

def immediate_button_test(w):
    opcode=source.op(w)
    if opcode in (28,29):
        mask=(w & 0xffff) << (16 if opcode==29 else 0)
        # Avoid treating unrelated broad masks such as 0xFFFF as
        # affirmative UP+DOWN tests. Exact one/two-bit masks only.
        if mask in (UP,DOWN,UP|DOWN):
            return {"opcode":"andis." if opcode==29 else "andi.",
                    "bits":mask,"rotated":False}
        return None
    if opcode==21:
        shift=(w>>11)&31
        mask=rotate_mask((w>>6)&31,(w>>1)&31)
        # PPC rlwinm rotates the *input* left by SH before masking.
        # The original input bits selected are ROR(mask, SH).
        original_bits=_ror32(mask,shift)
        if original_bits in (UP,DOWN,UP|DOWN):
            return {"opcode":"rlwinm"+("." if w&1 else ""),
                    "bits":original_bits,"rotated":bool(shift)}
    return None

def ordinal_step(w):
    if source.op(w)!=14:
        return None
    rd=(w>>21)&31
    ra=(w>>16)&31
    imm=source.signed16(w)
    if ra!=0 and imm in (-1,1):
        return {"reg":"r%d"%rd, "base":"r%d"%ra, "step":imm}
    return None

def pc_at(pc,units):
    return graph.format_site(pc,units)

def collect_function(w, f, units):
    """Read instruction words but report only coarse, public-bound offsets."""
    start,end,name,unit=f
    source.require(0<end-start<=MAX_FN and start%4==0 and end%4==0,
                   "FUNCTION_SPAN_INVALID")
    n=(end-start)//4
    words=struct.unpack_from(">"+("I"*n),w,start-source.MEM1)
    tests=[]
    steps=[]
    stores=[]
    small=[]
    conditional=[]
    for index,opcode in enumerate(words):
        b=immediate_button_test(opcode)
        if b:
            tests.append((index,b))
        p=ordinal_step(opcode)
        if p: steps.append((index,p))
        a=source.decode_access(opcode)
        if (a and a["op"] in ("stw","stb","sth") and
                a["base"] not in (0,1) and 0<=a["disp"]<=0x200):
            stores.append((index,a))
        if source.op(opcode) in (10,11) and 0<=source.signed16(opcode)<=16:
            small.append(index)
        if source.op(opcode)==16:
            conditional.append(index)

    # A D-pad-shaped test without an ordinal increment or write can still
    # matter; but never treat the constant mask itself as proof of input.
    up=[i for i,b in tests if b["bits"]&UP]
    down=[i for i,b in tests if b["bits"]&DOWN]
    if not (up or down):
        return None
    both=bool(up and down)
    anchor=min(up+down)
    prox_steps=[(i,d) for i,d in steps if abs(i-anchor)<=48]
    prox_stores=[(i,d) for i,d in stores if abs(i-anchor)<=64]
    near_cmp=sum(abs(i-anchor)<=48 for i in small)
    near_br=sum(abs(i-anchor)<=48 for i in conditional)
    # Rank pairs but retain low-scoring singular-bit readers, because
    # Up/Down handling may be split across different functions.
    score=(8*both+3*bool(prox_steps)+4*bool(prox_stores)+
           2*min(near_cmp,3)+min(near_br,3))
    if start in MOTION_ONLY: score-=8
    return {
        "function":name,
        "source_unit":unit,
        "source_relative_function_start":pc_at(start,units)["source_offset"],
        "function_bytes":end-start,
        "source_relative_up_test_sites":[pc_at(start+4*i,units)["source_offset"] for i in up[:8]],
        "source_relative_down_test_sites":[pc_at(start+4*i,units)["source_offset"] for i in down[:8]],
        "has_both_up_and_down_bit_shapes":both,
        "nearby_ordinal_steps":[{
            "pc":pc_at(start+4*i,units)["source_offset"],**d}
            for i,d in prox_steps[:8]],
        "nearby_nonstack_integer_stores":[{
            "pc":pc_at(start+4*i,units)["source_offset"],
            "operation":a["op"],
            "candidate_field_displacement":"+0x%03X"%a["disp"],
            "receiver_base_not_verified":"r%d"%a["base"],
            "value_register":"r%d"%a["reg"]}
            for i,a in prox_stores[:12]],
        "nearby_small_comparisons":near_cmp,
        "nearby_conditional_branches":near_br,
        "rank_score_not_evidence":score,
        "club_selector_source_verified":False,
        "dpad_input_register_proven":False,
        "stored_object_receiver_proven":False,
    }

def analyze_bank(bank, funcs, units, limit=25):
    source.require(1<=limit<=50,"BAD_RESULT_LIMIT")
    golf=[f for f in funcs if f[3].startswith(graph.GOLF_PREFIX)]
    found=[]
    for f in golf:
        # scan only these source-qualified published function text spans
        source.require(source.MEM1<=f[0]<f[1]<=source.MEM1+len(bank),
                       "FUNCTION_OUTSIDE_VERIFIED_BANK")
        result=collect_function(bank,f,units)
        if result is not None:
            found.append(result)
    found.sort(key=lambda x:(-x["rank_score_not_evidence"],
               x["source_unit"],x["source_relative_function_start"]))
    return {
        "status":"P0_REV1_DPAD_INTEGER_SELECTOR_STATIC_TRIAGE",
        "game_id":"RSPE01","revision":1,
        "public_dpad_up_bit":"0x0008",
        "public_dpad_down_bit":"0x0004",
        "public_button_defs":"ogws include/egg/core/eggController.h and include/revolution/WPAD/WPAD.h",
        "golf_functions_scanned":len(golf),
        "candidate_functions_with_direct_bit_shapes":len(found),
        "functions_with_both_up_down_shapes":
            sum(x["has_both_up_and_down_bit_shapes"] for x in found),
        "reported_candidates":found[:limit],
        "omitted_candidates":max(0,len(found)-limit),
        "masks_not_tied_to_actual_controller_status":True,
        "other_button_check_idioms_may_be_missed":True,
        "direct_published_bits_not_club_semantics":True,
        "selected_club_field_verified":False,
        "training_approved":False,
    }

def analyze_original(archive,capture,limit):
    file=source.sealed_bank(archive,capture)
    units=source.source_units(json.loads(source.INDEX.read_text("utf-8")))
    funcs=graph.parse_public_functions(json.loads(graph.FUNCS.read_text("utf-8")),units)
    with file.open("rb") as fh, closing(
            mmap.mmap(fh.fileno(),0,access=mmap.ACCESS_READ)) as bank:
        result=analyze_bank(bank,funcs,units,limit)
    result["original_archive_sha_preflight_passed"]=True
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path)
    p.add_argument("--capture",type=int,choices=range(1,8),default=5)
    p.add_argument("--limit",type=int,default=25)
    p.add_argument("--selftest",action="store_true")
    args=p.parse_args(argv)
    if args.selftest:
        arr=[
            (28<<26)|(3<<21)|(3<<16)|8,
            (14<<26)|(3<<21)|(3<<16)|1,
            (36<<26)|(3<<21)|(30<<16)|0x34,
            (28<<26)|(3<<21)|(3<<16)|4,
        ]
        unit="Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
        begin=0x802B4794
        bank=bytearray(begin-source.MEM1+len(arr)*4)
        struct.pack_into(">4I",bank,begin-source.MEM1,*arr)
        report=analyze_bank(bank,[(begin,begin+16,"synthetic",unit)],
                            {unit:(begin,begin+0x1000)})
        source.require(report["functions_with_both_up_down_shapes"]==1
                       and report["reported_candidates"][0]["nearby_ordinal_steps"]
                       and report["reported_candidates"][0]["nearby_nonstack_integer_stores"],
                       "SELFTEST_FAILED")
        print(json.dumps({"status":"SELFTEST_PASS","native_ram_used":False}))
        return 0
    if args.archive is None or not 1<=args.limit<=50:
        print(json.dumps({"status":"ABSTAIN_ARGS","training_approved":False}))
        return 2
    try:
        print(json.dumps(analyze_original(args.archive,args.capture,args.limit),
                         indent=2,sort_keys=True))
        return 0
    except (source.Abstain,TypeError,ValueError,KeyError,IndexError,
            OSError,ImportError,struct.error,OverflowError):
        print(json.dumps({"status":"ABSTAIN_VERIFIED_SOURCE_OR_ARCHIVE",
                          "training_approved":False}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
