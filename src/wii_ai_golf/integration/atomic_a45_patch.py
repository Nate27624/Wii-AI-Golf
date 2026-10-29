"""Add a frame-synchronous A45 prelude to an isolated, reviewed legacy V1 bridge.

The *input* is an existing local generated V1 swing bridge, not upstream source.
A new output file is required: NEVER edit the old trusted V1 bridge in place.
The prelude and unchanged 89-frame swing execute in ONE Felk coroutine
scheduler; polling frame.get_count from the RPC client cannot do this.
"""
from __future__ import annotations

from .atomic_patch import PATCH_MARKER
from .swing_patch import SWING_MARKER, SWING_NEUTRAL_V2_MARKER

ATOMIC_A45_MARKER = "# WII_AI_GOLF_ATOMIC_A45_BRIDGE_V1"

_SNIPPET = '''# WII_AI_GOLF_ATOMIC_A45_BRIDGE_V1
# Opt-in atomic action; 45 button-only ticks followed by the original V1
# 89-sample trace with no RPC/host polling boundary between phases.
def _wii_ai_atomic_a45_capabilities(_p):
    return {"atomic_a45_protocol": 1, "lead_frames": 45,
            "button_only_lead": True, "atomic_swing_followup": True}


def _wii_ai_submit_atomic_a45(p):
    global _wii_ai_trace, _wii_ai_trace_status
    if not isinstance(p, list) or len(p) != 2:
        raise ValueError("trace.submit_atomic_a45 requires [port, 89 samples]")
    port, samples = p
    if not isinstance(samples, list) or len(samples) != 89:
        raise ValueError("atomic A45 requires the frozen 89-frame swing")
    # Strict original A topology: held through setup/back/forward/follow,
    # released for the final 12. The original swing handler validates all
    # vector numeric ranges before anything is scheduled.
    if any(not isinstance(s, list) or not s or
           type(s[0]) is not bool or s[0] is not (i < 77)
           for i, s in enumerate(samples)):
        raise ValueError("atomic A45 original 77-held/12-released A shape required")
    status = _wii_ai_submit_swing([port, samples])
    t = _wii_ai_trace
    t["kind"] = "atomic_a45"
    t["a45_lead_start"] = t["start"]
    t["a45_applied"] = 0
    _wii_ai_trace_status = dict(status,
        kind="atomic_a45_swing", prehold_requested_frames=45,
        prehold_applied_frames=0, applied_frames=0,
        game_a_recognition_verified=False)
    return dict(_wii_ai_trace_status)


def _wii_ai_golf_atomic_a45_tick():
    global _wii_ai_trace, _wii_ai_trace_status
    t = _wii_ai_trace
    if t is None or not (t.get("kind") == "atomic_a45"
                         or t.get("a45_prehold_complete") is True):
        return _wii_ai_tick()
    if t.get("kind") == "atomic_a45":
        start = t["a45_lead_start"]
        if _frame_count < start:
            return
        index = _frame_count - start
        if index < 45:
            # Ensure the bridge callback itself ran once at each lead tick.
            if index != t["a45_applied"]:
                controller.set_wiimote_buttons(t["port"], {"A": False})
                _wii_ai_trace_status = {
                    "state": "error", "kind": "atomic_a45_swing",
                    "id": t["id"], "error": "a45_callback_gap",
                    "prehold_applied_frames": t["a45_applied"],
                    "applied_frames": 0}
                _wii_ai_trace = None
                return
            controller.set_wiimote_buttons(t["port"], {"A": True})
            t["a45_applied"] += 1
            _wii_ai_trace_status = {
                "state": "running", "kind": "atomic_a45_swing",
                "id": t["id"], "start_frame": start,
                "prehold_requested_frames": 45,
                "prehold_applied_frames": t["a45_applied"],
                "last_prehold_frame": _frame_count,
                "applied_frames": 0,
                "game_a_recognition_verified": False}
            return
        if index != 45 or t["a45_applied"] != 45:
            controller.set_wiimote_buttons(t["port"], {"A": False})
            _wii_ai_trace_status = {
                "state": "error", "kind": "atomic_a45_swing",
                "id": t["id"], "error": "a45_swing_transition_gap",
                "prehold_applied_frames": t["a45_applied"],
                "applied_frames": 0}
            _wii_ai_trace = None
            return
        # Original scheduler now starts its first 89 swing samples on THIS
        # callback, immediately following the 45 contiguous A-only callbacks.
        t["start"] = start + 45
        t["kind"] = "swing"
        t["a45_prehold_complete"] = True
    _wii_ai_tick()  # original V1 movement scheduler and completion/abort
    status = dict(_wii_ai_trace_status)
    status.update({
        "kind": "atomic_a45_swing", "prehold_requested_frames": 45,
        "prehold_applied_frames": 45,
        "prehold_start_frame": t["a45_lead_start"],
        "last_prehold_frame": t["a45_lead_start"] + 44,
        "trace_start_frame": t["a45_lead_start"] + 45,
        "game_a_recognition_verified": False,
    })
    _wii_ai_trace_status = status


'''


class AtomicA45PatchError(ValueError):
    pass


def patch_isolated_v1_bridge(source: str) -> str:
    """Return a separate, opt-in source; fail closed on structural ambiguity."""
    if not isinstance(source, str) or any(marker not in source for marker in (
        PATCH_MARKER, SWING_MARKER,
    )):
        raise AtomicA45PatchError("Expected generated atomic V1 swing bridge")
    if SWING_NEUTRAL_V2_MARKER in source or ATOMIC_A45_MARKER in source:
        raise AtomicA45PatchError("Expected unmodified V1 (not V2/A45)")
    edits = (
        ("HANDLERS = {", _SNIPPET + "HANDLERS = {"),
        ('    "trace.submit_swing": _wii_ai_submit_swing,',
         '    "trace.submit_swing": _wii_ai_submit_swing,\n'
         '    "trace.submit_atomic_a45": _wii_ai_submit_atomic_a45,\n'
         '    "trace.atomic_a45_capabilities": _wii_ai_atomic_a45_capabilities,'),
        ("    _wii_ai_tick()\n    _poll_sockets()",
         "    _wii_ai_golf_atomic_a45_tick()\n    _poll_sockets()"),
    )
    for old, new in edits:
        if source.count(old) != 1:
            raise AtomicA45PatchError("V1 bridge structure missing or ambiguous: " + repr(old))
        source = source.replace(old, new, 1)
    return source
