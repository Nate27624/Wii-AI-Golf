"""Experimental, version-gated read-only golf map-object translations.

Source: kiwi515/ogws_info RPGolMapObjBase.h (mTrans at +0x30 and
mScale at +0x3C), RPGolFieldManager.h. User evidence supports inline
translation as plausible, but coordinates and units still need independent
visual validation. Published pointer offsets overlap the scale vector,
so this probe deliberately does NOT dereference translation pointers.
No writes or input calls.
"""
from __future__ import annotations

import math
import struct
from typing import Any

from .symbol_probe import probe_rev1

# Names are keys in symbol_probe.STATIC/golf_field, not addresses hardcoded here.
OBJECT_KEYS = ("current_pin_obj_ptr", "current_start_obj_ptr", "cup_obj_ptr", "course_obj_ptr", "minimap_course_obj_ptr")


def _valid_ptr(ptr: int, length: int) -> bool:
    if type(ptr) is not int or ptr % 4:
        return False
    return ((0x80000000 <= ptr < 0x81800000 and ptr + length <= 0x81800000)
            or (0x90000000 <= ptr < 0x94000000 and ptr + length <= 0x94000000))


def _read_vec3(rpc: Any, address: int) -> dict[str, Any]:
    if not _valid_ptr(address, 12):
        return {"status": "out_of_supported_ram", "address": f"0x{address:08X}"}
    value = rpc.call("memory.read_bytes", [address, 12])
    if not isinstance(value, str) or len(value) != 24:
        raise ValueError("unexpected vec3 hex response")
    try:
        x, y, z = struct.unpack(">fff", bytes.fromhex(value))
    except (ValueError, struct.error) as exc:
        raise ValueError("invalid vector response") from exc
    finite = all(math.isfinite(v) for v in (x, y, z))
    # Diagnostic bound, not a calibrated game-space bound.
    reasonable = finite and all(abs(v) < 1e6 for v in (x, y, z))
    return {"address": f"0x{address:08X}", "xyz_raw": [x, y, z] if finite else None,
            "finite": finite, "within_diagnostic_bound": reasonable,
            "status": "candidate_unverified" if finite else "nonfinite"}


def capture_spatial_rev1(rpc: Any) -> dict[str, Any]:
    """Read candidate +0x30 translation and +0x3C scale of map objects.

    Calls probe_rev1 first, which *refuses further reads* for game region /
    revision other than RSPE01 disc revision 1.
    """
    baseline = probe_rev1(rpc)
    output: dict[str, Any] = {
        "source": "US-Rev1-struct-hypotheses-read-only; NOT validated coordinates",
        "game_id": baseline["game_id"], "disc_revision": baseline["disc_revision"],
        "supported": baseline["supported"], "map_objects": {},
    }
    if not baseline["supported"]:
        output["warning"] = "unsupported game revision; no struct dereferences"
        return output
    golf = baseline["fields"].get("golf_config", {})
    mode = golf.get("raw_fields", {}).get("game_mode_raw", {}).get("value_hex")
    hole = golf.get("raw_fields", {}).get("hole_raw", {}).get("value_hex")
    output["game_mode_raw"] = mode
    output["current_hole_raw"] = hole
    output["mode_label"] = "GAMEMODE_TR_NEARPIN" if mode == "0x00000004" else "other_or_unknown"
    if mode != "0x00000004":
        output["warning"] = "not Hitting the Green according to game mode; spatial reads skipped"
        return output
    field = baseline["fields"].get("golf_field", {})
    if not field.get("plausible_mem_pointer", False):
        output["warning"] = "golf field instance pointer invalid"
        return output
    raw = field.get("raw_fields", {})
    for key in OBJECT_KEYS:
        value = raw.get(key, {}).get("value_hex")
        if not isinstance(value, str):
            continue
        obj = int(value, 16)
        item: dict[str, Any] = {"object_pointer": value}
        if not _valid_ptr(obj, 0x48):
            item["status"] = "null_or_invalid_map_object_pointer"
            output["map_objects"][key] = item
            continue
        item["inline_translation_offset_0x30"] = _read_vec3(rpc, obj + 0x30)
        # +0x3C..+0x47 contains all three float components of mScale.
        # The published +0x40/+0x44 pointer annotations overlap those
        # scale components, so do NOT interpret the last 1.0 float as a ptr.
        item["inline_scale_offset_0x3c"] = _read_vec3(rpc, obj + 0x3C)
        output["map_objects"][key] = item
    def relative(a: str, b: str) -> dict[str, Any] | None:
        """Hypothesis-only vector from object a toward object b in game units."""
        left = output["map_objects"].get(a, {}).get("inline_translation_offset_0x30", {}).get("xyz_raw")
        right = output["map_objects"].get(b, {}).get("inline_translation_offset_0x30", {}).get("xyz_raw")
        if left is None or right is None:
            return None
        delta = [float(v - u) for u, v in zip(left, right)]
        if not all(math.isfinite(v) for v in delta):
            return None
        return {
            "delta_xyz": delta,
            "horizontal_xz_distance": math.hypot(delta[0], delta[2]),
            "distance_3d": math.sqrt(sum(v * v for v in delta)),
            "units": "unverified_game_coordinates",
        }

    output["relative_geometry_unverified"] = {
        "start_to_pin": relative("current_start_obj_ptr", "current_pin_obj_ptr"),
        "cup_to_pin": relative("cup_obj_ptr", "current_pin_obj_ptr"),
    }
    output["warning"] = (
        "Likely inline object translations and scale, NOT calibrated meters. "
        "Published pointer annotations overlap scale (+0x3C..+0x47), so no "
        "translation-pointer dereferences are attempted. Verify geometry "
        "over repeated state changes and with visible game observations."
    )
    return output
