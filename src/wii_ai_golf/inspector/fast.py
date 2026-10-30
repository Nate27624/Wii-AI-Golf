"""Source-equivalent bounded batched reader for the read-only live inspector.

The canonical P0 packet issues one bridge RPC for each scalar word.  The Felk
bridge also supports `memory.read_bytes`, used here to reduce *round trips* for
contiguous word vectors, never to bypass any existing source/epoch checks.

This is deliberately inspector-local: no changes to archival collectors or
training/data provenance.  Neither a host-read bracket nor read_bytes makes
cross-object fields atomic game physics samples.
"""
from __future__ import annotations

import time


def packet(rpc, phase: str, index: int) -> dict:
    """Batched equivalent of p0_live_directional_aim_series.packet.

    Source/scene/Rev1 gates and before/after epoch checks are the same as the
    canonical live collector. Avoid shared caches across different addresses
    or gate points. Return the same identity, word names and metadata contract.
    """
    import p0_live_no_contact_compare as base
    import p0_live_directional_aim_series as source

    def block(address: int, count: int, bank: str | None = None) -> tuple[int, ...]:
        if type(address) is not int or type(count) is not int or not 1 <= count <= 51 or not base.in_bank(address, 4 * count, bank):
            raise ValueError("invalid bounded batched read address")
        response = rpc.call("memory.read_bytes", [address, 4 * count])
        if type(response) is not str or len(response) != count * 8:
            raise ValueError("malformed bounded batched read")
        try:
            payload = bytes.fromhex(response)
        except ValueError as exc:
            raise ValueError("invalid hex bounded batched read") from exc
        return tuple(int.from_bytes(payload[i:i+4], "big") for i in range(0, len(payload), 4))

    def word(addr: int) -> int:
        if not base.in_bank(addr):
            raise ValueError("invalid bounded scalar address")
        value = rpc.call("memory.read_u32", [addr])
        if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
            raise ValueError("invalid bounded scalar")
        return value

    def ptr(addr: int, bank: str, size: int = 4) -> int:
        if not base.in_bank(addr, size, bank):
            raise ValueError("invalid source object pointer")
        return addr

    def vec(addr: int) -> tuple[int, int, int]:
        ptr(addr, "MEM2", 12)
        result = block(addr, 3, "MEM2")
        return result  # type: ignore[return-value]

    start = time.monotonic_ns()
    before = rpc.call("frame.get_count", [])
    if type(before) is not int or before < 0:
        raise ValueError("invalid bridge frame bracket")
    header = rpc.call("memory.read_bytes", [0x80000000, 8])
    if type(header) is not str or len(header) != 16:
        raise ValueError("invalid revision header")
    try:
        sig = bytes.fromhex(header)
    except ValueError as exc:
        raise ValueError("invalid revision header") from exc
    if sig[:6] != b"RSPE01" or sig[7] != 1:
        raise ValueError("not Wii Sports USA Rev1")

    mgr = ptr(word(base.SCENE_STATIC), "MEM1", 0x20)
    if word(base.SCENE_STATIC + 4) != 0 or word(mgr + 0x18) != 5:
        raise ValueError("not active Golf scene")
    scene = ptr(word(mgr + 0xC), "MEM2", 0xA0)
    if (word(scene + 0x1C) != 5 or word(scene + 0x20) != mgr or word(scene + 0x54) != 2
            or not 0x803C7718 <= word(scene) < 0x803C7798):
        raise ValueError("scene source/owner mismatch")
    config = ptr(word(base.CONFIG_STATIC), "MEM2", 0x9C)
    field = ptr(word(base.FIELD_STATIC), "MEM2", 0xA8)
    if word(config + 0x94) != 4:
        raise ValueError("not Hitting-the-Green mode 4")
    hole = word(config + 0x98)
    if hole > 8:
        raise ValueError("invalid hole index")
    pm = ptr(word(base.PLAYER_MANAGER_STATIC), "MEM2", 0x33C)
    if not 0x803C7DD0 <= word(pm) < 0x803C7DE0:
        raise ValueError("source player-manager type mismatch")
    selector = word(pm + 0x334)
    selected = [i for i in range(4) if selector == pm + 4 + i * base.STRIDE]
    if len(selected) != 1:
        raise ValueError("ambiguous selected player")
    record = ptr(selector, "MEM2", base.STRIDE)
    ball = ptr(word(record + 0x88), "MEM2", 0x120)
    if not 0x803C7918 <= word(ball) < 0x803C7A50:
        raise ValueError("selected ball type mismatch")
    translation = ptr(word(ball + 0x4C), "MEM2", 12)
    start_obj = ptr(word(field + 0x50), "MEM2", 0x50)
    pin = ptr(word(field + 0x44), "MEM2", 0x50)
    start_vec = ptr(word(start_obj + 0x4C), "MEM2", 12)
    pin_vec = ptr(word(pin + 0x4C), "MEM2", 12)
    values = {
        "selected_nested_plus_0x4c": vec(translation),
        "selected_ball_plus_0x30": vec(ball + 0x30),
        "selected_ball_cache_plus_0xcc": vec(ball + 0xCC),
        "selected_ball_cache_plus_0xf0": vec(ball + 0xF0),
        "selected_ball_cache_plus_0xfc": vec(ball + 0xFC),
        "record_initial_plus_0x54": vec(record + 0x54),
        "record_start_copy_plus_0x60": vec(record + 0x60),
        "tee_start_candidate": vec(start_vec),
        "pin_candidate": vec(pin_vec),
        "aim_candidate_plus_0x3c": (word(record + 0x3C),),
    }
    after = rpc.call("frame.get_count", [])
    if type(after) is not int or after < before:
        raise ValueError("invalid bridge frame order")
    identity = (mgr, scene, config, field, pm, selected[0], record, ball, translation,
                start_obj, start_vec, pin, pin_vec, hole)
    # The two extra 3-component probes match the canonical directional reader.
    extra = {
        "selected_record_plus_0x30": vec(record + 0x30),
        "selected_record_plus_0x90": vec(record + 0x90),
    }
    # Independently revalidate every source link *after* all candidate reads.
    if not source.end_epoch_matches(rpc, identity):
        raise ValueError("intra-packet scene/owner/ball/tee/pin identity changed")
    end_frame = rpc.call("frame.get_count", [])
    if type(end_frame) is not int or end_frame < after:
        raise ValueError("invalid bridge ordering")
    end = time.monotonic_ns()
    return {"phase": phase, "index": index, "start_ns": start, "end_ns": end,
            "frame_bracket": (before, end_frame), "identity": identity,
            "words": {**values, **extra}}
