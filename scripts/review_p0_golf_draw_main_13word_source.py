"""Pure bounded RSPE01 Rev1 drawing-side 13-word direct-control census.

Only invoke with canonical #231 Rev1 scene/source-gated read_u32. Exact
published fn_8028E0B0 entry and size 0x34; classification is SOURCE SYNTAX,
not a renderer invocation, game physics step, object identity or visual join.
No private bytes, source instruction words or heap addresses in output.
"""
from __future__ import annotations

ENTRY = 0x8028E0B0
SIZE = 0x34
END = ENTRY + SIZE
WORD_COUNT = SIZE // 4
MAP_OBJ_BALL_LO, MAP_OBJ_BALL_HI = 0x80296FD8, 0x8029B240
SIMULATE_MANAGER_LO, SIMULATE_MANAGER_HI = 0x8029B240, 0x8029BBB4
# Immutable published RSPE01 Rev1 .text source splits, not named functions.
# ogws config/RSPE01_01/splits.txt Git blob df4085de5285b0d188fdfec8c097b301382263d3
GOLF_DRAW_MANAGER_LO, GOLF_DRAW_MANAGER_HI = 0x80294184, 0x8029528C
GOLF_UNSPLIT_LO, GOLF_UNSPLIT_HI = 0x802A79F8, 0x802C7924


def _word(w):
    if type(w) is not int or not 0 <= w <= 0xFFFFFFFF:
        raise ValueError("unqualified 32-bit PPC code")
    return w


def _target(w, pc):
    """Exact PPC direct I-form BL/B target, not dynamic branch resolution."""
    if w >> 26 != 18:
        return None
    displacement = w & 0x03FFFFFC
    if displacement & 0x02000000:
        displacement -= 0x04000000
    target = displacement if w & 2 else pc + displacement
    if target % 4 or not 0x80000000 <= target <= 0x817FFFFC:
        return None
    return target


def _public_unit(target):
    if MAP_OBJ_BALL_LO <= target < MAP_OBJ_BALL_HI:
        return "RPGolMapObjBall_source_unit_ONLY"
    if SIMULATE_MANAGER_LO <= target < SIMULATE_MANAGER_HI:
        return "RPGolSimulateManager_source_unit_ONLY"
    if GOLF_DRAW_MANAGER_LO <= target < GOLF_DRAW_MANAGER_HI:
        return "RPGolDrawManager_source_unit_ONLY"
    if GOLF_UNSPLIT_LO <= target < GOLF_UNSPLIT_HI:
        return "RPGolScene_unsplit_source_unit_ONLY"
    return "OTHER_OR_UNKNOWN_PUBLIC_TEXT"


def census(read_u32):
    """One finite native source function; no scans, speculation or guest I/O."""
    words = [_word(read_u32(ENTRY + offset))
             for offset in range(0, SIZE, 4)]
    call_sites = []
    branch_sites = []
    indirect_sites = []
    d_form_base_r3 = []
    ordinary_blr_count = 0
    source_sc_count = 0
    possible_return_or_indirect = 0
    for i, w in enumerate(words):
        pc = ENTRY + i * 4
        offset = f"+0x{i*4:02X}"
        op = w >> 26
        if op == 18:
            target = _target(w, pc)
            item = {
                "source_function_relative_offset":offset,
                "target_public_code_pc":f"0x{target:08X}" if target is not None else None,
                "target_public_golf_unit_hint":
                    _public_unit(target) if target is not None else "INVALID_ABSTAIN",
                "actual_call_executed_verified":False,
            }
            if w & 1:
                call_sites.append(item)
            else:
                branch_sites.append(item)
        elif op == 16:
            branch_sites.append({
                "source_function_relative_offset":offset,
                "target_public_code_pc":None,
                "target_public_golf_unit_hint":"CONDITIONAL_BRANCH_TARGET_NOT_TYPED",
                "actual_call_executed_verified":False,
            })
        elif op == 17:  # PPC sc: system call, NOT a branch or guest physics tick.
            source_sc_count += 1
        elif op == 19 and ((w >> 1) & 1023) in (16, 528):
            if w == 0x4E800020:
                ordinary_blr_count += 1
            else:
                possible_return_or_indirect += 1
                indirect_sites.append(offset)
        if op in (32, 34, 40, 42, 48, 50, 36, 38, 44, 52, 54):
            base = (w >> 16) & 31
            if base == 3:
                imm = w & 0xFFFF
                if imm & 0x8000:
                    imm -= 0x10000
                d_form_base_r3.append({
                    "source_function_relative_offset":offset,
                    "syntactic_access":"load" if op in (32,34,40,42,48,50) else "store",
                    "source_field_displacement":
                        imm if -512 <= imm <= 512 else None,
                    "base_r3_actual_object_type_verified":False,
                })
    return {
        "kind":"P0-STATIC-GOLF-DRAW-MAIN-13-WORD-CENSUS",
        "published_function_entry":"fn_8028E0B0",
        "published_function_size_PPC_words":WORD_COUNT,
        "source_direct_BL_count":len(call_sites),
        "source_direct_BL_sites":call_sites,
        "source_branch_instructions_count":len(branch_sites),
        "source_branch_sites":branch_sites,
        "source_noncanonical_indirect_or_return_control_count":
            possible_return_or_indirect,
        "source_noncanonical_indirect_or_return_offsets":indirect_sites,
        "source_plain_blr_count":ordinary_blr_count,
        "source_system_call_instruction_count":source_sc_count,
        "source_d_form_base_r3_accesses":d_form_base_r3,
        "all_path_draw_call_role_verified":False,
        "render_object_submit_function_typed_and_verified":False,
        "source_global_or_player_selected_ball_drawn_verified":False,
        "actual_guest_render_execution_verified":False,
        "visual_frame_and_guest_physics_step_join_verified":False,
        "physical_ball_xyz_velocity_contact_power_score_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }
