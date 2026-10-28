"""Exact post-return CANDIDATE path study for the sole global pointer stw.

No RAM/Dolphin I/O. Given existing source-verified PPC read_u32, prove:
- preceding instruction is the plain PPC blr return (not merely any op19)
- following code is a *hypothetical* new entry, NOT an entry symbol proven;
- initial addi r3,0,positive supplies a literal argument to a first BL;
- conditional branch at known location skips an optional second BL;
- distinguish the possible call-return contributions to stw r3.
The 832 public .text units/symbol mappings are owned by PR #219. We report
public *code instruction* call target PC only, never private heap pointers.
"""
from __future__ import annotations

import review_p0_global_slot_store_cfg as earlier

UNIT_BASE=0x80296FD8
RETURN_PC=0x8029A034
POST_ENTRY=RETURN_PC+4
ADDI_PC=0x8029A040
FIRST_BL=0x8029A048
BRANCH_PC=0x8029A050
SECOND_BL=0x8029A058
STORE_PC=0x8029A05C


def location(pc):
    return "+0x%04X"%(pc-UNIT_BASE)


def plain_blr(word):
    # PowerPC bclr BO=20, BI=0, LK=0 (standard blr encoding).
    return (
        type(word) is int
        and word>>26==19
        and ((word>>1)&1023)==16
        and ((word>>21)&31)==20
        and ((word>>16)&31)==0
        and (word&1)==0
    )


def _decode_expected(read,disp):
    if not plain_blr(read(RETURN_PC)):
        raise ValueError("preceding source return is not exact plain blr")
    d=earlier._d(read(ADDI_PC))
    if d[:3]!=(14,3,0) or d[3]<=0:
        raise ValueError("first call's expected positive literal argument missing")
    st=earlier._d(read(STORE_PC))
    if st!=(36,3,13,disp):
        raise ValueError("global pointer slot stw source changed")
    first=earlier._branch(FIRST_BL,read(FIRST_BL))
    second=earlier._branch(SECOND_BL,read(SECOND_BL))
    split=earlier._branch(BRANCH_PC,read(BRANCH_PC))
    if (first is None or first["kind"]!="bl"
            or second is None or second["kind"]!="bl"
            or split is None or split["kind"]!="bc"
            or split["target"]!=STORE_PC):
        raise ValueError("exact two calls and conditional store branch not matched")
    for call in (first,second):
        dst=call["target"]
        if not isinstance(dst,int) or dst%4 or not 0x80000000<=dst<0x81800000:
            raise ValueError("direct call source target outside native .text range")
    return d,first,second,split


def analyze(read,source_global_displacement):
    if (type(source_global_displacement) is not int or
            not -32768<=source_global_displacement<=32767):
        raise ValueError("invalid singleton source offset")
    literal,first,second,split=_decode_expected(read,source_global_displacement)
    # Local bounded CFG starts AFTER independently matched blr. This is
    # explicitly hypothetical source entry; an external predecessor to any
    # instruction is possible. We cannot prove full function boundaries.
    pending=[(POST_ENTRY,"unknown_on_hypothetical_entry")]
    visited=set()
    at_store=set()
    exit_or_unknown=False
    unsupported_write=False
    while pending:
        pc,state=pending.pop()
        if pc==STORE_PC:
            at_store.add(state)
            continue
        if not POST_ENTRY<=pc<STORE_PC or pc%4:
            exit_or_unknown=True
            continue
        key=(pc,state)
        if key in visited:
            continue
        if len(visited)>256:
            raise ValueError("bounded local source CFG exhausted")
        visited.add(key)
        word=read(pc)
        if pc in (FIRST_BL,SECOND_BL):
            event=earlier._branch(pc,word)
            if event is None or event["kind"]!="bl":
                raise ValueError("reviewed source BL changed")
            state=("return_from_first_bl" if pc==FIRST_BL
                   else "return_from_second_bl")
            pending.append((pc+4,state))
            continue
        branch=earlier._branch(pc,word)
        if branch is not None:
            if branch["kind"]=="b":
                pending.append((branch["target"],state))
            elif branch["kind"]=="bc":
                pending.append((branch["target"],state))
                pending.append((pc+4,state))
            else:
                exit_or_unknown=True
            continue
        wrote=earlier._r3_written(word)
        if wrote is not None:
            if pc==ADDI_PC and wrote=="addi_literal_nonzero":
                state="positive_literal_argument"
            elif wrote=="mr_r3_from_r3":
                pass
            else:
                state="other_or_unrecognized_r3_assignment"
                unsupported_write=True
        pending.append((pc+4,state))
    # Endpoint source classes only; external entry paths not examined.
    sources=sorted(at_store)
    return {
        "source_unit":"RPGolMapObjBall",
        "preceding_source_pc":location(RETURN_PC),
        "preceding_instruction_is_exact_plain_blr":True,
        "hypothetical_post_return_entry_pc":location(POST_ENTRY),
        "post_return_entry_symbol_verified":False,
        "first_bl_source_pc":location(FIRST_BL),
        "first_bl_target_public_code_pc":"0x%08X"%first["target"],
        "first_bl_argument_r3_positive_literal_candidate":True,
        "second_bl_source_pc":location(SECOND_BL),
        "second_bl_target_public_code_pc":"0x%08X"%second["target"],
        "conditional_branch_source_pc":location(BRANCH_PC),
        "conditional_branch_targets_store":True,
        "conditional_branch_may_skip_second_bl":True,
        "hypothetical_entry_can_reach_store":bool(at_store),
        "store_r3_candidate_sources_from_this_entry":sources,
        "path_with_r3_from_first_bl_possible":"return_from_first_bl" in at_store,
        "path_with_r3_from_second_bl_possible":"return_from_second_bl" in at_store,
        "local_unrecognized_r3_write_possible":unsupported_write,
        "local_control_flow_escape_possible":exit_or_unknown,
        "external_predecessors_to_store_unexamined":True,
        "callee_identities_verified_by_public_symbol_index":False,
        "calls_confirmed_allocator_or_constructor":False,
        "runtime_store_value_verified":False,
        "function_init_or_cleanup_semantics_verified":False,
        "store_executed_during_human_shot_verified":False,
        "source_global_is_rendered_ball_verified":False,
        "physical_ball_xyz_verified":False,
        "training_approved":False,
    }
