"""Opt-in Felk Preview 4 atomic A + dedicated swing primitive extension.

The existing source-pinned atomic scheduler writes A+acceleration. This module
extends the *generated* atomic bridge to schedule A+set_wiimote_swing, using the
same frame loop, trace status and abort methods, without modifying upstream
mcp-dolphin sources or the pre-existing acceleration trace format.
"""
from __future__ import annotations

from .atomic_patch import PATCH_MARKER

SWING_MARKER = "# WII_AI_GOLF_SWING_TRACE_V1"
SWING_NEUTRAL_V2_MARKER = "# WII_AI_GOLF_SWING_NEUTRAL_BUTTON_ONLY_V2"

_SWING_HANDLER = '''# WII_AI_GOLF_SWING_TRACE_V1
# WII_AI_GOLF_SWING_NEUTRAL_BUTTON_ONLY_V2
def _wii_ai_swing_capabilities(_p):
    """Pure read-only RPC for safe client preflight, no input is dispatched."""
    return {"swing_protocol": 2, "neutral_button_only": True,
            "method": "trace.submit_swing", "button_first": True}


def _wii_ai_submit_swing(p):
    global _wii_ai_trace, _wii_ai_trace_next_id, _wii_ai_trace_status
    if _wii_ai_trace is not None:
        raise RuntimeError("a motion trace is already active")
    if len(p) != 2:
        raise ValueError("trace.submit_swing requires [remote_port, samples]")
    port, samples = p
    if type(port) is not int or port not in (0, 1, 2, 3):
        raise ValueError("Wiimote port must be 0..3")
    if not isinstance(samples, list) or not 1 <= len(samples) <= 600:
        raise ValueError("1..600 swing samples required")
    clean = []
    for sample in samples:
        if not isinstance(sample, list) or len(sample) != 8 or type(sample[0]) is not bool:
            raise ValueError("swing sample: [hold_a, dx,dy,dz,distance,speed,return_speed,angle]")
        raw = sample[1:]
        if any(type(x) not in (int, float) or not _wii_ai_math.isfinite(x) for x in raw):
            raise ValueError("swing parameters must be finite numeric values")
        dx, dy, dz, distance, speed, return_speed, angle = map(float, raw)
        if any(abs(v) > 1.0 for v in (dx, dy, dz)):
            raise ValueError("swing direction components must be -1..1")
        if not 0 <= distance <= 1.5 or not 0 <= speed <= 8.0 or not 0 <= return_speed <= 8.0:
            raise ValueError("swing distance (m) or speed (m/s) out of conservative bounds")
        if abs(angle) > 3.141592654:
            raise ValueError("swing angle must be within +/-pi radians")
        clean.append((sample[0], dx, dy, dz, distance, speed, return_speed, angle))
    _wii_ai_trace_next_id += 1
    start = _frame_count + 1
    _wii_ai_trace = {"id": _wii_ai_trace_next_id, "port": port, "samples": clean,
                     "kind": "swing", "start": start, "applied": 0}
    _wii_ai_trace_status = {"state": "scheduled", "kind": "swing",
                            "swing_protocol": 2,
                            "id": _wii_ai_trace_next_id, "start_frame": start,
                            "total_frames": len(clean), "applied_frames": 0}
    return dict(_wii_ai_trace_status)


'''


class SwingExtensionError(RuntimeError):
    """Input is not the expected generated atomic Felk bridge."""


def extend_atomic_bridge_with_swing(source: str) -> str:
    """Add the swing primitive to an already SHA-pinned atomic bridge.

    This never patches a naked upstream bridge. The caller first executes
    patch_bridge() against the reviewed upstream Git blob.
    """
    if PATCH_MARKER not in source or SWING_MARKER in source:
        raise SwingExtensionError("Expected unextended, source-pinned atomic bridge")
    substitutions = (
        ("HANDLERS = {", _SWING_HANDLER + "HANDLERS = {"),
        ('    "trace.submit": _wii_ai_submit,',
         '    "trace.submit": _wii_ai_submit,\n'
         '    "trace.submit_swing": _wii_ai_submit_swing,\n'
         '    "trace.swing_capabilities": _wii_ai_swing_capabilities,'),
        ('        hold_a, x, y, z = t["samples"][index]',
         '        hold_a = t["samples"][index][0]'),
        ('        controller.set_wiimote_acceleration(t["port"], x, y, z)',
         '        if t.get("kind") == "swing":\n'
         '            try:\n'
         '                # V2: neutral swing samples are BUTTON-ONLY frame updates.\n'
         '                # Calling set_wiimote_swing(0...) can reset dynamics or\n'
         '                # trigger an unintended practice swing before A is read.\n'
         '                motion = t["samples"][index][1:]\n'
         '                if any(value != 0.0 for value in motion):\n'
         '                    controller.set_wiimote_swing(t["port"], *motion)\n'
         '            except Exception as exc:\n'
         '                controller.set_wiimote_buttons(t["port"], {"A": False})\n'
         '                _wii_ai_trace_status = {"state": "error", "id": t["id"],\n'
         '                    "applied_frames": t["applied"], "error": f"{type(exc).__name__}: {exc}"}\n'
         '                _wii_ai_trace = None\n'
         '                return\n'
         '        else:\n'
         '            _, x, y, z = t["samples"][index]\n'
         '            controller.set_wiimote_acceleration(t["port"], x, y, z)'),
    )
    for anchor, new_text in substitutions:
        if source.count(anchor) != 1:
            raise SwingExtensionError(f"Unexpected generated bridge structure: {anchor!r}")
        source = source.replace(anchor, new_text, 1)
    return source
