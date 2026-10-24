"""Read-only pointers from public Wii Sports US Rev 1 golf structure notes.

Exploratory only: neither the pointers nor Hitting the Green interpretation
have been live validated. Require RSPE01 game ID and disc revision 1 first.
"""
from __future__ import annotations

from typing import Any

SOURCE = "https://github.com/kiwi515/ogws_info (RP/RPSports headers, US Rev 1)"
STATIC = {
    "golf_config": (0x804BF8C4, 0x9C, {"game_mode_raw": 0x94, "hole_raw": 0x98}),
    "golf_field": (0x804BF868, 0xA8, {
        "map_data_ptr": 0x18, "current_pin_obj_ptr": 0x44,
        "current_start_obj_ptr": 0x50, "cup_obj_ptr": 0x54,
        "course_obj_ptr": 0x70, "minimap_course_obj_ptr": 0x74,
        "minimap_ball_eff_ptr": 0x9C,
    }),
    "sports_sequence": (0x804BF708, 0xB0, {
        "training_game_raw": 0x0C, "golf_mode_raw": 0xAC,
    }),
}


def _plausible(ptr: int, size: int) -> bool:
    return (0x80000000 <= ptr < 0x81800000 and ptr + size <= 0x81800000) or (
        0x90000000 <= ptr < 0x94000000 and ptr + size <= 0x94000000)


def _u32(rpc: Any, address: int) -> int:
    result = rpc.call("memory.read_u32", [address])
    if type(result) is not int or not 0 <= result <= 0xFFFFFFFF:
        raise ValueError("invalid read_u32 result")
    return result


def probe_rev1(rpc: Any) -> dict[str, Any]:
    """Only dereference instance pointers if the game header matches US Rev1."""
    header_hex = rpc.call("memory.read_bytes", [0x80000000, 8])
    if not isinstance(header_hex, str) or len(header_hex) != 16:
        raise ValueError("invalid game header returned")
    header = bytes.fromhex(header_hex)
    code = header[:6].decode("ascii", errors="replace")
    revision = header[7]
    info: dict[str, Any] = {
        "source": "external-decomp-symbol-hints-read-only-unverified",
        "reference": SOURCE, "game_id": code, "disc_revision": revision,
        "supported": code == "RSPE01" and revision == 1,
        "fields": {},
    }
    if not info["supported"]:
        info["warning"] = "Static offsets unverified for this game/region/revision; NO struct reads performed"
        return info
    for name, (static_addr, size, fields) in STATIC.items():
        ptr = _u32(rpc, static_addr)
        item: dict[str, Any] = {
            "static_pointer_address": f"0x{static_addr:08X}",
            "instance_pointer": f"0x{ptr:08X}",
            "plausible_mem_pointer": _plausible(ptr, size),
        }
        if item["plausible_mem_pointer"]:
            item["raw_fields"] = {
                field: {"offset": f"+0x{offset:X}",
                        "value_hex": f"0x{_u32(rpc, ptr + offset):08X}"}
                for field, offset in fields.items()
            }
        else:
            item["raw_fields"] = {}
        info["fields"][name] = item
    info["warning"] = "Unverified struct addresses; raw fields/pointers require visual multi-run confirmation"
    return info
