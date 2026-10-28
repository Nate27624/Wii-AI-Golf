"""Review-only V1 adapter for the source-selected 51-word frame watcher.

No modification to original historical V1 bridge or frozen swing waveform.
A 45-request button prime is NOT the observed 45-Dolphin-frame A lead which
produced human confirmed contact. Never use this offline adapter as permission
to perform live watched gameplay without S001/S002/S000 owner review.
"""
from __future__ import annotations

import hashlib

from .atomic_patch import PATCH_MARKER, BOOT_MARKER
from .swing_patch import SWING_MARKER, SWING_NEUTRAL_V2_MARKER
from .ball_watch_patch import BALL_WATCH_MARKER, _BALL_WATCH_HANDLER

KNOWN_CONTACT_V1_SHA256 = (
    "fe04cb0ba312c559d5cb7edb8d0ac2185aca72046839a903160929ee7c58ca19"
)


class V1BallWatchCompatibilityError(ValueError):
    """Fail closed for missing/mismatched historical V1 runtime sources."""


_IDENTITY_HANDLER = '''def _wii_ball_v1_provenance(_p):
    # This describes patched controller source, NOT game contact.
    return {"swing_protocol": 1, "legacy_neutral_swing_events": True,
            "ball_watch": "S001-S002-51-untyped-u32-private",
            "a_lead_observed_frames_required_by_operator_baseline": 45,
            "a_lead_applied": False,
            "live_contact_verified": False,
            "game_ball_xyz_verified": False,
            "training_allowed": False}


'''


def extend_known_v1_with_selected_watch(
    source: str, *, expected_sha256: str = KNOWN_CONTACT_V1_SHA256
) -> str:
    """Add read-only source-selected watcher ahead of historical V1 tick.

    The SHA override exists solely for synthetic tests; the production CLI
    does not accept a SHA override. Original controller instructions preserved.
    """
    if not isinstance(source, str):
        raise V1BallWatchCompatibilityError("Expected UTF-8 bridge source")
    if hashlib.sha256(source.encode("utf-8")).hexdigest() != expected_sha256:
        raise V1BallWatchCompatibilityError("V1 source SHA-256 mismatch")
    if (PATCH_MARKER not in source or SWING_MARKER not in source
            or BOOT_MARKER in source or SWING_NEUTRAL_V2_MARKER in source
            or BALL_WATCH_MARKER in source):
        raise V1BallWatchCompatibilityError("Not isolated original no-autoload Swing V1")

    modifications = (
        ("HANDLERS = {",
         _BALL_WATCH_HANDLER + _IDENTITY_HANDLER + "HANDLERS = {"),
        ('    "trace.submit_swing": _wii_ai_submit_swing,',
         '    "trace.submit_swing": _wii_ai_submit_swing,\n'
         '    "golf.ball_watch.arm": _wii_ball_watch_arm,\n'
         '    "golf.ball_watch.stage": _wii_ball_watch_stage,\n'
         '    "golf.ball_watch.status": _wii_ball_watch_status,\n'
         '    "golf.ball_watch.drain": _wii_ball_watch_drain,\n'
         '    "golf.ball_watch.v1_provenance": _wii_ball_v1_provenance,'),
        ("    _wii_ai_tick()\n    _poll_sockets()",
         "    _wii_ball_watch_tick()\n    _wii_ai_tick()\n    _poll_sockets()"),
    )
    result = source
    for old, new in modifications:
        if result.count(old) != 1:
            raise V1BallWatchCompatibilityError(
                "V1 source layout mismatch; refuses anchor guessing")
        result = result.replace(old, new, 1)
    if (result.count("    _wii_ball_watch_tick()\n    _wii_ai_tick()") != 1
            or result.count(BALL_WATCH_MARKER) != 1):
        raise V1BallWatchCompatibilityError("Watcher tick duplication detected")
    reconstructed = result
    for old, new in reversed(modifications):
        if reconstructed.count(new) != 1:
            raise V1BallWatchCompatibilityError("Failed source preservation check")
        reconstructed = reconstructed.replace(new, old, 1)
    if reconstructed != source:
        raise V1BallWatchCompatibilityError("Original V1 source was not preserved")
    return result
