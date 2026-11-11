"""Opt-in source-gated selected-ball memory watch in existing Felk frame loop.

This adds NO controller calls or concurrent RPC writer. It never alters the
canonical swing trace. Only the local operator can arm and drain it; raw numeric
candidate vectors must remain in ignored Wii-AI-Golf-Data, never GitHub.
"""
from __future__ import annotations

from .atomic_patch import PATCH_MARKER
from .swing_patch import SWING_NEUTRAL_V2_MARKER

BALL_WATCH_MARKER = "# WII_AI_GOLF_SELECTED_BALL_WATCH_V1"

_BALL_WATCH_HANDLER = '''# WII_AI_GOLF_SELECTED_BALL_WATCH_V1
import math as _wii_ball_math
import struct as _wii_ball_struct
import time as _wii_ball_time

_wii_ball_watch = None
_wii_ball_watch_last = {"state": "idle"}
_wii_ball_watch_samples = []
_WII_BALL_MEM2_LOW, _WII_BALL_MEM2_HIGH = 0x90000000, 0x94000000


def _wii_ball_m2(address, length=4):
    return (type(address) is int and address % 4 == 0
            and _WII_BALL_MEM2_LOW <= address
            and address + length <= _WII_BALL_MEM2_HIGH)


def _wii_ball_u32(address):
    return memory.read_u32(address)


def _wii_ball_vec(address):
    if not _wii_ball_m2(address, 12):
        raise ValueError("unmapped source-backed candidate vector")
    values = []
    for d in (0, 4, 8):
        word = _wii_ball_u32(address + d)
        if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
            raise ValueError("invalid source word")
        value = _wii_ball_struct.unpack(">f", _wii_ball_struct.pack(">I", word))[0]
        if not _wii_ball_math.isfinite(value) or abs(value) > 100000:
            raise ValueError("implausible vector component")
        values.append(value)
    return values


def _wii_ball_snapshot():
    # Fail-closed RSPE01 Rev1 memory source-layout gates. No heap addresses
    # or raw pointer values are returned outside this function.
    if (_wii_ball_u32(0x80000000) != 0x52535045
            or _wii_ball_u32(0x80000004) != 0x30310001):
        raise ValueError("RSPE01 Rev1 header mismatch")
    manager = _wii_ball_u32(0x804BF4D8)
    if not (0x80000000 <= manager < 0x81800000
            and _wii_ball_u32(manager + 0x18) == 5):
        raise ValueError("scene manager source gate")
    scene = _wii_ball_u32(manager + 0x0C)
    if not (_wii_ball_m2(scene, 0xA0)
            and _wii_ball_u32(scene + 0x1C) == 5
            and _wii_ball_u32(scene + 0x20) == manager
            and _wii_ball_u32(scene + 0x54) == 2):
        raise ValueError("golf scene source gate")
    config = _wii_ball_u32(0x804BF8C4)
    if not (_wii_ball_m2(config, 0xA0)
            and _wii_ball_u32(config + 0x94) == 4):
        raise ValueError("training mode source gate")
    hole = _wii_ball_u32(config + 0x98)
    if type(hole) is not int or not 0 <= hole <= 8:
        raise ValueError("current-hole range gate")
    field = _wii_ball_u32(0x804BF868)
    pm = _wii_ball_u32(0x804BF8D0)
    if not (_wii_ball_m2(field, 0x90) and _wii_ball_m2(pm, 0x340)
            and 0x803C7DD0 <= _wii_ball_u32(pm) < 0x803C7DE0):
        raise ValueError("field/player manager source gate")
    selected_record = _wii_ball_u32(pm + 0x334)
    slot = next((i for i in range(4)
                 if selected_record == pm + 4 + 0xCC * i), None)
    if slot is None:
        raise ValueError("source-gated selected record missing")
    ball = _wii_ball_u32(selected_record + 0x88)
    if not (_wii_ball_m2(ball, 0x50)
            and 0x803C7918 <= _wii_ball_u32(ball) < 0x803C7A50):
        raise ValueError("selected ball candidate missing")
    ball_vector_pointer = _wii_ball_u32(ball + 0x4C)
    if ball_vector_pointer != ball + 0x30:
        raise ValueError("ball translation self-reference changed")
    start = _wii_ball_u32(field + 0x50)
    if not _wii_ball_m2(start, 0x50):
        raise ValueError("start object missing")
    if (_wii_ball_u32(start + 0x4C) != start + 0x30
            or _wii_ball_u32(start + 0x48) != start + 0x0C):
        raise ValueError("start object base layout changed")

    t = _wii_ai_trace
    index = (_frame_count - t["start"]) if t is not None else None
    if type(index) is not int or index < 0 or index >= len(t["samples"]):
        index = None
    return {
        "frame_tick_index": _frame_count,
        "trace_id_if_active": t["id"] if index is not None else None,
        "trace_sample_index_if_active": index,
        "selected_slot_candidate": slot,
        "source_hole_index": hole,
        "ball_translation_f32_candidate": _wii_ball_vec(ball_vector_pointer),
        "record_translation_f32_candidate": _wii_ball_vec(selected_record + 0x54),
        "current_start_f32_candidate": _wii_ball_vec(start + 0x30),
        # Identity categories only; no runtime addresses enter the report.
        "source_owner_consistent": True,
        # Never leave this private tuple in RPC samples; tracked in-memory
        # solely to detect reallocation/scene transitions across ticks.
        "_source_owner_tuple": (manager, scene, config, field, pm,
                                selected_record, ball, ball_vector_pointer,
                                start),
    }


def _wii_ball_watch_arm(p):
    global _wii_ball_watch, _wii_ball_watch_last, _wii_ball_watch_samples
    if _wii_ball_watch is not None:
        raise RuntimeError("ball watch already active")
    if _wii_ai_trace is not None:
        raise RuntimeError("arm before scheduling the known-good swing")
    if not isinstance(p, list) or len(p) != 2:
        raise ValueError("arm expects duration_frames and interval_frames")
    duration, interval = p
    if (type(duration) is not int or type(interval) is not int
            or not 24 <= duration <= 320 or not 2 <= interval <= 12
            or (duration + interval - 1) // interval > 80):
        raise ValueError("bounded watch requires at most 80 samples")
    _wii_ball_watch_samples = []
    _wii_ball_watch = {"start": _frame_count + 1,
                       "end": _frame_count + duration,
                       "interval": interval, "max_read_us": 0,
                       "stage": "idle_control", "source_owner_tuple": None}
    _wii_ball_watch_last = {"state": "armed", "samples": 0,
                           "requested_duration_frames": duration,
                           "interval_frames": interval,
                           "frame_count_source": "bridge_coroutine_tick_only"}
    return dict(_wii_ball_watch_last)


def _wii_ball_watch_stage(p):
    if (_wii_ball_watch is None or not isinstance(p, list)
            or len(p) != 1 or type(p[0]) is not str):
        raise ValueError("stage requires one active watch and one phase")
    current = _wii_ball_watch["stage"]
    successors = {
        "idle_control": "a_prime",
        "a_prime": "trace",
        "trace": "posttrace",
    }
    if p[0] != successors.get(current):
        raise ValueError("watch phase must advance exactly once in order")
    _wii_ball_watch["stage"] = p[0]
    return {"stage": p[0], "state": "recording_or_armed"}


def _wii_ball_watch_tick():
    """Single owner; called BEFORE the existing motion dispatch once per tick.

    Never calls a controller, network, file I/O or an extra RPC. A read after
    frameadvance but before controller dispatch is NOT proof of game-applied A.
    """
    global _wii_ball_watch, _wii_ball_watch_last
    cfg = _wii_ball_watch
    if cfg is None or _frame_count < cfg["start"]:
        return
    if _frame_count > cfg["end"] or len(_wii_ball_watch_samples) >= 80:
        _wii_ball_watch = None
        _wii_ball_watch_last = {"state": "complete",
                                "samples": len(_wii_ball_watch_samples),
                                "max_read_us": cfg["max_read_us"]}
        return
    if (_frame_count - cfg["start"]) % cfg["interval"] != 0:
        return
    before = _wii_ball_time.perf_counter()
    try:
        sample = _wii_ball_snapshot()
        owner = sample.pop("_source_owner_tuple")
        if cfg["source_owner_tuple"] is None:
            cfg["source_owner_tuple"] = owner
        elif cfg["source_owner_tuple"] != owner:
            raise ValueError("selected object ownership changed mid-study")
        sample["input_stage"] = cfg["stage"]
    except Exception:
        _wii_ball_watch = None
        _wii_ball_watch_last = {"state": "source_gate_failed",
                                "samples": len(_wii_ball_watch_samples),
                                "warning": "No vector/heap values released after gate failure"}
        return
    read_us = int((_wii_ball_time.perf_counter() - before) * 1000000)
    cfg["max_read_us"] = max(cfg["max_read_us"], read_us)
    sample["read_overhead_us"] = read_us
    _wii_ball_watch_samples.append(sample)
    if read_us > 5000:
        _wii_ball_watch = None
        _wii_ball_watch_last = {"state": "read_overhead_exceeded",
                                "samples": len(_wii_ball_watch_samples),
                                "max_read_us": read_us}
    else:
        _wii_ball_watch_last = {"state": "recording",
                                "samples": len(_wii_ball_watch_samples),
                                "max_read_us": cfg["max_read_us"]}


def _wii_ball_watch_status(_p):
    return dict(_wii_ball_watch_last)


def _wii_ball_watch_drain(p):
    global _wii_ball_watch, _wii_ball_watch_samples, _wii_ball_watch_last
    if p:
        raise ValueError("drain takes no parameters")
    if _wii_ball_watch_last.get("state") != "complete":
        raise RuntimeError("refuse partial or failed watched capture")
    result = {"status": dict(_wii_ball_watch_last),
              "samples": list(_wii_ball_watch_samples),
              "values_are_unverified_ball_translation_candidates": True,
              "emulated_guest_frame_or_contact_proven": False,
              "training_allowed": False}
    _wii_ball_watch = None
    _wii_ball_watch_samples = []
    _wii_ball_watch_last = {"state": "idle"}
    return result


'''


