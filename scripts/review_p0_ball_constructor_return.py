"""Golf Ball constructor-source audit for global object's second direct call.

Pure source-only PPC decoder. Rev1 function fn_8029AB78 is a constructor
candidate linked by the earlier #162 source study and reused by the
SimulateManager four inline ball-like objects. Source-authenticate:
  * direct BL inside constructor to RPGolMapObjBase fn_80290A48
  * early input r3 -> saved receiver register candidates
  * source register reconstruction just before literal PPC blr exits
  * known class-table/data store at +0x2C, bounded syntactic classification

No full-flow proof or dynamic global pointer identity. No native RAM
acquisition, Dolphin, new capture, raw PPC words, private pointer values,
source bank hashes or data upload.
"""
from __future__ import annotations

BALL_CTOR_ENTRY=0x8029AB78
BALL_CTOR_END=0x8029AD94
BASE_CTOR_CALL=0x8029AB90
BASE_CTOR_TARGET=0x80290A48
CLASS_TAG_PC=0x8029ABA4
UNIT_BASE=0x80296FD8
SCAN_LIMIT=0x21C//4


def _loc(pc):
    return f"+0x{pc-UNIT_BASE:04X}"


def _mr(word:int)->tuple[int,int]|None:
    if word>>26!=31 or (word>>1)&1023!=444:
        return None
    rs=(word>>21)&31
    ra=(word>>16)&31
    rb=(word>>11)&31
    return (ra,rs) if rb==rs else None


def _direct_branch(pc,word):
    if word>>26!=18:
        return None
    off=word&0x03fffffc
    if off&0x02000000: off-=0x04000000
    dst=off if word&2 else pc+off
    return {"destination":dst&0xffffffff,"with_link":bool(word&1)}


def _r3_assignment_class(word):
    op=word>>26
    m=_mr(word)
    if m is not None and m[0]==3:
        return "mr_from_r%d"%m[1]
    rt=(word>>21)&31
    ra=(word>>16)&31
    if op in (14,15,32,33,34,35,40,41,42,43) and rt==3:
        return "addi" if op==14 else "load_or_other_integer_writer"
    if op in (20,21,23,24,25,26,27,28,29) and ra==3:
        return "rotate_or_logical_writer"
    if op==46 and rt<=3:
        return "lmw_writer"
    if op==31 and (rt==3 or ra==3):
        return "unclassified_Xform_r3_effect"
    return None


def analyze(read) -> dict:
    if BALL_CTOR_END-BALL_CTOR_ENTRY != 0x21C or (BALL_CTOR_END-BALL_CTOR_ENTRY)//4!=SCAN_LIMIT:
        raise ValueError("public symbol function extent invalid")
    words={pc:read(pc) for pc in range(BALL_CTOR_ENTRY,BALL_CTOR_END,4)}
    if any(type(v) is not int or v<0 or v>0xffffffff for v in words.values()):
        raise ValueError("invalid source PPC")
    bl=_direct_branch(BASE_CTOR_CALL,words[BASE_CTOR_CALL])
    if bl!={"destination":BASE_CTOR_TARGET,"with_link":True}:
        raise ValueError("known Rev1 base-class constructor call not source confirmed")
    saves=[]
    for pc in range(BALL_CTOR_ENTRY,BASE_CTOR_CALL,4):
        m=_mr(words[pc])
        if m is not None and m[1]==3 and m[0] in (28,29,30,31):
            saves.append((pc,m[0]))
    blr=[pc for pc,w in words.items() if w==0x4e800020]
    candidate=[]
    for ret in blr:
        near=[]
        for pc in range(max(BALL_CTOR_ENTRY,ret-0x24),ret,4):
            cl=_r3_assignment_class(words[pc])
            if cl is not None: near.append((pc,cl))
        last=near[-1] if near else None
        saved_regs={reg for _pc,reg in saves}
        matching=(bool(last) and last[1].startswith("mr_from_r")
                  and int(last[1].removeprefix("mr_from_r")) in saved_regs)
        candidate.append({
            "return_instruction_unit_relative_pc":_loc(ret),
            "nearest_supported_r3_definition_class":last[1] if last else "unknown",
            "nearest_supported_r3_definition_unit_relative_pc":_loc(last[0]) if last else None,
            "r3_mr_from_entry_saved_register_syntactically_possible":matching,
            "complete_r3_reaching_definition_at_exit_verified":False,
        })
    tag=words[CLASS_TAG_PC]
    class_op=tag>>26
    return {
        "source_unit":"RPGolMapObjBall",
        "public_symbol":"fn_8029AB78",
        "public_symbol_size":0x21C,
        "public_function_entry_source_verified":True,
        "base_class_constructor_direct_call_verified":True,
        "base_constructor_public_symbol":"fn_80290A48",
        "base_constructor_call_relative_pc":_loc(BASE_CTOR_CALL),
        "entry_receiver_saved_register_candidate_count":len(saves),
        "entry_receiver_saved_register_classes":[f"r{x[1]}" for x in saves],
        "public_constructor_return_count_within_symbol":len(blr),
        "bounded_exit_r3_syntactic_relationships":candidate[:16],
        "more_return_sites_not_reported":max(0,len(candidate)-16),
        "class_table_initialization_instruction_op_category":
          ("integer_store" if class_op in (36,37,38,39,44,45,46,47)
           else "other_or_unknown"),
        "class_data_word_semantics_unverified":True,
        "all_return_values_must_equal_ctor_receiver_verified":False,
        "constructor_returns_allocated_object_on_nonnull_branch_verified":False,
        "global_slot_runtime_stores_ctor_return_verified":False,
        "live_ball_physical_xyz_verified":False,
        "actual_executed_shot_or_frame_verified":False,
        "training_approved":False,
    }
