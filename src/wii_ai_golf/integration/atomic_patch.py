"""Version-pinned experimental patch for dmang-dev/mcp-dolphin's Felk bridge.

We do not ship the third-party source file. Pass a *local* copy of its bridge
script and retain its MIT copyright/license. The resulting script is UNTESTED
inside Dolphin and must be evaluated with a lawful copy of the game.
"""
from __future__ import annotations

import hashlib

# mcp-dolphin main/bridge/mcp_bridge.py inspected 2026-10-24, v0.3.0.
UPSTREAM_GIT_BLOB_SHA = "8e70624680a365707f844b322f5b093746a1c022"
PATCH_MARKER = "# WII_AI_GOLF_ATOMIC_TRACE_V1"

# Executed inside the embedded Felk coroutine. No threads and no new socket.
# Trace data: [[hold_A_boolean, accel_x, accel_y, accel_z], ...]
_ATOMIC_SNIPPET = '''# WII_AI_GOLF_ATOMIC_TRACE_V1
import math as _wii_ai_math
_wii_ai_trace = None
_wii_ai_trace_status = {"state": "idle"}
_wii_ai_trace_next_id = 0


def _wii_ai_submit(p):
    global _wii_ai_trace, _wii_ai_trace_next_id, _wii_ai_trace_status
    if _wii_ai_trace is not None:
        raise RuntimeError("atomic trace already active")
    if len(p) != 2:
        raise ValueError("trace.submit wants [wiimote_port, list_of_frame_samples]")
    port, samples = p
    if type(port) is not int or port not in (0, 1, 2, 3):
        raise ValueError("port must be 0..3")
    if not isinstance(samples, list) or not 1 <= len(samples) <= 600:
        raise ValueError("trace needs 1..600 frames")
    clean = []
    for s in samples:
        if not isinstance(s, list) or len(s) != 4 or type(s[0]) is not bool:
            raise ValueError("sample must be [bool_hold_A, x, y, z]")
        xyz = s[1:]
        if any(type(x) not in (int, float) or not _wii_ai_math.isfinite(x) or abs(x) > 16.0 for x in xyz):
            raise ValueError("acceleration must be finite within +-16 approximate g")
        clean.append((s[0], *[float(x) for x in xyz]))
    _wii_ai_trace_next_id += 1
    start = _frame_count + 1
    _wii_ai_trace = {"id": _wii_ai_trace_next_id, "port": port, "samples": clean,
                     "start": start, "applied": 0}
    _wii_ai_trace_status = {"state": "scheduled", "id": _wii_ai_trace_next_id,
                            "start_frame": start, "total_frames": len(clean), "applied_frames": 0}
    return dict(_wii_ai_trace_status)


def _wii_ai_status(_p):
    return dict(_wii_ai_trace_status)


def _wii_ai_abort(_p):
    global _wii_ai_trace, _wii_ai_trace_status
    if _wii_ai_trace is None:
        return dict(_wii_ai_trace_status)
    port = _wii_ai_trace["port"]
    controller.set_wiimote_buttons(port, {"A": False})
    _wii_ai_trace_status = {"state": "aborted", "id": _wii_ai_trace["id"],
                            "applied_frames": _wii_ai_trace["applied"]}
    _wii_ai_trace = None
    return dict(_wii_ai_trace_status)


def _wii_ai_tick():
    """Called once per emulated frame from the existing bridge coroutine."""
    global _wii_ai_trace, _wii_ai_trace_status
    t = _wii_ai_trace
    if t is None or _frame_count < t["start"]:
        return
    index = _frame_count - t["start"]
    if index < len(t["samples"]):
        hold_a, x, y, z = t["samples"][index]
        # Both setters called within ONE emulator-frame coroutine tick.
        controller.set_wiimote_buttons(t["port"], {"A": hold_a})
        controller.set_wiimote_acceleration(t["port"], x, y, z)
        t["applied"] += 1
        _wii_ai_trace_status = {"state": "running", "id": t["id"],
                                "start_frame": t["start"], "last_dispatch_frame": _frame_count,
                                "total_frames": len(t["samples"]), "applied_frames": t["applied"]}
    else:
        controller.set_wiimote_buttons(t["port"], {"A": False})
        _wii_ai_trace_status = {"state": "complete", "id": t["id"],
                                "start_frame": t["start"], "completion_dispatch_frame": _frame_count,
                                "total_frames": len(t["samples"]), "applied_frames": t["applied"]}
        _wii_ai_trace = None

'''


class UnsupportedBridgeVersion(RuntimeError):
    pass


def git_blob_sha(text: str) -> str:
    contents = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\x00" + contents).hexdigest()


def patch_bridge(source: str, *, expected_sha: str = UPSTREAM_GIT_BLOB_SHA) -> str:
    """Fail closed on source mismatch; never mutate the original input."""
    if git_blob_sha(source) != expected_sha:
        raise UnsupportedBridgeVersion("Bridge source SHA mismatch: pin and inspect upstream before patching")
    if PATCH_MARKER in source:
        raise UnsupportedBridgeVersion("Already patched")
    targets = (
        ("HANDLERS = {", _ATOMIC_SNIPPET + "HANDLERS = {"),
        ('    "frame.get_count":                _frame_get_count,',
         '    "frame.get_count":                _frame_get_count,\n'
         '    "trace.submit": _wii_ai_submit,\n'
         '    "trace.status": _wii_ai_status,\n'
         '    "trace.abort": _wii_ai_abort,'),
        ("    _frame_count += 1\n    _poll_sockets()",
         "    _frame_count += 1\n    _wii_ai_tick()\n    _poll_sockets()"),
    )
    for old, new in targets:
        if source.count(old) != 1:
            raise UnsupportedBridgeVersion("Expected upstream structure missing or repeated")
        source = source.replace(old, new, 1)
    return source
