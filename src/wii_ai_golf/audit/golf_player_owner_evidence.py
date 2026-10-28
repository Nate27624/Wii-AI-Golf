"""Private read-only Rev1 RPGolPlayer pointer-owner evidence in the golf-main object.

A static .data region plus code pointers can SUPPORT a dynamic-type
hypothesis. It does NOT prove a typed C++ pointer, player swing state,
shot-power semantic or object lifetime. No game memory bytes are exported.
"""
from __future__ import annotations
import struct

from wii_ai_golf.audit.golf_cross_bank_state import (
    _Banks, audit_pair, STATIC_SCENE_SLOTS, STATIC_PLAYER_MANAGER
)

# doldecomp/ogws config/RSPE01_01/splits.txt source compilation unit bounds:
PLAYER_TEXT = (0x8029E62C, 0x802A2210)
PLAYER_DATA = (0x803C7CC8, 0x803C7DD0)
PLAYER_MANAGER_TEXT = (0x802A2210, 0x802A3560)
PLAYER_MANAGER_DATA = (0x803C7DD0, 0x803C7DE0)
MAIN_DATA = (0x803C7798, 0x803C77C0)
N_TABLE_WORDS = 12
MAIN_BYTES = 0x100
MIN_FUNCTION_POINTERS = 3


def _in(pointer, interval):
    return interval[0] <= pointer < interval[1]


def _table_evidence(banks, object_ptr, data_interval, code_interval):
    if banks.region(object_ptr, 0x80) != "MEM2":
        return None
    vptr = banks.u32(object_ptr)
    if not _in(vptr, data_interval):
        return None
    # Static global .data vtable guess. Ensure it can physically be read,
    # but do not infer a vtable merely from code-shaped words alone.
    if banks.region(vptr, N_TABLE_WORDS * 4) != "MEM1":
        return None
    functions = sum(_in(banks.u32(vptr + 4*i), code_interval)
                    for i in range(N_TABLE_WORDS))
    if functions < MIN_FUNCTION_POINTERS:
        return None
    return functions


def audit_player_owner(mem1, mem2, *, strict_size=True):
    """Scan ONLY 0x100 source-gated RPGolMain relative words; no bulk guessing."""
    source = audit_pair(mem1, mem2, strict_size=strict_size)
    banks = _Banks(mem1, mem2)
    manager = next(banks.u32(slot) for slot in STATIC_SCENE_SLOTS
                   if banks.region(banks.u32(slot), 0x20))
    scene = banks.u32(manager + 0x0C)
    main = banks.u32(scene + 0x9C)
    if not _in(banks.u32(main), MAIN_DATA):
        raise ValueError("Golf-main source .data pointer provenance missing")
    matches = []
    for offset in range(0x04, MAIN_BYTES, 4):
        candidate = banks.u32(main + offset)
        count = _table_evidence(banks, candidate, PLAYER_DATA, PLAYER_TEXT)
        if count is not None:
            matches.append({
                "owner": "source_gated_RPGolMain",
                "owner_relative_offset": f"+0x{offset:03X}",
                "target_bank": "MEM2",
                "first_word_within_player_data_unit": True,
                "first_twelve_table_words_in_player_text_unit": count,
                "vtable_hypothesis_only": True,
            })
    player_manager = banks.u32(STATIC_PLAYER_MANAGER)
    mgr_table = _table_evidence(
        banks, player_manager, PLAYER_MANAGER_DATA, PLAYER_MANAGER_TEXT)
    return {
        "schema_version": 1,
        "kind": "local-golf-player-object-source-evidence",
        "source": "doldecomp/ogws RSPE01_01/splits.txt Golf Main/Player/PlayerManager",
        "game_id": "RSPE01", "revision": 1, "game_mode": 4,
        "scene_chain_and_backlink_verified": source["source_chain"][
            "scene_backlink_matches_manager"],
        "source_main_object_vtable_data_unit_suggested": True,
        "main_words_screened": MAIN_BYTES // 4,
        "player_data_and_text_cross_unit_candidates": matches,
        "candidate_count": len(matches),
        "unique_source_player_like_candidate": len(matches) == 1,
        "player_manager_source_table_candidate": mgr_table is not None,
        "player_manager_first_twelve_table_words_in_manager_text_unit":
            mgr_table if mgr_table is not None else 0,
        "actual_C++_dynamic_type_verified": False,
        "player_object_lifetime_verified": False,
        "club_head_pose_verified": False,
        "swing_power_verified": False,
        "ball_state_verified": False,
        "same_game_frame_proven": False,
        "raw_memory_or_runtime_pointers_exported": False,
        "allowed_to_publish": False,
        "next_action": "Trace source writes into single source-player-like candidate "
                       "and validate object type in debugger before sampling "
                       "small relative windows around control and shot events.",
        "warning": "Comp-unit .data matches and calls into code unit do NOT "
                   "prove C++ object identity or field semantics. No model."
    }
