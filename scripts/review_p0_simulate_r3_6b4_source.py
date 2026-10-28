"""Pure PPC source-only triage of the SimulateManager +0x6B4 receiver-base.

Original operator #263: nearest r4 writer is lwz r4,+0x6B4(r3), then
mr r3,r4, then bl fn_80299ACC. This helper inspects only the bounded public
code window BEFORE the identified load for possible r3 producers. It MUST
receive an independently 14-bank SHA / RSPE01 Rev1 source-gated read_u32.

All classifications are syntactic; branches/calls, unknown PPC opcodes and
uncertain function boundaries preclude any all-path or runtime object claims.
No native files, instructions, user pointers, float values or hashes exposed.
"""
from __future__ import annotations

import review_p0_outer_operand_r4_r30_source as upstream

LABEL, ENTRY, CALLEE, OPERAND = upstream.SOURCES[0]
LOOKBACK_WORDS = 32
EXPECTED_DISPLACEMENT = "+0x6B4"


def analyze(read_u32):
    """Classify source r3 for one exact lwz r4,+0x6B4(r3) candidate."""
    qualified = upstream.analyze(read_u32)
    row = qualified["outer_operand_source_rows"][0]
    detail = row["nearest_pre_mr_integer_load_source_detail"]
    result = {
        "kind": "P0-SANITIZED-SIMULATE-R3-BASE-FOR-6B4",
        "exact_outer_callsite_syntactic_source_qualified": False,
        "actual_source_load_is_lwz_r4_plus_0x6b4_r3": False,
        "candidate_load_entry_relative_offset": None,
        "candidate_r3_source_class": None,
        "candidate_r3_definition_entry_relative_offset": None,
        "static_branch_or_call_before_load": None,
        "static_control_transfer_after_candidate_r3_definition": None,
        "nearby_call_before_load_could_write_r3": None,
        "status": "ABSTAIN_SOURCE_LOADER_MISMATCH",
        "source_entry_is_verified_function_extent": False,
        "all_path_r3_reaching_definition_verified": False,
        "base_r3_is_simulate_manager_or_ball_object_verified": False,
        "value_loaded_from_6b4_is_global_or_roster_ball_verified": False,
        "dynamic_ball_receiver_verified": False,
        "ball_xyz_velocity_power_impact_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }
    if (row["exact_inner_bl_in_bounded_0x100_window_count"] != 1 or
            not row["mr_r3_from_expected_operand_confirmed"] or
            detail is None or
            detail.get("candidate_D_form_integer_load_mnemonic") != "lwz" or
            detail.get("candidate_base_register") != "r3" or
            detail.get("candidate_source_field_displacement") != EXPECTED_DISPLACEMENT or
            row["tracked_source_operand"] != "r4"):
        return result
    offset = row["nearest_pre_mr_operand_write_entry_relative_offset"]
    if type(offset) is not str or not offset.startswith("+0x"):
        return result
    try:
        index = int(offset[3:], 16) // 4
    except ValueError:
        return result
    if index <= 0 or index >= upstream.SOURCE_WINDOW // 4:
        return result
    src = [_valid(read_u32(ENTRY + i * 4)) for i in range(index)]
    current = _valid(read_u32(ENTRY + index * 4))
    if (current >> 26 != 32 or (current >> 21) & 31 != 4
            or (current >> 16) & 31 != 3
            or (current & 0xFFFF) != 0x6B4):
        return result
    result["exact_outer_callsite_syntactic_source_qualified"] = True
    result["actual_source_load_is_lwz_r4_plus_0x6b4_r3"] = True
    result["candidate_load_entry_relative_offset"] = offset
    result["static_branch_or_call_before_load"] = any(
        upstream._control(x) for x in src)
    result["nearby_call_before_load_could_write_r3"] = any(
        x >> 26 == 18 and (x & 1) != 0 for x in src)
    start = max(0, index - LOOKBACK_WORDS)
    writers = [(i, upstream._source_write(src[i], 3))
               for i in range(start, index)
               if upstream._source_write(src[i], 3) is not None]
    if writers:
        last, kind = writers[-1]
        result["candidate_r3_source_class"] = kind
        result["candidate_r3_definition_entry_relative_offset"] = f"+0x{last*4:03X}"
        result["static_control_transfer_after_candidate_r3_definition"] = any(
            upstream._control(src[i]) for i in range(last+1,index))
        result["status"] = (
            "ABSTAIN_R3_CONTROL_TRANSFER_OR_UNKNOWN_WRITER"
            if result["static_branch_or_call_before_load"] or
               result["static_control_transfer_after_candidate_r3_definition"] or
               kind.startswith("unknown")
            else "SOURCE_SYNTAX_ONLY_R3_PRODUCER_CANDIDATE"
        )
    else:
        result["status"] = (
            "ABSTAIN_R3_POSSIBLE_CALL_RETURN"
            if result["nearby_call_before_load_could_write_r3"]
            else "ABSTAIN_ENTRY_R3_OR_UNSUPPORTED_PRODUCER"
        )
    return result


def _valid(word):
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("unqualified source instruction")
    return word
