"""Narrow PPC source register-safety audit for Golf ball ctor's return.

Only scans fn_8029AB78 (published Rev1 function 0x21C bytes), with known
source-backed entry r3→r31 save and r3←r31 before exact blr. Classifies
possible r31 writes between save and return-copy, possible r3 writes in
return suffix, and direct PPC branches that can bypass return-copy.

All evidence is source-relative and categorical. Unsupported PPC forms,
external control flow, stack restoration and callee ABI are not modeled
as a proved must-definition. Never assumes live gameplay execution,
rendered ball coordinates, global pointer identity or training approval.
No native RAM reader, Dolphin or file I/O in this helper.
"""
from __future__ import annotations

ENTRY=0x8029AB78
BASE_CALL=0x8029AB90
FINAL_COPY=0x8029AD7C
RETURN=0x8029AD90
END=0x8029AD94
UNIT_BASE=0x80296FD8

def _loc(pc:int)->str:
    return f"+0x{pc-UNIT_BASE:04X}"

def _mr(word:int):
    if word>>26!=31 or ((word>>1)&1023)!=444:
        return None
    rs=(word>>21)&31
    ra=(word>>16)&31
    rb=(word>>11)&31
    return (ra,rs) if rs==rb else None

def _branch(pc,word):
    op=word>>26
    if op==18:
        off=word&0x03fffffc
        if off&0x02000000: off-=0x04000000
        return ((off if word&2 else pc+off)&0xffffffff, "call" if word&1 else "b")
    if op==16:
        off=word&0xfffc
        if off&0x8000: off-=0x10000
        return ((off if word&2 else pc+off)&0xffffffff,"conditional")
    if op==19 and ((word>>1)&1023) in (16,528):
        return (None,"indirect")
    return None

def _gpr_write_kind(word:int,reg:int)->str|None:
    """Conservative r31 or r3 GPR write risk, not complete PPC semantics."""
    op=word>>26
    rt=(word>>21)&31
    ra=(word>>16)&31
    m=_mr(word)
    if m and m[0]==reg:
        return "copy_from_r"+str(m[1])
    if op in (12,13,14,15,32,33,34,35,40,41,42,43) and rt==reg:
        return "direct_integer_destination"
    if op==46 and rt<=reg:
        return "lmw_includes_register"
    if op in (20,21,23,24,25,26,27,28,29) and ra==reg:
        return "rotate_or_logical_dest_rA"
    if op in (33,35,37,39,41,43,45,49,51,53,55) and ra==reg:
        return "update_base_rA"
    # Some X-form opcodes write rA, others rT; this decoder refuses to
    # dismiss either possible write without a full opcode-specific proof.
    if op==31 and (rt==reg or ra==reg):
        return "unresolved_X_form_register_effect"
    if op in (4,30) and (rt==reg or ra==reg):
        return "unresolved_opcode_register_effect"
    return None

def audit(read)->dict:
    if (END-ENTRY)!=0x21C or FINAL_COPY>=RETURN or RETURN+4!=END:
        raise ValueError("published Rev1 ctor function boundaries invalid")
    words={pc:read(pc) for pc in range(ENTRY,END,4)}
    if any(type(w) is not int or w<0 or w>0xffffffff for w in words.values()):
        raise ValueError("not a valid Rev1 PPC code word")
    saves=[pc for pc in range(ENTRY,BASE_CALL,4) if _mr(words[pc])==(31,3)]
    if len(saves)!=1:
        raise ValueError("exact one constructor incoming receiver save expected")
    if _mr(words[FINAL_COPY])!=(3,31):
        raise ValueError("exact source return copy r3,r31 missing")
    if words[RETURN]!=0x4e800020:
        raise ValueError("source return not exact blr")
    save=saves[0]
    preceding=[]
    for pc in range(save+4,FINAL_COPY,4):
        kind=_gpr_write_kind(words[pc],31)
        if kind:
            preceding.append({"source_relative_pc":_loc(pc),"write_risk_class":kind})
    suffix=[]
    for pc in range(FINAL_COPY+4,RETURN,4):
        kind=_gpr_write_kind(words[pc],3)
        if kind:
            suffix.append({"source_relative_pc":_loc(pc),"write_risk_class":kind})
    branches=[]
    bypass=[]
    outside=[]
    indirect=[]
    for pc in range(ENTRY,FINAL_COPY,4):
        branch=_branch(pc,words[pc])
        if branch is None:
            continue
        target,kind=branch
        if kind=="call":
            # ABI nonvolatile r31 is preserved by well-formed callees,
            # but source-only analysis does not verify every callee.
            continue
        if kind=="indirect":
            indirect.append(_loc(pc))
        elif target is not None and FINAL_COPY<target<=RETURN:
            bypass.append(_loc(pc))
            branches.append({"source_relative_pc":_loc(pc),
                             "target_relative_pc":_loc(target),
                             "hazard":"direct_jump_bypasses_final_return_copy"})
        elif target is not None and not ENTRY<=target<END:
            outside.append(_loc(pc))
    return {
        "kind":"S002-SOURCE-BALL-CTOR-REGISTER-RETURN-RISK",
        "source_function":"fn_8029AB78",
        "source_entry_receiver_save_relative_pc":_loc(save),
        "entry_saved_receiver_is_r31":True,
        "final_copy_r3_from_r31_relative_pc":_loc(FINAL_COPY),
        "final_plain_blr_relative_pc":_loc(RETURN),
        "recognized_r31_writes_after_save_before_copy":preceding[:25],
        "recognized_r31_write_count":len(preceding),
        "unreported_r31_writes":max(0,len(preceding)-25),
        "recognized_r3_writes_after_copy_before_blr":suffix[:25],
        "recognized_r3_suffix_write_count":len(suffix),
        "direct_branch_bypasses_copy":bool(bypass),
        "direct_bypass_branch_sites":branches[:25],
        "unreported_bypass_branches":max(0,len(branches)-25),
        "external_branch_sites":outside[:25],
        "indirect_branch_sites":indirect[:25],
        "source_no_detected_r31_or_r3_clobber_or_direct_bypass":(
            not preceding and not suffix and not bypass
        ),
        "full_source_register_write_classifier_verified":False,
        "all_callee_nonvolatile_r31_preservation_verified":False,
        "whole_function_receiver_to_return_must_def_verified":False,
        "actual_global_pointer_runtime_identity_verified":False,
        "actual_inflight_execution_verified":False,
        "physical_world_xyz_velocity_contact_power_score_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }
