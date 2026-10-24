"""Read-only, source-constrained Wii Sports US Rev1 outcome discovery.

These RAM windows are exploratory evidence, NOT identified ball-position or
Hitting-the-Green score fields. The data-gathering session must be launched
with the canonical emulator+pre-start intro before invoking this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import struct
from typing import Any

# Static-instance pointer symbols documented by kiwi515/ogws_info for US Rev1.
# The chosen bounded windows are exploratory; they are not decoded score fields.
STATIC_STRUCTS = {
    "golf_config": (0x804BF8C4, 0x1C74),
    "golf_field": (0x804BF868, 0xA8),
    "sports_sequence": (0x804BF708, 0xD0),
}
EFFECT_POINTER_OFFSETS = {
    "minimap_ball_effect": 0x9C,
    "minimap_player_effect": 0x94,
    "minimap_shot_line_effect": 0x98,
}
EFFECT_BYTES = 0x200
MAX_SAMPLE_BYTES = 12 * 1024
CHUNK_BYTES = 1024


def _ram(address: int, length: int) -> bool:
    return type(address) is int and address % 4 == 0 and length > 0 and (
        (0x80000000 <= address and address + length <= 0x81800000)
        or (0x90000000 <= address and address + length <= 0x94000000)
    )


def _u32(rpc: Any, address: int) -> int:
    result = rpc.call("memory.read_u32", [address])
    if type(result) is not int or not 0 <= result <= 0xFFFFFFFF:
        raise ValueError("invalid u32 RPC result")
    return result


def _bytes(rpc: Any, address: int, length: int) -> bytes:
    if not _ram(address, length):
        raise ValueError("invalid bounded Wii RAM region")
    output = bytearray()
    for offset in range(0, length, CHUNK_BYTES):
        n = min(CHUNK_BYTES, length - offset)
        data = rpc.call("memory.read_bytes", [address + offset, n])
        if not isinstance(data, str) or len(data) != 2 * n:
            raise ValueError("unexpected memory.read_bytes response length")
        try:
            output.extend(bytes.fromhex(data))
        except ValueError as exc:
            raise ValueError("invalid hexadecimal memory response") from exc
    return bytes(output)


def capture_outcome_windows(rpc: Any, phase: str) -> dict[str, Any]:
    """One bounded sample; rejects wrong disc revision and training mode.

    No savestate operations, controller writes or arbitrary user RAM ranges.
    Multi-frame snapshot spans are recorded so samples cannot be called atomic.
    """
    if phase not in ("pre", "post", "settled"):
        raise ValueError("invalid observation phase")
    frame_start = rpc.call("frame.get_count", [])
    if type(frame_start) is not int or frame_start < 0:
        raise ValueError("invalid frame start")
    header = _bytes(rpc, 0x80000000, 8)
    if header[:6] != b"RSPE01" or header[7] != 1:
        raise RuntimeError("Only Wii Sports USA revision 1 (RSPE01, rev byte 1) is supported")

    ptrs = {name: _u32(rpc, pointer_at)
            for name, (pointer_at, _size) in STATIC_STRUCTS.items()}
    for name, (_pointer_at, size) in STATIC_STRUCTS.items():
        if not _ram(ptrs[name], size):
            raise RuntimeError(f"Missing or invalid {name} instance pointer")
    mode = _u32(rpc, ptrs["golf_config"] + 0x94)
    if mode != 4:
        raise RuntimeError("Game not in Hitting the Green training mode (RPGolConfig mode 4)")

    regions = {name: (ptrs[name], size)
               for name, (_pointer_at, size) in STATIC_STRUCTS.items()}
    field = ptrs["golf_field"]
    for name, off in EFFECT_POINTER_OFFSETS.items():
        ptr = _u32(rpc, field + off)
        if _ram(ptr, EFFECT_BYTES):
            regions[name] = (ptr, EFFECT_BYTES)
    if sum(size for _ptr, size in regions.values()) > MAX_SAMPLE_BYTES:
        raise RuntimeError("outcome snapshot would exceed 12 KiB per sample")
    windows = {}
    for name, (ptr, size) in regions.items():
        windows[name] = {"address": f"0x{ptr:08X}", "bytes_hex": _bytes(rpc, ptr, size).hex()}
    frame_end = rpc.call("frame.get_count", [])
    if type(frame_end) is not int or frame_end < frame_start:
        raise ValueError("invalid frame end")
    return {
        "schema_version": 1, "source": "Felk-read-only-US-Rev1-unverified-golf-windows",
        "phase": phase, "utc": datetime.now(timezone.utc).isoformat(),
        "game_id": "RSPE01", "disc_revision": 1, "game_mode_raw": mode,
        "frame_start": frame_start, "frame_end": frame_end,
        "non_atomic_frame_span": frame_end - frame_start,
        "windows": windows, "bytes_read": sum(size for _addr, size in regions.values()),
        "warning": "not an authoritative ball XYZ, landing, score, or hit detector",
    }


def _words(sample: dict[str, Any]) -> dict[int, tuple[int, set[str]]]:
    """Big-endian word-aligned addresses, deduplicated across overlapping windows."""
    if sample.get("game_id") != "RSPE01" or sample.get("disc_revision") != 1:
        raise ValueError("invalid game identification in snapshot")
    result: dict[int, tuple[int, set[str]]] = {}
    for window, data in sample.get("windows", {}).items():
        if window not in (set(STATIC_STRUCTS) | set(EFFECT_POINTER_OFFSETS)):
            continue
        if not isinstance(data, dict):
            raise ValueError("invalid window structure")
        base = int(data["address"], 16)
        raw = bytes.fromhex(data["bytes_hex"])
        if not _ram(base, len(raw)) or len(raw) > MAX_SAMPLE_BYTES:
            raise ValueError("malformed capture region")
        for offset in range(0, len(raw) - 3, 4):
            address = base + offset
            value = struct.unpack_from(">I", raw, offset)[0]
            if address in result:
                if result[address][0] != value:
                    raise ValueError("same absolute memory address had conflicting window values")
                result[address][1].add(window)
            else:
                result[address] = (value, {window})
    return result


def _variants(bits: int) -> dict[str, Any]:
    f = struct.unpack(">f", struct.pack(">I", bits))[0]
    signed = bits if bits < 0x80000000 else bits - 0x100000000
    return {"u32": bits, "s32": signed, "f32": round(f, 5) if math.isfinite(f) else None}


def rank_outcome_candidates(samples: list[dict[str, Any]], *,
                            human_distance: float | None = None,
                            tolerance: float = 0.1,
                            top_n: int = 80) -> dict[str, Any]:
    """Find stable pre-shot and stable settled persistent raw RAM differences.

    This does not identify an official training score or confirm ball landing.
    """
    if type(top_n) is not int or not 1 <= top_n <= 500:
        raise ValueError("top_n must be between 1 and 500")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and nonnegative")
    if human_distance is not None and (type(human_distance) not in (float, int)
                                       or not math.isfinite(human_distance)
                                       or human_distance < 0):
        raise ValueError("human distance must be finite and nonnegative")
    phases = [s.get("phase") for s in samples]
    npre, npost, nsettled = phases.count("pre"), phases.count("post"), phases.count("settled")
    if npre < 2 or nsettled < 2 or any(p not in ("pre", "post", "settled") for p in phases):
        raise ValueError("require >=2 pre and >=2 settled observations")
    if phases != sorted(phases, key={"pre": 0, "post": 1, "settled": 2}.get):
        raise ValueError("observations must be chronological pre/post/settled")
    rows = [_words(sample) for sample in samples]
    masks = {phase: [r for sample, r in zip(samples, rows) if sample["phase"] == phase]
             for phase in ("pre", "post", "settled")}
    common = set.intersection(*(set(row) for row in rows)) if rows else set()
    ranked = []
    for address in sorted(common):
        first = [row[address][0] for row in masks["pre"]]
        last = [row[address][0] for row in masks["settled"]]
        if len(set(first)) != 1 or len(set(last)) != 1 or first[0] == last[0]:
            continue
        post = [row[address][0] for row in masks["post"]]
        provenance = sorted(set.union(*(row[address][1] for row in rows)))
        before, after = _variants(first[0]), _variants(last[0])
        match = []
        if human_distance is not None:
            for kind in ("f32", "u32", "s32"):
                actual = after[kind]
                if actual is not None and abs(actual - human_distance) <= tolerance:
                    match.append(kind)
        ranked.append({
            "address": f"0x{address:08X}", "windows": provenance,
            "before": before, "settled": after,
            "post_distinct_values": len(set(post)),
            "post_samples_differing_from_pre": sum(x != first[0] for x in post),
            "matches_displayed_numeric_label_as": match,
            "status": "unverified_persistent_ram_change_NOT_game_score_or_ball_xyz",
        })
    ranked.sort(key=lambda v: (-bool(v["matches_displayed_numeric_label_as"]),
                               -v["post_samples_differing_from_pre"],
                               -v["post_distinct_values"], v["address"]))
    return {
        "schema_version": 1, "pre_samples": npre, "post_samples": npost,
        "settled_samples": nsettled, "sample_count": len(samples),
        "all_phase_stable_change_count": len(ranked),
        "candidates_truncated": len(ranked) > top_n,
        "candidates": ranked[:top_n],
        "human_displayed_distance_raw_unverified": human_distance,
        "human_label_tolerance_no_unit_conversion": tolerance,
        "ball_position_verified": False, "game_score_verified": False,
        "warning": ("Big-endian u32/s32/f32 raw changes; a numeric match may be "
                    "coincidental. Multi-frame snapshots and unknown display units "
                    "prevent inferring exact landing, true power or game score."),
    }
