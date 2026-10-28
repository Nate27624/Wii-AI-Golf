"""S002 offline Rev1 GetWind() source-table candidate checks.

This reads a private existing MEM1+MEM2 pair. Only bounded statistics leave
this function: no runtime integer entries, memory pointers, file paths,
game-memory bytes, or unknown wind-unit/angle assertions.

It depends on the canonical S002 paired-bank source chain (PR #151).
Exports can be from different emulated frames; this never proves a wind
value belongs to a particular observed onscreen hole or shot.
"""
from __future__ import annotations

from .golf_cross_bank_state import (
    _Banks, audit_pair, STATIC_CONFIG, BASE_MEM1, MEM1_SIZE,
)

# Source-identified RPGolConfig::GetWind in US Rev1 DOL at 0x8029CE74.
# The function indexes two tables of 9 BE u32 entries by mCurrentHole
# at config+0x98. Tables are RPGolConfig.cpp .bss, NOT DOL file contents.
WIND_DIRECTION_TABLE = 0x804A8B54
WIND_SPEED_TABLE = 0x804A8B78
WIND_SLOTS = 9


def audit_wind_source_tables(mem1, mem2, *, strict_size: bool = True) -> dict:
    """Shape-check both fixed raw integer tables after source-chain validation.

    Function's name/argument order is independently documented by
    kiwi515/ogws_info RPGolConfig::GetWind(dirOut,spdOut), while exact BSS
    addresses and index are inferred from the operator's US Rev1 DOL.
    Raw integer values are deliberately NOT returned or categorized as
    degrees, m/s or miles per hour.
    """
    source = audit_pair(mem1, mem2, strict_size=strict_size)
    if source["conditions"]["game_mode"] != 4:
        raise ValueError("Not a validated Golf training mode")
    banks = _Banks(mem1, mem2)

    cfg = banks.u32(STATIC_CONFIG)
    if banks.region(cfg, 0x9C) is None:
        raise ValueError("Source RPGolConfig object not accessible")
    index = banks.u32(cfg + 0x98)
    # The 9-entry source BSS arrays are indexed directly: do not modulo,
    # mask, clamp or assume this is the onscreen 1-based hole number.
    if type(index) is not int or not 0 <= index < WIND_SLOTS:
        raise ValueError("Source wind hole index out of nine-slot range")

    # Require that *every* source table entry resides in the MEM1 image.
    for start in (WIND_DIRECTION_TABLE, WIND_SPEED_TABLE):
        if (not BASE_MEM1 <= start
                or start + 4 * WIND_SLOTS > BASE_MEM1 + min(len(mem1), MEM1_SIZE)):
            raise ValueError("Raw wind table is not within captured MEM1")
    dirs = tuple(banks.u32(WIND_DIRECTION_TABLE + 4 * i)
                 for i in range(WIND_SLOTS))
    speeds = tuple(banks.u32(WIND_SPEED_TABLE + 4 * i)
                   for i in range(WIND_SLOTS))

    return {
        "kind": "local_golf_rev1_getwind_bss_shape_audit",
        "schema_version": 1,
        "study_id": "S002-REV1-WIND-SOURCE-01",
        "game_id": "RSPE01",
        "revision": 1,
        "mode4_source_chain_verified": True,
        "raw_hole_table_index_in_bounds": True,
        "raw_hole_index_source_member_verified": True,
        "table_slots_read": WIND_SLOTS,
        "direction_table_distinct_raw_word_count": len(set(dirs)),
        "speed_table_distinct_raw_word_count": len(set(speeds)),
        "direction_table_nonzero_word_count": sum(bool(x) for x in dirs),
        "speed_table_nonzero_word_count": sum(bool(x) for x in speeds),
        "selected_direction_raw_word_nonzero": bool(dirs[index]),
        "selected_speed_raw_word_nonzero": bool(speeds[index]),
        "direction_raw_all_entries_equal": len(set(dirs)) == 1,
        "speed_raw_all_entries_equal": len(set(speeds)) == 1,
        "raw_hole_index_exposed": False,
        "raw_wind_integer_values_exposed": False,
        "individual_slot_addresses_exposed": False,
        "game_getwind_code_execution_observed": False,
        "same_emulated_frame_pair_verified": False,
        "same_boot_pair_verified": False,
        "windspeed_units_verified": False,
        "wind_direction_convention_verified": False,
        "visual_wind_correspondence_verified": False,
        "runtime_gameplay_wind_verified": False,
        "approved_for_model_training": False,
        "private_input_bytes_published": False,
        "warning": (
            "Read-only US Rev1 source-table shape test against one pair of "
            "not-proven-synchronous private banks. Source-backed GetWind "
            "lookup sites do not establish onscreen wind direction, units, "
            "current gameplay phase, or same-boot timing. Raw table values "
            "are not published; don't fit a model using these flags."
        ),
    }
