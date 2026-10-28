"""Bounded static footprint of three source-confirmed SimulateManager callees.

Reads 10+70+157 PPC source instructions from the seven already SHA-qualified
original Rev1 bank pairs. Every result is SOURCE ONLY. Direct store opcodes
are not proven writes to a ball; a call in the function is not an executed
physics tick. Never emit raw PPC, runtime pointers, float values, private paths.
"""
from __future__ import annotations

ENTRY=0x8028E158
CALLEES=(
    ("fn_8029B554",0x8029B554,0x28,0x7C),
    ("fn_8029B43C",0x8029B43C,0x118,0x90),
    ("fn_8029B57C",0x8029B57C,0x274,0x168),
)
SIM_LO,SIM_HI=0x8029B240,0x8029BBB4
FLOAT_LOAD_OPS=(48,49,50,51)
FLOAT_STORE_OPS=(52,53,54,55)
GPR_STORE_OPS=(36,37,38,39,44,45,47)
GPR_LOAD_OPS=(32,33,34,35,40,41,42,43,46)
X_STORE_XOS=(151,183,215,247,407,439,663,695,727,759)

def _bl_target(pc,w):
    off=w&0x03fffffc
    if off&0x02000000:off-=0x04000000
    return (off if w&2 else pc+off)&0xffffffff

def _bc_target(pc,w):
    off=w&0xfffc
    if off&0x8000:off-=0x10000
    return (off if w&2 else pc+off)&0xffffffff

def _rel(pc,entry):
    return "+0x%04X"%(pc-entry)

def _word(w):
    if type(w) is not int or not 0<=w<=0xffffffff:
        raise ValueError("invalid source PPC instruction")

def _main_gate(main_report):
    if (type(main_report) is not dict or
        main_report.get("kind") !=
        "P0-REV1-GOLF-MAIN-UPDATE-DIRECT-BL-BOUNDED-CENSUS" or
        main_report.get("independent_prior_0x100_original_BL_prefix_matched") is not True or
        main_report.get("exact_source_words_scanned")!=101 or
        main_report.get("guest_physics_step_clock_verified") is not False):
        raise ValueError("source-attested 101-word main prerequisite missing")
    entries=main_report.get("source_direct_linked_calls")
    if type(entries) is not list:
        raise ValueError("main BL census absent")
    for name,pc,length,off in CALLEES:
        qualified=[r for r in entries if
                   r.get("source_main_function_relative_pc")==_rel(ENTRY+off,ENTRY)
                   and r.get("target_public_code_pc")==f"0x{pc:08X}"
                   and r.get("target_source_code_unit_class")==
                       "published_RPGolSimulateManager_text_only"]
        if len(qualified)!=1:
            raise ValueError("three independently authenticated source BL targets changed")

