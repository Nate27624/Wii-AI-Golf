"""Pure bounded PPC callsite inventory for Rev1 Golf::fn_8028E158.

Only invoked after original 7-capture OnCalculate thunk validates scene+0x9C
and exact branch to this entry. Independent immutable ogws symbols.txt Rev1
records fn_8028E158 0x8028E158 size 0x194 = 101 instructions.
No blanket code search, runtime code hook, game writes or private bytes output.
Static counts cannot prove physics cadence, execution, model/render binding.
"""
from __future__ import annotations

MAIN_ENTRY=0x8028E158
MAIN_SIZE=0x194
MAIN_END=MAIN_ENTRY+MAIN_SIZE
MAIN_UNIT=(0x8028E098,0x8028E900)
SIM_UNIT=(0x8029B240,0x8029BBB4)
GOLF_MAPOBJ_BALL_UNIT=(0x80296FD8,0x8029B240)
SOURCE_FUNCTION="fn_8028E158"
SOURCE_WORDS=MAIN_SIZE//4

def _decode_b(pc: int, w: int) -> int:
    off=w&0x03FFFFFC
    if off&0x02000000:
        off-=0x04000000
    return (off if w&2 else pc+off)&0xffffffff

def _unit(dest: int) -> str:
    if SIM_UNIT[0]<=dest<SIM_UNIT[1]:
        return "published_RPGolSimulateManager_text_only"
    if MAIN_UNIT[0]<=dest<MAIN_UNIT[1]:
        return "published_RPGolMain_text_only"
    if GOLF_MAPOBJ_BALL_UNIT[0]<=dest<GOLF_MAPOBJ_BALL_UNIT[1]:
        return "published_RPGolMapObjBall_text_only"
    return "outside_three_published_Golf_source_units"

def _loc(pc: int) -> str:
    return "+0x%04X" % (pc-MAIN_UNIT[0])

def classify_source_words(words, *, thunk_target: str) -> dict:
    if thunk_target!="0x8028E158":
        raise ValueError("original source-gated thunk target did not match exact function entry")
    if not isinstance(words,(tuple,list)) or len(words)!=SOURCE_WORDS:
        raise ValueError("expected exactly 101 bounded Golf main source words")
    if any(type(w) is not int or not 0<=w<=0xffffffff for w in words):
        raise ValueError("malformed source PPC word")
    direct=[]
    cond_count=0
    plain_count=0
    indirect_branch_count=0
    indirect_link_count=0
    unk_special_branch_count=0
    other_b_links=0
    for i,w in enumerate(words):
        pc=MAIN_ENTRY+i*4
        op=w>>26
        if op==18:  # PPC direct I-form b / bl
            dest=_decode_b(pc,w)
            if dest%4 or not 0x80000000<=dest<0x81800000:
                raise ValueError("unqualified source direct branch destination")
            if w&1:
                direct.append({
                    "source_main_unit_relative_pc":_loc(pc),
                    "target_public_code_pc":f"0x{dest:08X}",
                    "target_source_code_unit_class":_unit(dest),
                    "actual_execution_or_receiver_type_verified":False,
                })
            else:
                plain_count+=1
        elif op==16:  # PPC conditional B-form; don't assume executed
            cond_count+=1
            if w&1:
                other_b_links+=1
        elif op==19:
            xo=(w>>1)&1023
            if xo in (16,528):  # bclr / bcctr (+ LK for bclrl / bcctrl)
                indirect_branch_count+=1
                if w&1:
                    indirect_link_count+=1
            elif w&1:
                unk_special_branch_count+=1

    count_sim=sum(
        d["target_source_code_unit_class"]=="published_RPGolSimulateManager_text_only"
        for d in direct)
    return {
        "kind":"P0-REV1-GOLF-MAIN-UPDATE-DIRECT-BL-BOUNDED-CENSUS",
        "source_function":SOURCE_FUNCTION,
        "source_entry_public_code_pc":f"0x{MAIN_ENTRY:08X}",
        "source_function_size_bytes":MAIN_SIZE,
        "exact_source_words_scanned":SOURCE_WORDS,
        "source_thunk_target_exact_entry_qualified":True,
        "source_direct_linked_calls":direct,
        "source_direct_linked_call_count":len(direct),
        "source_direct_BL_target_in_simulate_manager_code_unit_count":count_sim,
        "source_conditional_branch_count":cond_count,
        "source_direct_nonlinking_branch_count":plain_count,
        "source_indirect_branch_instruction_count":indirect_branch_count,
        "source_indirect_linked_branch_count":indirect_link_count,
        "source_conditional_link_or_unclassified_branch_count":other_b_links+unk_special_branch_count,
        "all_paths_call_simulator_exactly_once_verified":False,
        "any_call_is_game_ball_physics_update_verified":False,
        "guest_physics_step_clock_verified":False,
        "dynamic_run_or_scene_vtable_dispatch_verified":False,
        "rendered_ball_visual_join_verified":False,
        "physical_xyz_velocity_power_impact_score_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }
