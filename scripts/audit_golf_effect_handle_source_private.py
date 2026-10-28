"""Rev1 code-only RPSysEffect HandleBase and FieldManager r31 source triage.

Search the already preserved SHA-checked B0 PPC code. No Dolphin launch,
new RAM scan, hidden pointer disclosure or data writes. A matching D-form
offset is not a proof of receiver identity. The source header says
RPSysEffect+0x78 contains HandleBase {u32 ID, LinkedObject* pointer}.
Source: doldecomp/ogws include/Pack/RPKernel/RPSysEffectBase.h,
include/nw4r/ef/ef_handle.h, src/nw4r/ef/ef_handle.cpp.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

SCRIPTS=str(Path(__file__).resolve().parent)
if SCRIPTS not in sys.path:
    sys.path.insert(0,SCRIPTS)

import audit_golf_aim_ppc_context_private as context
import audit_golf_aim_ppc_offsets_private as dform
import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_four_phase_private as four
import audit_selected_ball_start_link_private as selected

EFFECT_TEXT_START=0x80194158
EFFECT_TEXT_END=0x801957C0
FIELD_START=0x80290D50
FIELD_END=0x80290E4C
TARGETS=(0x78,0x7C)
MAX_SOURCE_HITS=130
MAX_CONTEXTS=18
# These source-code PCs were independently observed in the operator's actual
# RSPE01 Rev1 saved B0 image, not inferred from guessed structures.
R31_FROM_R3_PC=0x80290DD0
R31_FROM_R3_WORD=0x7C7F1B78
R29_FROM_R31_PC=0x80290E4C
R29_FROM_R31_WORD=0x7FFDFB78
FIELD_METHOD_SHAPED_PROLOGUE=0x80290DB0
LOOP_LOAD_CHILD_PC=0x80290E78
LOOP_LOAD_CHILD_WORD=0x807D0004
LOOP_ADVANCE_PC=0x80290EB8
LOOP_ADVANCE_WORD=0x3BBD0004


def _method_shaped_prologue(word:int)->bool:
    """Likely PPC stack frame stwu r1,-N(r1), not independently a CFG entry."""
    return (type(word) is int and (word>>26)==37
            and (word>>21)&31==1 and (word>>16)&31==1
            and bool(word&0x8000))


def _compatible_with_handle_word(hit:dict)->bool:
    """Opcode filter only, NOT a base-pointer or handle ownership assertion."""
    if hit["access"]=="write":
        return hit["mnemonic"] in ("stw","stwu")
    if hit["access"]=="read":
        return hit["mnemonic"] in ("lwz","lwzu")
    return False


def r31_assignment_candidate(word:int,pc:int):
    """Conservative source reg destination checks, unknown ext op stays unknown."""
    if type(word) is not int or not 0<=word<0x100000000 or pc & 3:
        raise ValueError("Invalid aligned PPC word")
    op=word>>26
    rt=(word>>21)&31
    ra=(word>>16)&31
    rb=(word>>11)&31
    if op==31 and (word>>1)&0x3FF==444 and ra==31:
        return {"pc":f"0x{pc:08X}",
                "type":"or_or_mr_to_r31",
                "source_registers":[f"r{rt}",f"r{rb}"]}
    if op in (14,15,32,33,34,35,40,41,42,43,46) and rt==31:
        return {"pc":f"0x{pc:08X}","type":"known_dform_r31_destination",
                "source_registers":[f"r{ra}"]}
    if op in (20,21,23,24,25,26,27,28,29) and ra==31:
        return {"pc":f"0x{pc:08X}","type":"known_immediate_or_shift_r31_destination",
                "source_registers":[f"r{rt}"]}
    # Low-level indexed arithmetic and load-store instructions might also
    # assign r31; this scanner is NOT exhaustive source register dataflow.
    return None


def _around(get_word,pc:int,start:int,end:int,before=5,after=7):
    return [{
        "pc":f"0x{addr:08X}",
        "word":f"0x{get_word(addr):08X}",
        "approximate_disassembly":context.decode(get_word(addr),addr)}
        for addr in range(max(start,pc-4*before),min(end,pc+4*(after+1)),4)]


def analyze(get_word):
    if ((EFFECT_TEXT_START|EFFECT_TEXT_END|FIELD_START|FIELD_END)&3
            or EFFECT_TEXT_END-EFFECT_TEXT_START>0x2000
            or FIELD_END-FIELD_START>0x200):
        raise ValueError("Source range incorrectly bounded")

    # The FieldManager writer's real source target at 0x80290E4C is known
    # independently; refuse a different revision/code path.
    if get_word(FIELD_END)!=0x7FFDFB78:
        raise ValueError("Known FieldManager r31->r29 assignment not present")
    r31_candidates=[]
    for pc in range(FIELD_START,FIELD_END,4):
        cand=r31_assignment_candidate(get_word(pc),pc)
        if cand:
            r31_candidates.append(cand)
    field_contexts=[
        {"candidate":c,
         "code":_around(get_word,int(c["pc"],16),FIELD_START,FIELD_END)}
        for c in r31_candidates[-8:]
    ]

    r31_from_r3_source_seen=(get_word(R31_FROM_R3_PC)==R31_FROM_R3_WORD)
    r31_changed_after_source=any(
        int(x["pc"],16)>R31_FROM_R3_PC for x in r31_candidates)
    r29_chain_source_seen=(
        r31_from_r3_source_seen
        and get_word(R29_FROM_R31_PC)==R29_FROM_R31_WORD
        and get_word(LOOP_LOAD_CHILD_PC)==LOOP_LOAD_CHILD_WORD
        and get_word(LOOP_ADVANCE_PC)==LOOP_ADVANCE_WORD
        and _method_shaped_prologue(get_word(FIELD_METHOD_SHAPED_PROLOGUE))
    )
    # The scanner only knows select dest opcode families, not full CFG. This
    # proves an exact static idiom and no RECOGNIZED intervening r31 writes.
    field_static_chain=(r29_chain_source_seen and not r31_changed_after_source)

    hits=[]
    for pc in range(EFFECT_TEXT_START,EFFECT_TEXT_END,4):
        hit=dform.decode_dform(get_word(pc),pc,targets=TARGETS)
        if hit is None:
            continue
        hits.append({
            "pc":hit["instruction_address_hex"],
            "offset":hit["relative_displacement_hex"],
            "mnemonic":hit["mnemonic"],
            "access":hit["access_kind"],
            "base_register":hit["base_reg"],
            "value_register":hit["source_or_destination_reg"],
            "receiver_verified_as_RPSysEffect_this":False,
        })
        hits[-1]["opcode_compatible_with_direct_HandleBase_word"] = (
            _compatible_with_handle_word(hits[-1]))
        hits[-1]["float_store_incompatible_with_direct_pointer_write"] = (
            hits[-1]["access"] == "write"
            and hits[-1]["mnemonic"] in ("stfs","stfsu")
            and hits[-1]["offset"] == "+0x07C")
        if len(hits)>MAX_SOURCE_HITS:
            raise ValueError("Unexpected effect-source offset hit count")
    # Put adjacent paired stores first, then reads. Still source-only.
    ordered=sorted(hits,key=lambda x:(
        0 if x["access"]=="write" else 1,
        int(x["pc"],16)))
    contexts=[
        {"candidate":hit,
         "code":_around(get_word,int(hit["pc"],16),
                        EFFECT_TEXT_START,EFFECT_TEXT_END)}
        for hit in ordered[:MAX_CONTEXTS]
    ]
    return {
        "kind":"S002-Rev1-effect-handle-source-PPC-r31-audit",
        "game":"RSPE01 Rev1",
        "source_header_RPSysEffect_mHandle_field_verified":True,
        "source_header_HandleBase_members_verified":True,
        "expected_effect_handle_members":[
            {"offset":"+0x078","type":"u32","member":"mHandle.mObjectID"},
            {"offset":"+0x07C","type":"LinkedObject*",
             "member":"mHandle.mObject"}
        ],
        "field_manager_r31_to_r29_pc":"0x80290E4C",
        "field_manager_r31_candidate_defs":r31_candidates,
        "field_manager_r31_candidate_contexts":field_contexts,
        "field_manager_r31_from_incoming_r3_source_pattern_verified":
            field_static_chain,
        "field_manager_r31_source_pattern_pc":f"0x{R31_FROM_R3_PC:08X}",
        "field_manager_r31_no_recognized_intervening_redefinition":
            r31_from_r3_source_seen and not r31_changed_after_source,
        "field_manager_r31_to_r29_child_pointer_cursor_static_verified":
            field_static_chain,
        "field_manager_method_boundary_cfg_verified":False,
        "field_manager_r31_origin_proven":False,
        "field_manager_r31_def_scanner_exhaustive":False,
        "RPSysEffectBase_text_range":[
            f"0x{EFFECT_TEXT_START:08X}",f"0x{EFFECT_TEXT_END:08X}"],
        "RPSysEffectBase_literal_handle_hits":hits,
        "RPSysEffectBase_write_count":sum(
            x["access"]=="write" for x in hits),
        "RPSysEffectBase_read_count":sum(
            x["access"]=="read" for x in hits),
        "RPSysEffectBase_opcode_compatible_handle_store_candidates":sum(
            x["access"]=="write"
            and x["opcode_compatible_with_direct_HandleBase_word"]
            for x in hits),
        "RPSysEffectBase_float_store_offset_07c_collision_count":sum(
            x["float_store_incompatible_with_direct_pointer_write"]
            for x in hits),
        "RPSysEffectBase_literal_offset_search_exhausts_handle_mutations":False,
        "RPSysEffectBase_contexts":contexts,
        "RPSysEffect_base_receiver_proven":False,
        "actual_four_minimap_effect_object_identity_verified":False,
        "source_header_predicts_ID_pointer_pair_at_078_07C":True,
        "saved_successful_shot_not_reloaded_by_this_code_scanner":True,
        "observed_four_pairs_runtime_handle_identity_verified":False,
        "RPSysEffect_size_or_allocator_stride_verified":False,
        "ball_motion_verified":False,
        "training_allowed":False,
        "allowed_to_publish":False,
    }


def run_local(folder:Path):
    old=dform.run_local(folder)
    if old.get("source_selected_record_snapshot_gated") is not True:
        raise ValueError("Prior source gate false")
    root=selected.DATA_ROOT.resolve(strict=True)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing original private study")
    folder=folder.resolve(strict=True)
    if folder==root or not folder.is_relative_to(root):
        raise ValueError("Outside private B0 source root")
    manifest=four._validate_manifest(folder)
    paths={k:four._approved_bank(
        folder,f"B0-{k}.bin",roster.MEM1_SIZE if k=="MEM1"
        else roster.MEM2_SIZE) for k in ("MEM1","MEM2")}
    if any(four._hash(p)!=manifest["B0"]["sha256"][k]
           for k,p in paths.items()):
        raise ValueError("Immutable code bank hash mismatch")
    with ExitStack() as stack:
        mmaps=[]
        for p in paths.values():
            f=stack.enter_context(p.open("rb"))
            mmaps.append(stack.enter_context(
                mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)))
        return analyze(roster.TwoBankReader(*mmaps).u32)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run_local(args.private_root),indent=2,sort_keys=True))
    except (OSError,ValueError,TypeError,KeyError,OverflowError) as exc:
        print("S002 typed effect handle source audit FAILED CLOSED: "+
              type(exc).__name__,file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
