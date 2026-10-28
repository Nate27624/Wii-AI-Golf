"""Targeted source-only follow-up to exact verified fifteen global-slot reads.

The earlier audit located precisely three candidate r3 -> direct BL handoffs
and one source-global+0x4C field load. This module authenticates the source
PPC opcodes at those exact public code sites and reports only code-call
destinations and bounded first use of the +0x4C pointer. Neither call target
nor syntax proves execution, receiver identity, rendering or world coordinates.

Pure PPC callback module: NO native file I/O, no pointer-value reads, no ROM,
Dolphin, upload or training.
"""
from __future__ import annotations

UNIT_BASE = 0x80296FD8
UNIT_END = 0x8029B240
CALL_PAIRS = ((0x2B64,0x2B70), (0x2BE0,0x2BEC), (0x2C64,0x2C68))
TRANSLATION_PAIR = (0x2CF8,0x2CFC)
VECTOR_WINDOW = 8

def _word(read, pc):
    v=read(pc)
    if type(v) is not int or not 0 <= v <= 0xffffffff:
        raise ValueError("invalid source-only PPC word")
    return v

def _signed16(w):
    n=w&0xffff
    return n-0x10000 if n&0x8000 else n

def _loc(pc):
    return f"+0x{pc-UNIT_BASE:04X}"

def _bl_target(pc, w):
    if w>>26 != 18 or not (w&1):
        raise ValueError("expected exact direct PPC branch with link")
    off=w&0x03fffffc
    if off&0x02000000:
        off-=0x04000000
    dest=(off if w&2 else pc+off)&0xffffffff
    if dest%4 or not 0x80000000<=dest<0x81800000:
        raise ValueError("branch target not in qualified public code region")
    return dest

def _six_unit_target(dest, six_units):
    if not isinstance(six_units,(tuple,list)) or len(six_units)!=6:
        raise ValueError("six-unit source table not qualified")
    matching=[(name,lo,hi) for name,lo,hi in six_units if lo<=dest<hi]
    if len(matching)>1:
        raise ValueError("overlapping source code units")
    if matching:
        name,lo,_=matching[0]
        return (name, f"+0x{dest-lo:04X}")
    return ("outside_six_scanned_golf_units",None)

def _mr(w):
    if w>>26!=31 or (w>>1)&1023 != 444:
        return None
    src=(w>>21)&31
    dst=(w>>16)&31
    rb=(w>>11)&31
    return (dst,src) if rb==src else None

def _write_effect(w, tracked):
    """Safety-biased, deliberately incomplete PowerPC GPR effect classifier."""
    op=w>>26
    rt=(w>>21)&31
    ra=(w>>16)&31
    m=_mr(w)
    if m is not None:
        return m[0]==tracked
    if op in (12,13,14,15,32,33,34,35,40,41,42,43):
        return rt==tracked or (op in (33,35,41,43) and ra==tracked)
    if op==46:
        return rt<=tracked
    if op in (20,21,23,24,25,26,27,28,29):
        return ra==tracked
    if op in (37,39,45,49,51,53,55):
        return ra==tracked
    if op in (36,38,44,47,48,50,52,54,10,11,59,63):
        return False
    return True

def _first_event(read, rptr, firstpc):
    events=[]
    status="no_direct_vector_component_use_in_eight_words"
    stop=None
    for index in range(1,VECTOR_WINDOW+1):
        pc=firstpc+index*4
        if pc>=UNIT_END:
            status="source_unit_boundary"
            break
        w=_word(read,pc)
        op=w>>26
        base=(w>>16)&31
        rel=_signed16(w)
        if op in (16,17,18,19):
            status="branch_or_call_before_complete_direct_vector_use"
            stop=_loc(pc)
            break
        # lfs/stfs fN,N(rptr) are direct syntactic accesses. No
        # FPR numeric values or source vector component semantics implied.
        if op in (48,52) and base==rptr and rel in (0,4,8):
            entry={"access_kind":"lfs" if op==48 else "stfs",
                   "vector_offset":rel,"instruction_relative_pc":_loc(pc)}
            events.append(entry)
            continue
        if op in (32,34,40,42) and base==rptr:
            status="nested_gpr_load_before_complete_vector_use"
            stop=_loc(pc)
            break
        if op in (36,38,44) and base==rptr:
            status="nested_gpr_store_before_complete_vector_use"
            stop=_loc(pc)
            break
        if _write_effect(w,rptr):
            status="potential_translation_register_clobber"
            stop=_loc(pc)
            break
        # Unknown unhandled instructions are NOT proven to preserve
        # all GPR aliases or whole-function behavior.
    if events and status=="no_direct_vector_component_use_in_eight_words":
        status="direct_vector_float_access_syntax_observed"
    return {"first_syntactic_vector_use_class":status,
            "recognized_direct_f32_accesses":events[:8],
            "stop_source_unit_relative_pc":stop,
            "three_distinct_component_offsets_seen":
                set(e["vector_offset"] for e in events)=={0,4,8}}

