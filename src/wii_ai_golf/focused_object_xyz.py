"""Focused, source-gated read-only probe for the leading one-hop golf object.

NOT verified as the ball. No absolute RAM address is hardcoded: resolve
golf_field instance and field +0x04 on every observation. No writes.
"""
from __future__ import annotations
import math
import struct
from typing import Any
from .symbol_probe import probe_rev1
from .physics_pointer_census import valid_mem, read_bytes

OWNER_OFFSET = 0x04  # observed one-hop field on 20261024T232725Z-b034328d
VEC_OFFSET = 0x50   # largest dynamic aligned vec3 in that object's first 128B


def preflight(rpc: Any) -> int:
    info = probe_rev1(rpc)
    if not info.get("supported"):
        raise RuntimeError("focused probe requires Wii Sports RSPE01 disc revision 1")
    field = info.get("fields", {}).get("golf_field", {})
    mode = (info.get("fields", {}).get("golf_config", {})
            .get("raw_fields", {}).get("game_mode_raw", {}).get("value_hex"))
    if mode != "0x00000004" or not field.get("plausible_mem_pointer"):
        raise RuntimeError("focused probe requires Hitting the Green mode 4")
    root = int(field["instance_pointer"], 16)
    if not valid_mem(root + OWNER_OFFSET, 4):
        raise RuntimeError("invalid golf field root pointer")
    return root


def observe(rpc: Any, root: int) -> dict[str, Any]:
    """One pointer read + 12 bytes + two frame reads, on a persistent connection."""
    start = rpc.call("frame.get_count")
    if type(start) is not int or start < 0:
        raise ValueError("invalid frame start")
    ptr = rpc.call("memory.read_u32", [root + OWNER_OFFSET])
    if not valid_mem(ptr, VEC_OFFSET + 12):
        raise RuntimeError("dynamic golf object pointer invalidated; stop recording")
    raw = read_bytes(rpc, ptr + VEC_OFFSET, 12)
    xyz = struct.unpack(">fff", raw)
    if not all(math.isfinite(x) and abs(x) < 100000 for x in xyz):
        raise RuntimeError("nonfinite/implausible object coordinates")
    end = rpc.call("frame.get_count")
    if type(end) is not int or end < start:
        raise ValueError("invalid frame end")
    return {"object_base": f"0x{ptr:08X}", "vec_address": f"0x{ptr+VEC_OFFSET:08X}",
            "xyz": [round(x, 6) for x in xyz], "frame_start": start,
            "frame_end": end, "frame_span": end-start}


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for sample in samples:
        groups.setdefault(sample["object_base"], []).append(sample)
    results = []
    for base, rows in groups.items():
        consecutive = [(a,b) for a,b in zip(rows,rows[1:])
                       if b["frame_start"] >= a["frame_end"]]
        changes = [math.dist(a["xyz"],b["xyz"]) for a,b in consecutive]
        moves = [v for v in changes if v >= 0.1]
        results.append({"object_base":base,"observations":len(rows),
                        "moving_steps":len(moves),
                        "max_step_displacement_unverified":round(max(changes,default=0),4),
                        "first_xyz":rows[0]["xyz"],"last_xyz":rows[-1]["xyz"]})
    return {"sample_count":len(samples),"object_instances":results,
            "status":"UNVERIFIED_object_movement_NOT_confirmed_ball_physics"}
