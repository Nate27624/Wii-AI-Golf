"""Read-only narrowly targeted Wii Sports US Rev1 motion sampling.

Hypothesis-only: no ball or score memory location has been verified.
Reads <= 128 bytes per sample; source-gated once before collection.
"""
from __future__ import annotations

import math
import struct
from typing import Any

from .symbol_probe import probe_rev1

# Persistent minimap effect pointers are only hints from decompiled structs.
# Track local effect transforms, not physical ball by assumption.
OFFSETS = {"minimap_ball_eff_ptr": 0x9C,
           "minimap_player_eff_ptr": 0x94,
           "minimap_shot_line_eff_ptr": 0x98}
MAX_BYTES = 128


def read_hex(rpc: Any, address: int, count: int) -> bytes:
    if not (0x80000000 <= address and address+count <= 0x81800000 or
            0x90000000 <= address and address+count <= 0x94000000):
        raise ValueError("read outside MEM1/MEM2")
    if not 1 <= count <= MAX_BYTES:
        raise ValueError("targeted read must be 1..128 bytes")
    result = rpc.call("memory.read_bytes", [address, count])
    if not isinstance(result, str) or len(result) != count*2:
        raise ValueError("invalid targeted hex")
    raw = bytes.fromhex(result)
    if len(raw) != count:
        raise ValueError("invalid targeted byte count")
    return raw


def preflight(rpc: Any) -> dict[str, Any]:
    info = probe_rev1(rpc)
    if not info["supported"]:
        raise RuntimeError("targeted scan requires Wii Sports RSPE01 revision 1")
    field = info["fields"]["golf_field"]
    mode = info["fields"]["golf_config"]["raw_fields"]["game_mode_raw"]["value_hex"]
    if mode != "0x00000004" or not field["plausible_mem_pointer"]:
        raise RuntimeError("targeted scan requires live Hitting the Green game mode")
    fieldaddr = int(field["instance_pointer"],16)
    pointers = {}
    for name, offset in OFFSETS.items():
        ptr = rpc.call("memory.read_u32", [fieldaddr+offset])
        if type(ptr) is int and ptr % 4 == 0 and (
            0x80000000 <= ptr < 0x817FFF80 or 0x90000000 <= ptr < 0x93FFFF80):
            pointers[name] = ptr
    if not pointers:
        raise RuntimeError("no valid minimap effect pointers")
    return {"game_id": info["game_id"], "disc_revision": info["disc_revision"],
            "mode_raw": mode, "sources": pointers}


def capture_one(rpc: Any, sources: dict[str, int],
                *, offset: int = 0x30, length: int = 64) -> dict[str, Any]:
    """Frame-bracketed narrow reads; one TCP connection reused between samples."""
    if offset < 0 or offset % 4 or length < 4 or length > MAX_BYTES or length % 4:
        raise ValueError("offset/length require aligned bounded values")
    before = rpc.call("frame.get_count")
    if type(before) is not int or before < 0:
        raise ValueError("bad starting frame count")
    windows = {}
    seen = {}
    for name, base in sources.items():
        address = base + offset
        if address not in seen:
            raw = read_hex(rpc, address, length)
            seen[address] = raw
        else:
            raw = seen[address]
        windows[name] = {"address": f"0x{address:08X}", "bytes_hex": raw.hex()}
    after = rpc.call("frame.get_count")
    if type(after) is not int or after < before:
        raise ValueError("bad ending frame count")
    return {"frame_start": before, "frame_end": after, "frame_span": after-before,
            "windows": windows}


def analyze(captures: list[dict[str, Any]]) -> dict[str, Any]:
    """Deduplicated aligned float changes; never claim a score or ball identity."""
    by_address: dict[int, list[tuple[int, tuple[float, float, float]]]] = {}
    for i, capture in enumerate(captures):
        seen: set[int] = set()
        for window in capture.get("windows", {}).values():
            base = int(window["address"],16)
            raw = bytes.fromhex(window["bytes_hex"])
            for offset in range(0,len(raw)-11,4):
                addr=base+offset
                if addr in seen: continue
                seen.add(addr)
                xyz=struct.unpack_from(">fff",raw,offset)
                if all(math.isfinite(v) and abs(v)<100000 for v in xyz):
                    by_address.setdefault(addr,[]).append((i,xyz))
    out=[]
    for addr,entries in by_address.items():
        pairs=[(a,b) for a,b in zip(entries,entries[1:]) if b[0]==a[0]+1]
        changes=sum(math.dist(a[1],b[1])>=0.1 for a,b in pairs)
        if changes>=2:
            out.append({"address": f"0x{addr:08X}", "changed_steps":changes,
                        "samples":len(entries),
                        "first_xyz":[round(v,4) for v in entries[0][1]],
                        "last_xyz":[round(v,4) for v in entries[-1][1]]})
    out.sort(key=lambda x:(-x["changed_steps"],x["address"]))
    return {"sample_count":len(captures), "candidate_count":len(out),
            "candidates":out[:20], "status":"unverified_render_effect_hypotheses_not_ball_position"}