def analyze(read, first_use_report, source_global_disp, six_units):
    if (type(first_use_report) is not dict or
        first_use_report.get("kind")!="S002-GLOBAL-SLOT-DIRECT-READ-FIRST-USE-HINTS" or
        first_use_report.get("exact_known_direct_loads_checked")!=15 or
        first_use_report.get("approved_for_model_training") is not False):
        raise ValueError("source-global fifteen-read qualification missing")
    entries=first_use_report.get("source_only_first_use_hints")
    if not isinstance(entries,list) or len(entries)!=15:
        raise ValueError("expected exactly 15 authenticated sites")
    bysite={}
    for e in entries:
        key=e.get("global_load_unit_relative_pc")
        if type(key) is not str or key in bysite:
            raise ValueError("duplicate or missing source-global load")
        bysite[key]=e
    outputs=[]
    for source_off, call_off in CALL_PAIRS:
        k=f"+0x{source_off:04X}"
        e=bysite.get(k)
        if (e is None or e.get("first_bounded_consumer_class")!="direct_bl_after_r3_pointer_candidate"
            or e.get("first_bounded_consumer_unit_relative_pc")!=f"+0x{call_off:04X}"
            or e.get("destination_GPR")!="r3"):
            raise ValueError("three original source call hints no longer match")
        source=UNIT_BASE+source_off
        load=_word(read,source)
        if (load>>26 !=32 or (load>>21)&31 !=3 or (load>>16)&31 !=13
            or _signed16(load)!=source_global_disp):
            raise ValueError("source-global load changed")
        callpc=UNIT_BASE+call_off
        dest=_bl_target(callpc,_word(read,callpc))
        unit,offset=_six_unit_target(dest,six_units)
        outputs.append({
            "global_pointer_load_source_relative_pc":k,
            "direct_bl_source_relative_pc":f"+0x{call_off:04X}",
            "direct_bl_public_target_code_pc":f"0x{dest:08X}",
            "target_scanned_golf_unit_or_external":unit,
            "target_scanned_unit_relative_pc":offset,
            "direct_source_global_pointer_is_runtime_r3_argument_verified":False
        })
    a,b=TRANSLATION_PAIR
    e=bysite.get(f"+0x{a:04X}")
    if (e is None or e.get("first_bounded_consumer_class")!="field_load_from_source_global_pointer"
        or e.get("source_syntactic_field_displacement")!=0x4C
        or e.get("first_bounded_consumer_unit_relative_pc")!=f"+0x{b:04X}"
        or e.get("destination_GPR")!="r3"):
        raise ValueError("typed translation first-use candidate changed")
    w=_word(read,UNIT_BASE+a)
    if (w>>26, (w>>21)&31, (w>>16)&31, _signed16(w))!=(32,3,13,source_global_disp):
        raise ValueError("translation source-global load changed")
    second=_word(read,UNIT_BASE+b)
    if (second>>26,(second>>16)&31,_signed16(second))!=(32,3,0x4c):
        raise ValueError("not an exact lwz global ball +0x4C")
    rptr=(second>>21)&31
    trans=_first_event(read,rptr,UNIT_BASE+b)
    return {
        "kind":"S002-GLOBAL-POINTER-THREE-BL-AND-TRANSLATION-USE",
        "source_qualified_global_direct_reads":15,
        "exact_three_candidate_direct_calls":outputs,
        "source_global_translation_field_read":{
            "load_relative_pc":f"+0x{a:04X}",
            "translation_pointer_load_relative_pc":f"+0x{b:04X}",
            "pointer_destination_GPR":f"r{rptr}",
            "source_member_offset":0x4c,
            **trans,
        },
        "bounded_source_syntax_only":True,
        "whole_function_control_flow_verified":False,
        "dynamic_receiver_or_renderer_identity_verified":False,
        "physical_xyz_velocity_power_impact_score_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }
