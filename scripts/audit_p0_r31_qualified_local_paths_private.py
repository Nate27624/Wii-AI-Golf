"""Offline bounded branch+GPR31-path refinement for original Rev1 Player store.

Grounded ONLY in #219 exact SHA-gated original private B0, #244 exact
mr r31,r3 / stfs f0,+0x90(r31) and new per-instruction PPC classifier.
Three-state path exploration, with strict and EABI-callee scenarios.
Not full CFG, not real typed pointer, not physical/shot/training evidence.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys
import audit_p0_r31_opcode_classes_private as op
import audit_p0_r31_local_cfg_private as src
import audit_ball_xyz_source_callers_private as upstream

COPY=src.COPY
STORE=src.STORE
START=src.UNIT_START
COUNT=(STORE-COPY)//4+1
ALLOWED={"intact","unknown","clobber_candidate"}


def _pc(pc:int)->str:
    return "+0x%04X"%(pc-START)


def run_paths(words:dict[int,int],assume_compliant_nonvolatile_call:bool)->dict:
    """Possible LOCAL paths from immediately AFTER source mr, not all callers.

    The strict model allows calls to taint r31; the EABI model presumes each
    called function obeys preservation of callee-saved r31.
    """
    stack=[(COPY+4,"intact")]
    visited=set()
    stores=set()
    reason=set()
    edges=set()
    while stack:
        pc,reg=stack.pop()
        if (pc,reg) in visited:
            continue
        visited.add((pc,reg))
        if len(visited)>128:
            raise ValueError("state budget exceeded")
        if pc==STORE:
            stores.add(reg)
            continue
        if pc<COPY or pc>STORE or pc not in words:
            reason.add("local_path_exits_window")
            continue
        word=words[pc]
        flow=src._branch(pc,word)
        if flow is not None:
            kind,target=flow
            edges.add((_pc(pc),kind,_pc(target) if target in words else None))
            if kind in ("indirect_or_return","system_call"):
                reason.add("indirect_or_system_flow_unresolved")
                continue
            if kind in ("linked_call","linked_conditional_call"):
                reason.add("called_function_effect_not_verified")
                on_call=reg if assume_compliant_nonvolatile_call else "unknown"
                stack.append((pc+4,on_call))
                if kind=="linked_conditional_call":
                    stack.append((pc+4,reg))
            elif kind=="conditional_branch":
                stack.append((pc+4,reg))
                stack.append((target,reg))
            elif kind=="unconditional_branch":
                stack.append((target,reg))
            else:
                reason.add("unknown_branch_kind")
            continue
        effect=op.classify_gpr31(word)
        if effect["r31_direct_instruction_write_confirmed"]:
            reg="clobber_candidate"
            reason.add("direct_r31_write_on_some_local_path")
        elif effect["r31_gpr_write_possible_unknown"]:
            reg="unknown"
            reason.add("unrecognized_possible_r31_effect")
        if reg not in ALLOWED:
            raise ValueError("invalid source path state")
        stack.append((pc+4,reg))
    return {
        "store_path_exists":bool(stores),
        "store_path_with_copy_still_intact_possible":"intact" in stores,
        "store_path_with_unknown_r31_possible":"unknown" in stores,
        "store_path_with_postcopy_r31_write_possible":"clobber_candidate" in stores,
        "conditional_and_link_branch_edges":[
            {"source_site":x,"kind":y,"local_target_or_none":z}
            for x,y,z in sorted(edges)
        ],
        "incomplete_reasons":sorted(reason),
        "all_reachable_store_states":sorted(stores),
        "full_function_or_external_entry_cfg_verified":False,
        "selected_player_receiver_identity_verified":False,
        "dynamic_store_execution_verified":False,
    }


def analyze(data:bytes)->dict:
    if type(data) is not bytes or len(data)!=COUNT*4:
        raise ValueError("unexpected bounded PPC source window")
    src.analyze_window(data)
    op.analyze_window(data)
    words={COPY+i*4:struct.unpack_from(">I",data,i*4)[0] for i in range(COUNT)}
    classification=[{
        "source_site":_pc(pc),
        "opcode_family":op.classify_gpr31(word)["opcode_family"],
        "direct_r31_write":op.classify_gpr31(word)["r31_direct_instruction_write_confirmed"],
        "unknown_r31_effect":op.classify_gpr31(word)["r31_gpr_write_possible_unknown"],
    } for pc,word in sorted(words.items()) if pc!=STORE]
    strict=run_paths(words,False)
    compliant=run_paths(words,True)
    return {
        "kind":"S002-P0-PLAYER-R31-QUALIFIED-LOCAL-PATHS",
        "source_game":"RSPE01","disc_revision":1,
        "source_unit":"RPGolPlayer",
        "copy_source_site":"+0x1BE8",
        "store_source_site":"+0x1C18",
        "source_exact_copy_store_verified":True,
        "source_intervening_instruction_count":COUNT-2,
        "known_source_instruction_classes":classification,
        "no_callee_preservation_assumed":strict,
        "all_linked_calls_assumed_EABI_r31_preserved":compliant,
        "EABI_callee_assumption_verified_by_this_source_study":False,
        "all_external_predecessors_to_store_excluded":False,
        "complete_function_entry_and_prologue_verified":False,
        "runtime_r3_is_selected_player_record_verified":False,
        "runtime_r31_store_executes_during_wedge_verified":False,
        "physical_ball_xyz_velocity_power_contact_verified":False,
        "approved_for_training":False,
        "allowed_to_publish":False,
    }


def audit(session:Path,data_root:Path)->dict:
    # Reuses all original #219 byte/golf/header/SHA and #244 source gates.
    op.audit(session,data_root)
    try:
        bank=upstream.checked_private_b0(session,data_root)
    except upstream.UntrustedInput:
        raise ValueError("Untrusted B0 source") from None
    with bank.open("rb") as fp:
        fp.seek(COPY-upstream.MEM1_START)
        raw=fp.read(COUNT*4)
    if len(raw)!=COUNT*4:
        raise ValueError("Original source window truncated")
    try:
        upstream.checked_private_b0(session,data_root)
    except upstream.UntrustedInput:
        raise ValueError("Original B0 changed") from None
    out=analyze(raw)
    out["original_private_B0_SHA_verified_before_after"]=True
    return out


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    default=Path(__file__).resolve().parents[2]/"Wii-AI-Golf-Data"
    p.add_argument("--data-root",type=Path,default=default)
    p.add_argument("--private-session",type=Path)
    args=p.parse_args(argv)
    session=args.private_session or args.data_root/"ball-study-20261027-212633"
    try:
        out=audit(session,args.data_root)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,ImportError,AttributeError,struct.error):
        print("P0 qualified r31 local paths ABSTAIN: original B0 SHA, PPC source or bounded path validation failed. No private bytes or paths disclosed.",file=sys.stderr)
        return 2
    print(json.dumps(out,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
