"""Offline PPC source-only upstream receiver-argument hints for S002 #240/#219.

No RAM/ROM input, filesystem, Dolphin, bridge, writes, parser imports, logging,
or network. This pure function consumes ONLY a caller-supplied, independently
Rev1/SHA-gated read_u32(pc) callback. No byte/word/pointer is ever serialized.
The two published source entries are not independently verified function extents.
The 0x100-byte forward windows can miss a real call; a static match does not
prove same function, reaching definition, object identity, or runtime execution.
"""
from __future__ import annotations

# From public source-gated #219 two-hop callgraph. Bounded lookahead is an
# explicit SEARCH WINDOW, NOT a verified function size or control-flow proof.
WINDOW = 0x100
LOCAL_DEFINITION_WINDOW = 0x40
SOURCES = (
    ("SimulateManager_outer_to_ball_local",
     0x8029B43C, 0x80299ACC, 0x8029B240, 0x8029BBB4),
    ("MapObjBall_outer_to_ball_local",
     0x8029A204, 0x80299C20, 0x80296FD8, 0x8029B240),
)

def _require_word(word):
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("invalid source PPC instruction")
    return word

def _branch(pc, word):
    """PPC b/bl: 26-bit signed, AA and LK respected."""
    word = _require_word(word)
    if word >> 26 != 18:
        return None
    disp = word & 0x03FFFFFC
    if disp & 0x02000000:
        disp -= 0x04000000
    target = (disp if word & 2 else pc + disp) & 0xFFFFFFFF
    return target, bool(word & 1)

def _control(word):
    """Syntax-level barrier only; no execution assertion."""
    word = _require_word(word)
    op = word >> 26
    if op == 18:
        return "linked_call" if word & 1 else "unconditional_branch"
    if op == 16:
        return "conditional_branch"
    if op == 17:
        return "system_call"
    if op == 19:
        xo = (word >> 1) & 1023
        if xo == 16:
            return "branch_to_link_register"
        if xo == 528:
            return "branch_to_count_register"
    return None

def _mr_r3(word):
    if word >> 26 != 31 or ((word >> 1) & 1023) != 444:
        return None
    rs, ra, rb = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
    return rs if ra == 3 and rb == rs else None

def _r3_definition(word):
    """A deliberately incomplete, explicitly classified GPR r3 write audit.

    Recognized D-form GPR loads/addi variants and exact mr only. Other op31
    instructions (which may or may not write r3) are *unknown*, never assumed
    to preserve r3.
    """
    word = _require_word(word)
    moved = _mr_r3(word)
    if moved is not None:
        return f"mr_r3_from_r{moved}"
    op, rt, ra = word >> 26, (word >> 21) & 31, (word >> 16) & 31
    if op in (14, 15, 32, 33, 34, 35, 40, 41, 42, 43) and rt == 3:
        if op in (14, 15):
            return "addi_or_addis_r3_immediate" if ra == 0 else f"addi_or_addis_r3_from_r{ra}"
        return f"gpr_load_r3_from_r{ra}"
    if op == 31 and (rt == 3 or ra == 3):
        return "other_X_form_possible_r3_write"
    return None

def inspect_upstream(read_u32):
    """Produce no raw memory or source words; refuse ambiguous call windows.

    Caller MUST independently attest exact RSPE01 Rev1 source bytes before
    invoking. We cannot authenticate a callback or detect unexamined control
    paths and deliberately make no such claims.
    """
    if not callable(read_u32):
        raise ValueError("source read callback required")
    rows = []
    for label, entry, callee, low, high in SOURCES:
        upper = entry + WINDOW
        if not low <= entry < upper <= high:
            raise ValueError("search window crosses published source unit")
        words = [_require_word(read_u32(pc)) for pc in range(entry, upper, 4)]
        calls = [
            index for index, word in enumerate(words)
            if _branch(entry + index * 4, word) == (callee, True)
        ]
        row = {
            "outer_source_function_entry_label": label,
            "known_inner_entry_target_from_219": True,
            "forward_scan_bytes_not_function_extent": WINDOW,
            "exact_direct_calls_found_within_window": len(calls),
            "candidate_callsite_source_entry_offset": None,
            "nearest_supported_r3_definition_class": None,
            "nearest_r3_definition_distance_words": None,
            "prior_control_transfer_in_window": None,
            "control_transfer_after_nearest_definition": None,
            "unsupported_possible_r3_write_seen": None,
            "bounded_syntactic_candidate_only": True,
            "all_paths_receiver_source_verified": False,
            "runtime_receiver_object_verified": False,
            "source_function_extent_verified": False,
        }
        if len(calls) != 1:
            row["status"] = ("NO_EXACT_DIRECT_CALL_IN_BOUNDED_WINDOW"
                             if not calls else "MULTIPLE_DIRECT_CALLS_ABSTAIN")
            rows.append(row)
            continue
        call_index = calls[0]
        previous = words[:call_index]
        near_start = max(0, call_index - LOCAL_DEFINITION_WINDOW // 4)
        candidates = [
            (i, _r3_definition(words[i]))
            for i in range(near_start, call_index)
            if _r3_definition(words[i]) is not None
        ]
        prior_controls = [_control(w) for w in previous]
        row["candidate_callsite_source_entry_offset"] = f"+0x{call_index * 4:03X}"
        row["prior_control_transfer_in_window"] = any(x is not None for x in prior_controls)
        row["unsupported_possible_r3_write_seen"] = any(
            label == "other_X_form_possible_r3_write" for _, label in candidates)
        if not candidates:
            row["status"] = "NO_SUPPORTED_NEAR_CALL_R3_SOURCE_ABSTAIN"
        else:
            index, cls = candidates[-1]
            row["nearest_supported_r3_definition_class"] = cls
            row["nearest_r3_definition_distance_words"] = call_index - index
            row["control_transfer_after_nearest_definition"] = any(
                _control(words[k]) is not None for k in range(index + 1, call_index))
            row["status"] = ("SYNTAX_ONLY_WITH_CONTROL_FLOW_HAZARD"
                             if row["prior_control_transfer_in_window"] or
                             row["unsupported_possible_r3_write_seen"]
                             else "SYNTAX_ONLY_NEEDS_CFG_AND_RUNTIME")
        rows.append(row)
    return {
        "kind": "P0-SANITIZED-OUTER-GOLF-RECEIVER-ARG-SOURCE-HINTS",
        "public_rev1_outer_source_windows_examined": len(SOURCES),
        "source_byte_provenance_authenticated_by_this_helper": False,
        "source_reader_requires_independent_RSPE01_rev1_SHA_gate": True,
        "window_absence_is_not_proof_of_no_other_call": True,
        "function_label_is_not_verified_dynamic_callstack": True,
        "source_global_or_selected_ball_receiver_identified": False,
        "cache_writer_executed_in_captured_shot_verified": False,
        "rendered_ball_identity_or_physics_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "outer_call_windows": rows,
    }