class BallWatchPatchError(RuntimeError):
    """Refuse an unfamiliar source bridge or an already-watched bridge."""


def extend_swing_bridge_with_ball_watch(source: str) -> str:
    """Generate a NEW bridge source, never patch a running bridge in place."""
    if (PATCH_MARKER not in source or SWING_NEUTRAL_V2_MARKER not in source
            or BALL_WATCH_MARKER in source):
        raise BallWatchPatchError("Expected unmodified pinned Swing V2 bridge")
    patches = (
        ("HANDLERS = {", _BALL_WATCH_HANDLER + "HANDLERS = {"),
        ('    "trace.swing_capabilities": _wii_ai_swing_capabilities,',
         '    "trace.swing_capabilities": _wii_ai_swing_capabilities,\n'
         '    "golf.ball_watch.arm": _wii_ball_watch_arm,\n'
         '    "golf.ball_watch.stage": _wii_ball_watch_stage,\n'
         '    "golf.ball_watch.status": _wii_ball_watch_status,\n'
         '    "golf.ball_watch.drain": _wii_ball_watch_drain,'),
        ("    _wii_ai_tick()\n    _poll_sockets()",
         "    _wii_ball_watch_tick()\n    _wii_ai_tick()\n    _poll_sockets()"),
    )
    for old, new in patches:
        if source.count(old) != 1:
            raise BallWatchPatchError("Unexpected pinned generated-bridge anchor")
        source = source.replace(old, new, 1)
    return source
