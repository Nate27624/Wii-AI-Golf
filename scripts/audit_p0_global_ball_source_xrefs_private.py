"""Exact Rev1 source-global ball slot xrefs, not arbitrary RAM or ball physics.

Uses existing #240 source-global slot proof and #230 phase-selected reader.
Only scans published Golf .text bounded units for direct PowerPC r13
D-form accesses to the single already verified source-global ball slot.
An absent direct store is not proof that other code cannot write it.
Output is public-source unit labels, counts and unit-relative instruction
offsets only. Raw instructions, data words, pointers, floats, paths, hashes
and RAM stay private; never uploads, writes or invokes Dolphin.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import mmap
from pathlib import Path
import sys

HERE=str(Path(__file__).resolve().parent)
if HERE in sys.path: sys.path.remove(HERE)
sys.path.insert(0,HERE)
import audit_p0_global_ball_roster_receiver_private as owner
import review_p0_global_slot_store_cfg as writer_cfg
import review_p0_global_slot_post_return_paths as post_return
import review_p0_global_slot_symbol_nullguard as public_symbol_guard
import review_p0_ball_constructor_return as constructor_return

seven=owner.seven
roster=owner.roster
prev=owner.prev

# Public RSPE01_01 split .text unit bounds; same as #219's published index.
UNITS=(
    ("RPGolMain",0x8028E098,0x8028E900),
    ("RPGolFieldManager",0x80290B44,0x80294184),
    ("RPGolMapObjBall",0x80296FD8,0x8029B240),
    ("RPGolSimulateManager",0x8029B240,0x8029BBB4),
    ("RPGolPlayer",0x8029E62C,0x802A2210),
    ("RPGolPlayerManager",0x802A2210,0x802A3560),
)
PHASES=(5,6,7)
# Source-ref enumeration is *not* execution or an exhaustive write alias search.
KINDS={
    32:"direct_lwz_read",
    33:"direct_lwzu_read_update",
    36:"direct_stw_write",
    37:"direct_stwu_write_update",
    14:"addi_address_formation",
    15:"addis_high_displacement_ambiguous",
}


def classify_source_refs(read, global_slot_offset:int) -> dict:
    if type(global_slot_offset) is not int or not -0x8000 <= global_slot_offset < 0x8000:
        raise ValueError("invalid signed source-global r13 displacement")
    hits=[]
    for name,lo,hi in UNITS:
        if lo%4 or hi%4 or lo>=hi:
            raise ValueError("invalid known published code interval")
        for pc in range(lo,hi,4):
            instr=read(pc)
            d=prev.dform(instr)
            if d["ra"]!=13 or d["imm"]!=global_slot_offset or d["op"] not in KINDS:
                continue
            hits.append({
                "source_unit":name,
                "unit_relative_pc":f"+0x{pc-lo:04X}",
                "source_access_type":KINDS[d["op"]],
            })
    if not any(x["unit_relative_pc"]==
               f"+0x{prev.GLOBAL_LOAD_PC-0x80296FD8:04X}"
               and x["source_unit"]=="RPGolMapObjBall"
               and x["source_access_type"]=="direct_lwz_read" for x in hits):
        raise ValueError("known source-global load not in vetted golf source unit")
    # Exact bounded source-only access counts; no runtime positions or words.
    counts={}
    for kind in KINDS.values():
        counts[kind]=sum(x["source_access_type"]==kind for x in hits)
    return {
        "source_golf_text_units_examined":len(UNITS),
        "golf_source_code_words_examined":sum((hi-lo)//4 for _,lo,hi in UNITS),
        "known_global_ball_load_instruction_confirmed":True,
        "global_slot_direct_r13_reference_counts":counts,
        "source_global_r13_reference_sites":hits[:32],
        "more_source_sites_not_printed":max(0,len(hits)-32),
        "source_slot_direct_writer_identified_in_these_units":
            counts["direct_stw_write"]+counts["direct_stwu_write_update"]>0,
        "non_r13_and_indirect_store_sources_not_examined":True,
        "direct_store_cannot_prove_executed_during_shot":True,
        "no_direct_store_cannot_disprove_indirect_writer":True,
    }



# This narrow window follows the previously verified 0x80299C70..0x8029A030
# source cache routine. It is a SOURCE CODE WINDOW, not a newly asserted
# function entry or executed control-flow path.
WRITER_WINDOW_START=0x8029A030
WRITER_PC=0x8029A05C
WRITER_UNIT_BASE=0x80296FD8


def classify_known_writer_value(read, displacement:int) -> dict:
    """Classify one exact stw's register source and bounded near-def.

    A static nearest write is not branch-sensitive reaching definition and
    can miss unrecognized opcodes, indirect aliasing or a call-clobbered reg.
    """
    word=read(WRITER_PC)
    d=prev.dform(word)
    if (d["op"],d["ra"],d["imm"])!=(36,13,displacement):
        raise ValueError("the sole source-global direct stw at reviewed PC changed")
    reg=d["rt"]  # For stw, D-form bits 21..25 encode rS, NOT an output rT.
    defs=[]
    hazards=[]
    for pc in range(WRITER_WINDOW_START,WRITER_PC,4):
        ins=read(pc)
        di=prev.dform(ins)
        op=di["op"]
        if op in (16,17,18) or (
            op==19 and ((ins>>1)&1023) in (16,50,528)):
            hazards.append(pc)
        source=None
        if op==14 and di["rt"]==reg:
            source=("literal_zero_candidate" if di["ra"]==0 and di["imm"]==0
                    else "addi_other")
        elif op==15 and di["rt"]==reg:
            source="addis_other"
        elif op in (32,33,34,35,40,42,46) and di["rt"]==reg:
            source="integer_memory_load"
        elif op==31 and ((ins>>1)&1023)==444:
            rs=(ins>>21)&31
            ra=(ins>>16)&31
            rb=(ins>>11)&31
            if ra==reg and rb==rs:
                source=("mr_from_same_reg" if rs==reg
                        else "mr_from_other_register")
        if source is not None:
            defs.append((pc,source))
    last=defs[-1] if defs else None
    later_hazard=any(pc>last[0] for pc in hazards) if last else bool(hazards)
    return {
        "source_unit":"RPGolMapObjBall",
        "source_unit_relative_store_pc":f"+0x{WRITER_PC-WRITER_UNIT_BASE:04X}",
        "exact_stw_source_slot_verified":True,
        "store_source_register":f"r{reg}",
        "candidate_nearest_recognized_definition_class":
            last[1] if last else "unknown_no_recognized_def_in_bounded_window",
        "candidate_nearest_definition_unit_relative_pc":
            f"+0x{last[0]-WRITER_UNIT_BASE:04X}" if last else None,
        "control_transfer_in_window":bool(hazards),
        "control_transfer_after_candidate_definition":later_hazard,
        "source_value_may_be_zero_candidate":
            bool(last and last[1]=="literal_zero_candidate"),
        "store_value_runtime_zero_verified":False,
        "source_register_reaching_definition_fully_verified":False,
        "source_writer_ran_during_wedge_verified":False,
        "window_is_not_verified_function_entry":True,
    }


def validate_and_read_three(directory:Path) -> dict:
    directory=seven._private_directory(directory)
    observations=[]
    code_ref=None
    source_digest=None
    global_slot=None
    for phase in PHASES:
        paths=seven._phase_banks(directory,phase)
        if paths is None:
            raise ValueError("wedge native MEM1/MEM2 pair absent")
        before={bank:seven._hash(path) for bank,path in paths.items()}
        with ExitStack() as stack:
            maps={}
            for bank,path in paths.items():
                fp=stack.enter_context(path.open("rb"))
                maps[bank]=stack.enter_context(mmap.mmap(fp.fileno(),0,access=mmap.ACCESS_READ))
            rd=roster.TwoBankReader(maps["MEM1"],maps["MEM2"])
            sample=seven._source_sample(maps["MEM1"],maps["MEM2"])
            code=prev.source_global_slot(rd.u32)
            if not code["static_source_global_slot_supported"]:
                raise ValueError("source-global slot not directly source-proven")
            runtime=prev.sample_runtime(rd.u32,sample,code)
            membership=owner.roster_global_membership(
                rd.u32,sample,runtime["_private_runtime_source_global_pointer"])
            if not membership["global_matches_exactly_zero_player_slots"]:
                raise ValueError("source-global unexpected roster member")
            disp=code["slot"]-prev.SDA_BASE
            if global_slot is None:
                global_slot=code["slot"]
            elif global_slot!=code["slot"]:
                raise ValueError("r13 global slot drifted across wedge")
            # Source ROM text/code must be bitwise invariant across all three
            # offline snapshots. Digests never leave this process.
            sha=hashlib.sha256()
            for _,lo,hi in UNITS:
                for pc in range(lo,hi,4):
                    sha.update(rd.u32(pc).to_bytes(4,"big"))
            digest=sha.digest()
            if source_digest is None:
                source_digest=digest
                code_ref=classify_source_refs(rd.u32,disp)
                code_ref["single_direct_slot_store_source_candidate"]=classify_known_writer_value(rd.u32,disp)
                code_ref["single_direct_slot_store_bounded_cfg"]=writer_cfg.analyze(rd.u32,disp)
                code_ref["single_direct_slot_store_post_return_paths"]=post_return.analyze(rd.u32,disp)
                code_ref["single_direct_slot_store_public_symbols_and_BO"]=public_symbol_guard.analyze(rd.u32,disp)
                code_ref["separate_global_ball_constructor_return_candidates"]=constructor_return.analyze(rd.u32)
            elif digest!=source_digest:
                raise ValueError("Rev1 golf source code differs across wedge phases")
            observations.append({
                "phase":phase,
                "global_source_outside_four_roster_balls":True,
                "global_current_equals_selected_cache_CC_components":
                    runtime["global_current_equals_selected_cache_CC_components"],
                "global_current_equals_selected_live_components":
                    runtime["global_current_equals_selected_current_components"],
                "_identity":sample["refs"],
                "_pin":sample["triplets"]["source_selected_pin"],
                "_start":sample["triplets"]["source_current_start"],
                "_hole":sample["hole"],
                "_slot":sample["selected_index"],
            })
        for bank,path in paths.items():
            if seven._hash(path)!=before[bank]:
                raise ValueError("native bank modified during source read")
    root=observations[0]
    for observation in observations[1:]:
        if (observation["_identity"]!=root["_identity"]
                or observation["_pin"]!=root["_pin"]
                or observation["_start"]!=root["_start"]
                or observation["_hole"]!=root["_hole"]
                or observation["_slot"]!=root["_slot"]):
            raise ValueError("wedge source actor/field/geometry changed")
    return {
        "kind":"P0-SANITIZED-R13-GLOBAL-BALL-DIRECT-SOURCE-XREFS",
        "wedge_phases_source_validated":3,
        "source_global_slot_identical_across_wedge":True,
        "source_code_identical_across_wedge":True,
        "source_selected_geometry_stable_across_wedge":True,
        "source_global_vs_selected_CC_live_relationships":[
            {key:value for key,value in item.items() if not key.startswith("_")}
            for item in observations
        ],
        "static_source_global_slot_xrefs":code_ref,
        "global_ball_owner_function_verified":False,
        "global_ball_role_as_simulated_prediction_verified":False,
        "cache_update_runtime_receiver_verified":False,
        "cache_update_executed_during_shot_verified":False,
        "real_ball_world_xyz_verified":False,
        "frame_atomicity_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump-directory",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        out=validate_and_read_three(args.dump_directory)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,AttributeError):
        print("P0 GLOBAL SOURCE XREF ABSTAIN: source-code, private pairs or"
              " selected object reference control changed.", file=sys.stderr)
        return 2
    print(json.dumps(out,sort_keys=True,indent=2,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
