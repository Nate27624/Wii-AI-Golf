"""Source-anchored allocation/null-check candidate for the global ball slot.

From public RSPE01 Rev1 ogws map (symbol blob
ec42efd5ef247dff7920e905f9004fc579dd3f74) and public EGG source:
  fn_8029A038 entry 0x8029A038 size 0xA8, RPGolMapObjBall.cpp
  __nw__FUl (operator new(size_t)) entry 0x800A3244, eggHeap.cpp
  fn_8029AB78 entry 0x8029AB78 size 0x21C, RPGolMapObjBall.cpp

These exact public symbols have been resolved. Classification of bc
must inspect PPC BO/BI instead of blindly assuming a conditional branch.
R3 side effects and whether the second call is a constructor are NOT proven.
No private RAM, source instruction words, heap pointer values, or uploads.
"""
from __future__ import annotations
import review_p0_global_slot_post_return_paths as prior

PUBLIC_SYMBOL_BLOB_SHA="ec42efd5ef247dff7920e905f9004fc579dd3f74"
PUBLIC_SPLITS_BLOB_SHA="df4085de5285b0d188fdfec8c097b301382263d3"

ENTRY_PC=0x8029A038
FIRST_CALL=prior.FIRST_BL
SECOND_CALL=prior.SECOND_BL
COMPARE_PC=FIRST_CALL+4
BRANCH_PC=prior.BRANCH_PC

TARGETS=(
  ("__nw__FUl","egg/core/eggHeap.cpp",0x800A3244,0x800A2C2C,0x800A341C),
  ("fn_8029AB78","Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp",
   0x8029AB78,0x80296FD8,0x8029B240),
)

def compare_r3_zero(word:int) -> dict:
    if type(word) is not int or not 0<=word<=0xffffffff:
        raise ValueError("non PPC instruction")
    op=word>>26
    if op not in (10,11):
        return {"compare_r3_zero_verified":False,
                "kind":"not_immediate_compare"}
    ra=(word>>16)&31
    imm=word&0xffff
    bf=(word>>23)&7
    l=(word>>21)&1
    verified=ra==3 and imm==0 and bf==0 and l==0
    return {"compare_r3_zero_verified":verified,
            "kind":("cmplwi_cr0_r3_zero" if op==10 else "cmpwi_cr0_r3_zero")
                    if verified else "other_immediate_compare"}

def branch_BO_BI(word:int) -> dict:
    if type(word) is not int or not 0<=word<=0xffffffff or word>>26!=16:
        raise ValueError("not branch conditional PPC instruction")
    bo=(word>>21)&31
    bi=(word>>16)&31
    cr_ignored=bool(bo&16)
    ctr_ignored=bool(bo&4)
    always=cr_ignored and ctr_ignored
    return {
        "BO_category":("unconditional_always" if always else
                       "CR_condition" if not cr_ignored and ctr_ignored else
                       "CTR_condition" if cr_ignored else "CR_and_CTR_condition"),
        "branch_to_store_unconditionally":always,
        "branch_to_store_conditional":not always,
        "CR0_EQ_bit_selected":bi==2 and not cr_ignored,
        "CR0_EQ_desired_true":bool(bo&8) if bi==2 and not cr_ignored else None,
        "requires_ctr_state":not ctr_ignored,
    }

def analyze(read,source_global_displacement:int)->dict:
    paths=prior.analyze(read,source_global_displacement)
    if prior.POST_ENTRY!=ENTRY_PC:
        raise ValueError("pinned public entry does not match source boundary")
    if (paths["first_bl_target_public_code_pc"] != "0x800A3244"
        or paths["second_bl_target_public_code_pc"]!="0x8029AB78"):
        raise ValueError("expected public symbols not actual PPC BL targets")
    cmp=compare_r3_zero(read(COMPARE_PC))
    bo=branch_BO_BI(read(BRANCH_PC))
    is_null_guard=bool(cmp["compare_r3_zero_verified"]
        and bo["BO_category"]=="CR_condition"
        and bo["CR0_EQ_bit_selected"]
        and bo["CR0_EQ_desired_true"])
    if bo["branch_to_store_unconditionally"]:
        # Prior helper assumes all bc can fall through. The BO category
        # overrides that incorrect possibility only at this exact site.
        true_sources=["return_from_first_bl"]
        second_call_possible=False
    else:
        true_sources=paths["store_r3_candidate_sources_from_this_entry"]
        second_call_possible=paths["path_with_r3_from_second_bl_possible"]
    return {
        "source_function_entry_symbol":"fn_8029A038",
        "source_function_entry_matches_public_map":True,
        "source_function_size_known_from_public_symbol":True,
        "exact_operator_new_target_verified":True,
        "first_callee_public_symbol":TARGETS[0][0],
        "first_callee_source_unit":TARGETS[0][1],
        "first_callee_unit_relative_entry":"+0x%04X"%(TARGETS[0][2]-TARGETS[0][3]),
        "second_callee_public_symbol":TARGETS[1][0],
        "second_callee_source_unit":TARGETS[1][1],
        "second_callee_unit_relative_entry":"+0x%04X"%(TARGETS[1][2]-TARGETS[1][3]),
        "source_map_public_ogws_symbols_pinned":True,
        "branch_to_store":bo,
        "compare_after_operator_new":cmp,
        "null_allocation_skips_second_call_pattern_verified":is_null_guard,
        "second_call_possible_per_BO_category":second_call_possible,
        "post_return_store_r3_candidate_classes_after_BO":true_sources,
        "intervening_instruction_r3_effect_not_exhaustively_verified":True,
        "second_callee_is_ball_constructor_verified":False,
        "source_pointer_is_initialized_to_new_object_verified":False,
        "actual_written_pointer_value_verified":False,
        "function_called_at_runtime_verified":False,
        "renderer_uses_global_object_verified":False,
        "ball_physical_xyz_velocity_contact_power_score_verified":False,
        "training_approved":False,
    }
