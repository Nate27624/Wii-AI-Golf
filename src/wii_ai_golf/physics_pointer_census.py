"""Source-gated pointer census for Wii Sports golf ball-object discovery.

Every pointer remains HYPOTHETICAL, even if motion-correlated.
Only read existing bounded game RAM, never patch/write memory.
"""
from __future__ import annotations
import math
import struct
from typing import Any

from .symbol_probe import probe_rev1

# Starting objects are decompilation-documented fields, not ball physics.
ROOT_NAMES = ("golf_config", "golf_field", "sports_sequence")
RAM = ((0x80000000, 0x81800000), (0x90000000, 0x94000000))
ROOT_BYTES = 0xA8
OBJECT_BYTES = 0x80
MAX_POINTERS = 16
MAX_ROUND_BYTES = 4096


def valid_mem(address: int, length: int) -> bool:
    return type(address) is int and address % 4 == 0 and length > 0 and any(
        lo <= address and address + length <= hi for lo, hi in RAM)


def read_bytes(rpc: Any, address: int, size: int) -> bytes:
    if size > OBJECT_BYTES or not valid_mem(address, size):
        raise ValueError("invalid bounded pointer-census RAM address/size")
    value = rpc.call("memory.read_bytes", [address, size])
    if not isinstance(value, str) or len(value) != 2 * size:
        raise ValueError("invalid pointer-census byte response")
    raw = bytes.fromhex(value)
    if len(raw) != size:
        raise ValueError("invalid pointer-census hex response")
    return raw


def discover_roots(rpc: Any) -> dict[str, int]:
    info = probe_rev1(rpc)
    if not info.get("supported"):
        raise RuntimeError("pointer census requires verified RSPE01 revision 1 header")
    mode = info["fields"]["golf_config"]["raw_fields"]["game_mode_raw"]["value_hex"]
    if mode != "0x00000004":
        raise RuntimeError("pointer census requires Hitting the Green mode 4")
    roots = {}
    for name in ROOT_NAMES:
        item = info["fields"][name]
        if item["plausible_mem_pointer"]:
            ptr = int(item["instance_pointer"],16)
            if valid_mem(ptr, OBJECT_BYTES):
                roots[name] = ptr
    if "golf_field" not in roots:
        raise RuntimeError("golf field manager unavailable")
    return roots


def find_pointer_candidates(rpc: Any, roots: dict[str, int],
                            max_pointers: int = MAX_POINTERS) -> list[dict[str, Any]]:
    """One level of aligned, bounded pointers; no arbitrary recursive walking."""
    if not 1 <= max_pointers <= MAX_POINTERS:
        raise ValueError("max_pointers outside safe budget")
    seen = set(roots.values())
    found = []
    for owner, ptr in sorted(roots.items()):
        raw = read_bytes(rpc, ptr, OBJECT_BYTES)
        for off in range(0, OBJECT_BYTES, 4):
            target = struct.unpack_from(">I",raw,off)[0]
            if not valid_mem(target, OBJECT_BYTES) or target in seen:
                continue
            seen.add(target)
            found.append({"owner":owner,"owner_offset":f"+0x{off:X}",
                          "address":f"0x{target:08X}",
                          "status":"UNVERIFIED_ONE_HOP_POINTER_NOT_A_BALL"})
            if len(found) >= max_pointers:
                return found
    return found


def capture(rpc: Any, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if len(candidates)>MAX_POINTERS:
        raise ValueError("pointer count exceeds limit")
    start=rpc.call("frame.get_count")
    if type(start) is not int or start<0:
        raise ValueError("invalid start frame")
    result=[]
    seen=set()
    for row in candidates:
        addr=int(row["address"],16)
        if addr in seen:
            continue
        seen.add(addr)
        raw=read_bytes(rpc,addr,OBJECT_BYTES)
        result.append({"address":row["address"],"bytes_hex":raw.hex()})
    end=rpc.call("frame.get_count")
    if type(end) is not int or end<start:
        raise ValueError("invalid end frame")
    return {"frame_start":start,"frame_end":end,"frame_span":end-start,
            "objects":result}


def analyze(captures: list[dict[str, Any]]) -> dict[str, Any]:
    """Rank object-local aligned floats by consecutive-sample change."""
    observed={}
    for index,capture_row in enumerate(captures):
        for obj in capture_row.get("objects",[]):
            base=int(obj["address"],16)
            raw=bytes.fromhex(obj["bytes_hex"])
            for off in range(0,len(raw)-11,4):
                vec=struct.unpack_from(">fff",raw,off)
                if all(math.isfinite(n) and abs(n)<100000 for n in vec):
                    observed.setdefault((base,off),[]).append((index,vec))
    out=[]
    for (base,off),records in observed.items():
        steps=[math.dist(a[1],b[1]) for a,b in zip(records,records[1:]) if b[0]==a[0]+1]
        changed=sum(v>=0.1 for v in steps)
        if changed < 2:continue
        first,last=records[0][1],records[-1][1]
        out.append({"address":f"0x{base+off:08X}","base":f"0x{base:08X}",
                    "offset":f"+0x{off:X}","changes":changed,
                    "first":[round(v,4) for v in first],
                    "last":[round(v,4) for v in last],
                    "status":"UNVERIFIED_VEC3_NOT_BALL"})
    out.sort(key=lambda v:(-v["changes"],v["address"]))
    return {"samples":len(captures),"candidates_total":len(out),
            "candidates":out[:30],"warning":"Only one-hop memory candidates, not decoded ball physics"}