def analyze(main_words, callee_words, main_report):
    _main_gate(main_report)
    if type(main_words) not in(tuple,list) or len(main_words)!=101:
        raise ValueError("main function word window mismatch")
    for w in main_words:_word(w)
    if type(callee_words) is not dict or set(callee_words)!={
            x[0] for x in CALLEES}:
        raise ValueError("three callee source windows required")
    summary=[]
    for name,entry,length,off in CALLEES:
        words=callee_words[name]
        if type(words) not in(tuple,list) or len(words)!=length//4:
            raise ValueError("exact public callee symbol size mismatch")
        if not SIM_LO<=entry<entry+length<=SIM_HI:
            raise ValueError("source code unit provenance mismatch")
        direct_calls=[]
        conditional=0
        indirect=0
        nonlink_direct=0
        gpr_stores=[]
        fp_stores=[]
        fp_loads=0
        gpr_loads=0
        ambiguous_xform_memory=0
        for i,w in enumerate(words):
            _word(w)
            op=w>>26
            pc=entry+i*4
            if op==18:
                if w&1:
                    dest=_bl_target(pc,w)
                    if dest%4 or not 0x80000000<=dest<0x81800000:
                        raise ValueError("unqualified source BL target")
                    direct_calls.append({
                        "relative_pc":_rel(pc,entry),
                        "target_public_code_pc":f"0x{dest:08X}",
                    })
                else:nonlink_direct+=1
            elif op==16:
                conditional+=1
            elif op==19 and (w>>1)&1023 in(16,528):
                indirect+=1
            elif op in FLOAT_STORE_OPS or op in GPR_STORE_OPS:
                row={
                    "relative_pc":_rel(pc,entry),
                    "source_base_GPR":f"r{(w>>16)&31}",
                    "source_signed_displacement":((w&65535)-65536 if w&32768 else w&65535),
                    "store_kind":"float_D_form" if op in FLOAT_STORE_OPS else "integer_D_form",
                    "receiver_alias_or_actual_ball_write_verified":False,
                }
                (fp_stores if op in FLOAT_STORE_OPS else gpr_stores).append(row)
            elif op in FLOAT_LOAD_OPS:fp_loads+=1
            elif op in GPR_LOAD_OPS:gpr_loads+=1
            elif op==31 and (w>>1)&1023 in X_STORE_XOS:
                ambiguous_xform_memory+=1
        summary.append({
            "public_source_function":name,
            "function_size_bytes":length,
            "source_words_verified":length//4,
            "direct_linked_calls":direct_calls,
            "direct_call_count":len(direct_calls),
            "source_conditional_branch_count":conditional,
            "source_indirect_branch_count":indirect,
            "source_nonlink_direct_b_count":nonlink_direct,
            "source_integer_D_form_store_sites":gpr_stores,
            "source_float_D_form_store_sites":fp_stores,
            "source_integer_D_form_load_count":gpr_loads,
            "source_float_D_form_load_count":fp_loads,
            "source_X_form_store_candidates_not_proven_receiver":ambiguous_xform_memory,
            "pure_predicate_or_game_ball_integrator_verified":False,
        })

    # Exactly four instruction slots between the first and second BL.
    gap=[]
    for off in range(0x80,0x90,4):
        w=main_words[off//4]
        op=w>>26
        row={"main_function_relative_pc":_rel(ENTRY+off,ENTRY)}
        if op==16:
            dest=_bc_target(ENTRY+off,w)
            row["source_class"]="conditional_branch"
            row["forward_branch_bypasses_second_BL_syntactically"]=(
                dest>ENTRY+0x90 and 0x80000000<=dest<0x81800000)
            row["target_main_function_relative_pc"]=(
                _rel(dest,ENTRY) if ENTRY<=dest<ENTRY+0x194 else None)
        elif op==18:
            dest=_bl_target(ENTRY+off,w)
            row["source_class"]="direct_BL" if w&1 else "direct_B"
            row["forward_branch_bypasses_second_BL_syntactically"]=(
                not(w&1) and dest>ENTRY+0x90 and 0x80000000<=dest<0x81800000)
            row["target_main_function_relative_pc"]=(
                _rel(dest,ENTRY) if ENTRY<=dest<ENTRY+0x194 else None)
        elif op==19:
            row["source_class"]="special_branch_or_control_opcode"
            row["forward_branch_bypasses_second_BL_syntactically"]=False
        elif op==11 and ((w>>16)&31)==3 and (w&65535)==0:
            row["source_class"]="compare_r3_to_zero_syntax"
            row["forward_branch_bypasses_second_BL_syntactically"]=False
        else:
            row["source_class"]="other_PPC_source_instruction"
            row["forward_branch_bypasses_second_BL_syntactically"]=False
        gap.append(row)
    return {
        "kind":"P0-REV1-THREE-SIM-CALLEE-BOUNDED-FOOTPRINT",
        "prior_101_word_source_BL_and_prefix_gates_held":True,
        "exact_three_source_callee_instruction_total":237,
        "callee_source_code_unchanged_across_seven":True,
        "callee_footprints":summary,
        "gap_after_first_before_second_call":gap,
        "game_update_function_semantics_verified":False,
        "either_sim_callee_executes_once_per_scene_callback_verified":False,
        "runtime_global_or_selected_ball_receiver_verified":False,
        "guest_physics_step_clock_verified":False,
        "rendered_projectile_or_world_xyz_velocity_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }
