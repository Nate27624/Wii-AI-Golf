"""One bounded exact Rev1 fn_8029A5EC callee source inventory.

This method is the target of three authenticated global-ball source-slot
reader/BL pairs from the existing S002 15-read audit. Public ogws RSPE01
Rev1 symbols.txt names fn_8029A5EC at 0x8029A5EC with size 0x138.
Only classify direct GPR3/GPR31 D-form field references, source direct BL
targets and entry r3 save candidates. Do NOT claim r31 aliases the
incoming pointer on any path or infer physics, renderer, or execution.
Pure callback, no guest RAM deref or native file access.
"""
from __future__ import annotations

ENTRY = 0x8029A5EC
SIZE = 0x138
END = ENTRY + SIZE
UNIT_BASE = 0x80296FD8
MAX_REPORT = 28
FIELD_OPS = {
    32: "lwz", 33: "lwzu", 34: "lbz", 35: "lbzu",
    36: "stw", 37: "stwu", 38: "stb", 39: "stbu",
    40: "lhz", 41: "lhzu", 42: "lha", 43: "lhau",
    44: "sth", 45: "sthu", 46: "lmw", 47: "stmw",
    48: "lfs", 49: "lfsu", 50: "lfd", 51: "lfdu",
    52: "stfs", 53: "stfsu", 54: "stfd", 55: "stfdu"
}

def _word(read,pc):
    w=read(pc)
    if type(w) is not int or not 0<=w<=0xffffffff:
        raise ValueError("unqualified source PPC")
    return w

def _loc(pc):
    return f"+0x{pc-UNIT_BASE:04X}"

def _mr(w):
    if w>>26 != 31 or (w>>1)&1023 != 444:
        return None
    src=(w>>21)&31
    dest=(w>>16)&31
    b=(w>>11)&31
    return (dest,src) if b==src else None

def _bl(pc,w):
    if w>>26 !=18 or not(w&1):
        return None
    offset=w&0x03fffffc
    if offset&0x02000000:offset-=0x04000000
    target=(offset if w&2 else pc+offset)&0xffffffff
    return target

def audit(read, source_calls, six_units):
    if type(source_calls) is not list or len(source_calls)!=3:
        raise ValueError("three qualified global pointer readers required")
    expected=("+0x2B70","+0x2BEC","+0x2C68")
    if (tuple(row.get("direct_bl_source_relative_pc") for row in source_calls)!=expected or
        any(row.get("direct_bl_public_target_code_pc")!="0x8029A5EC" for row in source_calls) or
        any(row.get("direct_source_global_pointer_is_runtime_r3_argument_verified") is not False for row in source_calls)):
        raise ValueError("three source caller identities differ")
    if (not isinstance(six_units,tuple) or len(six_units)!=6 or
        not any(name=="RPGolMapObjBall" and low<=ENTRY<END<=high
                for name,low,high in six_units)):
        raise ValueError("public source unit qualification missing")
    words={pc:_word(read,pc) for pc in range(ENTRY,END,4)}
    field=[]
    calls=[]
    saves=[]
    hazard_count=0
    for pc,w in words.items():
        op=w>>26
        rs=(w>>21)&31
        ra=(w>>16)&31
        immediate=w&65535
        signed=immediate-65536 if immediate&32768 else immediate
        mr=_mr(w)
        if pc<ENTRY+0x40 and mr is not None and mr[1]==3 and mr[0] in(28,29,30,31):
            saves.append({"source_relative_pc":_loc(pc),"copy_candidate_GPR":f"r{mr[0]}"})
        if op in(16,17,18,19):
            hazard_count+=1
        if op in FIELD_OPS and ra in(3,31):
            field.append({
                "source_relative_pc":_loc(pc),
                "GPR_address_base":f"r{ra}",
                "source_memory_opcode":FIELD_OPS[op],
                "source_field_signed_offset":signed,
                "receiver_alias_to_global_proven":False,
            })
        dest=_bl(pc,w)
        if dest is not None:
            if not 0x80000000<=dest<0x81800000 or dest%4:
                raise ValueError("source direct BL not valid code target")
            matching=[(name,lo) for name,lo,hi in six_units if lo<=dest<hi]
            if len(matching)>1:
                raise ValueError("overlapping public source units")
            calls.append({
                "source_relative_pc":_loc(pc),
                "public_target_code_pc":f"0x{dest:08X}",
                "target_source_unit":matching[0][0] if matching else "outside_six_Golf_units",
                "target_unit_relative_pc":f"+0x{dest-matching[0][1]:04X}" if matching else None,
                "called_function_role_verified":False,
            })
    return {
        "kind":"S002-ONE-COMMON-GLOBAL-POINTER-CALLEE-STATIC-BOUNDS",
        "source_function":"fn_8029A5EC",
        "public_function_source_unit":"RPGolMapObjBall",
        "public_function_size_bytes":SIZE,
        "source_words_scanned":SIZE//4,
        "three_verified_source_BL_sites_same_target":True,
        "early_input_r3_callee_saved_copy_candidates":saves[:MAX_REPORT],
        "source_direct_GPR3_GPR31_field_accesses":field[:MAX_REPORT],
        "source_direct_field_access_count":len(field),
        "source_direct_BL_targets":calls[:MAX_REPORT],
        "source_direct_BL_count":len(calls),
        "branch_or_call_instruction_count_in_function":hazard_count,
        "more_field_sites_unreported":max(0,len(field)-MAX_REPORT),
        "more_call_sites_unreported":max(0,len(calls)-MAX_REPORT),
        "any_GPR31_field_load_is_receiver_proven":False,
        "function_is_rendered_or_physics_method_verified":False,
        "whole_function_dataflow_controlflow_verified":False,
        "source_called_at_runtime_verified":False,
        "physical_xyz_velocity_power_impact_score_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }
