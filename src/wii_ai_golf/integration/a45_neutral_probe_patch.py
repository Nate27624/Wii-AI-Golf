"""Opt-in isolated V1-atomic bridge patch: skip swing setter on neutral samples.

This is a DISTINCT source file, not a modification of the original V1 bridge.
The A45 scheduler, RPC message format and nonzero swing calls stay untouched.
"""
from __future__ import annotations

from .atomic_a45_patch import ATOMIC_A45_MARKER
from .swing_patch import SWING_MARKER, SWING_NEUTRAL_V2_MARKER

ATOMIC_NEUTRAL_MARKER = "# WII_AI_GOLF_A45_NEUTRAL_CALL_SUPPRESSION_V1"
_ZERO_CALL = '                controller.set_wiimote_swing(t["port"], *t["samples"][index][1:])'
_ZERO_REPLACEMENT = (
    '                motion = t["samples"][index][1:]\n'
    '                if any(value != 0.0 for value in motion):\n'
    '                    controller.set_wiimote_swing(t["port"], *motion)'
)
_CAPS = '''# WII_AI_GOLF_A45_NEUTRAL_CALL_SUPPRESSION_V1
def _wii_ai_a45_neutral_capabilities(_p):
    return {"neutral_protocol": 1, "atomic_a45_protocol": 1,
            "no_swing_calls_for_zero_samples": True,
            "nonzero_swing_calls_preserved": True}


'''


def patch_atomic_v1_to_neutral(source: str) -> str:
    if not isinstance(source, str):
        raise ValueError("Expected an atomic V1 source string")
    for required in ("# WII_AI_GOLF_ATOMIC_TRACE_V1",
                     SWING_MARKER, ATOMIC_A45_MARKER):
        if required not in source:
            raise ValueError("Missing previously reviewed V1 atomic bridge marker")
    if (SWING_NEUTRAL_V2_MARKER in source
            or ATOMIC_NEUTRAL_MARKER in source
            or "# WII_AI_GOLF_STARTUP_STATE_V1" in source):
        raise ValueError("Already patched, autoload or incompatible bridge")
    replacements = (
        (_ZERO_CALL, _ZERO_REPLACEMENT),
        ("HANDLERS = {", _CAPS + "HANDLERS = {"),
        ('    "trace.atomic_a45_capabilities": _wii_ai_atomic_a45_capabilities,',
         '    "trace.atomic_a45_capabilities": _wii_ai_atomic_a45_capabilities,\n'
         '    "trace.a45_neutral_capabilities": _wii_ai_a45_neutral_capabilities,'),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError("Atomic V1 bridge structural mismatch at " + repr(old))
        source = source.replace(old, new, 1)
    if source.count('controller.set_wiimote_swing(t["port"], *motion)') != 1:
        raise ValueError("Patched bridge swing setter site not unique")
    return source
