"""P0 offline bounded PPC FPR-value producer clues near six exact player stores.

Purpose: find the closest syntactically plausible floating-register producer,
NOT prove the store's r30/r31 receiver or runtime execution.
Strictly source-relative code classes, no game values, raw PPC words,
runtime pointers, private paths, hashes or native RAM in output.
Requires #244 original B0 SHA/manifest and exact RSPE01 Rev1 provenance.
No Dolphin / shot / memory writes / network / training.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_player_record_store_candidates_private as owner
import audit_ball_xyz_source_callers_private as upstream

PLAYER="RPGolPlayer"
# Original OPERATOR source-validated D-form stfs instructions.
# Relative to upstream published RPGolPlayer compilation unit only.
SITES=(
    (0x0FAC,0x30,0,31),
    (0x0FE4,0x30,0,31),
    (0x0FF8,0x30,0,31),
    (0x1FFC,0x30,3,30),
    (0x2008,0x30,0,30),
    (0x1C18,0x90,0,31),
)
MAX_BACK_BYTES=96
CONTEXT_BEFORE=8
CONTEXT_AFTER=2

def word_at(data:bytes,offset:int)->int:
    if type(data) is not bytes or offset<0 or offset%4 or offset+4>len(data):
        raise ValueError("outside bounded source unit")
    return struct.unpack_from(">I",data,offset)[0]

def source_offset(off:int)->str:
    if off<0 or off%4:
        raise ValueError("bad source offset")
    return f"+0x{off:04X}"

def op_class(word:int)->dict:
    if type(word) is not int or not 0<=word<=0xffffffff:
        raise ValueError("invalid public-source PPC word")
    op=word>>26
    rt=(word>>21)&31
    ra=(word>>16)&31
    if op in (16,17,18,19):
        # Barrier regardless of whether a given opcode-19 instruction is
        # a branch, conservatively avoiding false "reaching" f0 claims.
        return {"kind":"flow_or_control_barrier","fpr_def":None,"base_reg":None,"barrier":True}
    if op in (48,49,50,51):
        return {"kind":{48:"lfs",49:"lfsu",50:"lfd",51:"lfdu"}[op],
                "fpr_def":rt,"base_reg":ra,"barrier":False}
    if op in (52,53,54,55):
        return {"kind":{52:"stfs",53:"stfsu",54:"stfd",55:"stfdu"}[op],
                "fpr_def":None,"base_reg":ra,"barrier":False}
    if op in (59,63,4):
        # Some PPC FP/control variants do not actually write RT;
        # this is a possible producer, NEVER a proven definition.
        return {"kind":{59:"fp_single_possible_writer",
                        63:"fp_double_or_control_possible_writer",
                        4:"paired_single_possible_writer"}[op],
                "fpr_def":rt,"base_reg":None,"barrier":False}
    if op in (32,33,34,35,40,41,42,43):
        return {"kind":"integer_load","fpr_def":None,"base_reg":ra,"barrier":False}
    if op in (36,37,38,39,44,45,46,47):
        return {"kind":"integer_store","fpr_def":None,"base_reg":ra,"barrier":False}
    if op in (14,15,24,25,26,27,28,29,31):
        return {"kind":"integer_or_extended","fpr_def":None,"base_reg":None,"barrier":False}
    return {"kind":"unclassified_not_proven_FPR_writer","fpr_def":None,
            "base_reg":None,"barrier":False}

def verify_exact_sites(unit:bytes):
    if type(unit) is not bytes or len(unit)<max(s[0] for s in SITES)+4:
        raise ValueError("required source unit absent")
    for off,disp,fs,base in SITES:
        word=word_at(unit,off)
        if owner.decode_dform_store(word)!=("stfs",fs,base,disp):
            raise ValueError("exact Rev1 source store site drift")
    return True

def nearest_fpr_clue(unit:bytes,off:int,target_fpr:int)->dict:
    if off<MAX_BACK_BYTES or off+4>len(unit) or target_fpr not in range(32):
        raise ValueError("bad bounded FPR source study")
    scanned=0
    for pc in range(off-4,off-MAX_BACK_BYTES-1,-4):
        decoded=op_class(word_at(unit,pc))
        scanned+=1
        if decoded["barrier"]:
            return {"origin_class":"control_flow_barrier",
                    "source_relative_instruction":source_offset(pc),
                    "instructions_back":scanned,
                    "register_value_producer_proven":False}
        if decoded["fpr_def"]==target_fpr:
            # Label "candidate", even for lfs/lfd; this is only
            # one linear predecessor, no executing CFG evidence.
            return {"origin_class":decoded["kind"],
                    "source_relative_instruction":source_offset(pc),
                    "instructions_back":scanned,
                    "register_value_producer_proven":False}
    return {"origin_class":"no_local_FPR_producer_found",
            "source_relative_instruction":None,
            "instructions_back":scanned,
            "register_value_producer_proven":False}

def describe(unit:bytes)->dict:
    verify_exact_sites(unit)
    sites=[]
    for off,disp,fs,ra in SITES:
        context=[]
        for pc in range(off-CONTEXT_BEFORE*4,off+(CONTEXT_AFTER+1)*4,4):
            d=op_class(word_at(unit,pc))
            context.append({
                "source_relative_instruction":source_offset(pc),
                "instruction_class":d["kind"],
                "possible_fpr_destination":None if d["fpr_def"] is None
                    else f"f{d['fpr_def']}",
                "source_memory_base":None if d["base_reg"] is None
                    else f"r{d['base_reg']}",
                "possible_flow_barrier":d["barrier"],
            })
        sites.append({
            "source_unit":PLAYER,
            "source_relative_store":source_offset(off),
            "member_displacement_candidate":f"+0x{disp:03X}",
            "stored_fpr":f"f{fs}",
            "unverified_receiver_base":f"r{ra}",
            "bounded_fpr_producer_hint":nearest_fpr_clue(unit,off,fs),
            "context":context,
            "selected_player_record_receiver_verified":False,
            "store_executed_during_wedge_verified":False,
        })
    return {
        "kind":"P0-PLAYER-FLOAT-SIX-STORE-LOCAL-PRODUCER-CLUES",
        "schema_version":1,
        "source_game":"RSPE01",
        "disc_revision":1,
        "exact_six_operator_stores_source_verified":True,
        "source_b0_original_archive_sha_verified":True,
        "site_count":len(sites),
        "site_evidence":sites,
        "complete_reaching_definitions_or_call_graph":False,
        "selected_record_receiver_identity_verified":False,
        "runtime_writers_verified":False,
        "source_FPR_clue_proves_float_game_semantics":False,
        "physical_xyz_verified":False,
        "velocity_verified":False,
        "power_verified":False,
        "impact_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }

def audit(session:Path,data_root:Path):
    # First invoke exact existing #244 original B0 SHA/Rev1/source reader.
    source_report=owner.audit(session,data_root)
    if (source_report.get("native_source_b0_sha256_verified_before_and_after_read") is not True
            or source_report.get("approved_for_training") is not False):
        raise ValueError("original B0 source/manifest qualification refused")
    target=upstream.checked_private_b0(session,data_root)
    unit=next(((lo,hi) for name,lo,hi in upstream.UNITS if name==PLAYER),None)
    if unit is None:
        raise ValueError("public Player source unit not grounded")
    lo,hi=unit
    if hi<=lo or hi-lo>0x100000 or lo<upstream.MEM1_START:
        raise ValueError("invalid public source range")
    with target.open("rb") as fp:
        fp.seek(lo-upstream.MEM1_START)
        data=fp.read(hi-lo)
    # Original B0 cannot change even after the source-only read.
    upstream.checked_private_b0(session,data_root)
    return describe(data)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--private-session",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        report=audit(args.private_session,args.data_root)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,AttributeError,struct.error,
            upstream.UntrustedInput):
        print("P0 FPR producer study ABSTAINED: private SHA/Rev1/site/owner gate failed.",
              file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
