"""Review-only V1 adapter for the source-selected 51-word frame watcher.

No modification to original historical V1 bridge or frozen swing waveform.
A 45-request button prime is NOT the observed 45-Dolphin-frame A lead which
produced human confirmed contact. Never use this offline adapter as permission
to perform live watched gameplay without S001/S002/S000 owner review.
"""
from __future__ import annotations

import ast
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



def _find_unique_emulator_tick_line(source: str) -> int:
    """Find original V1 tick within the actual frameadvance loop, not by adjacency."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise V1BallWatchCompatibilityError("V1 source syntax not parseable") from exc
    found = []
    for node in tree.body:
        if not (isinstance(node, ast.While)
                and isinstance(node.test, ast.Constant) and node.test.value is True):
            continue
        body = node.body
        def call_is(statement, name, owner=None):
            if not (isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Call)
                    and not statement.value.args and not statement.value.keywords):
                return False
            fn = statement.value.func
            if owner:
                return (isinstance(fn, ast.Attribute) and fn.attr == name
                        and isinstance(fn.value, ast.Name) and fn.value.id == owner)
            return isinstance(fn, ast.Name) and fn.id == name
        advance = [i for i, item in enumerate(body)
                   if isinstance(item, ast.Expr) and isinstance(item.value, ast.Await)
                   and isinstance(item.value.value, ast.Call)
                   and isinstance(item.value.value.func, ast.Attribute)
                   and item.value.value.func.attr == "frameadvance"
                   and isinstance(item.value.value.func.value, ast.Name)
                   and item.value.value.func.value.id == "event"]
        increments = [i for i, item in enumerate(body)
                      if isinstance(item, ast.AugAssign)
                      and isinstance(item.target, ast.Name)
                      and item.target.id == "_frame_count"
                      and isinstance(item.op, ast.Add)
                      and isinstance(item.value, ast.Constant)
                      and item.value.value == 1]
        ticks = [(i, item) for i, item in enumerate(body) if call_is(item, "_wii_ai_tick")]
        polls = [i for i, item in enumerate(body) if call_is(item, "_poll_sockets")]
        if (len(advance) == len(increments) == len(ticks) == len(polls) == 1
                and advance[0] < increments[0] < ticks[0]):
            found.append(ticks[0][1])
    if len(found) != 1:
        raise V1BallWatchCompatibilityError("Unique verified frameadvance loop absent")
    # No hidden additional invocation may coexist in a nested function/loop.
    all_ticks = [node for node in ast.walk(tree)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name)
                 and node.func.id == "_wii_ai_tick"]
    if len(all_ticks) != 1:
        raise V1BallWatchCompatibilityError("Duplicate/hidden V1 controller tick")
    line = found[0].lineno
    lines = source.splitlines(keepends=True)
    if line < 1 or line > len(lines):
        raise V1BallWatchCompatibilityError("Invalid source location")
    original = lines[line - 1]
    if original.rstrip("\r\n") != "    _wii_ai_tick()" or not original.endswith("\n"):
        raise V1BallWatchCompatibilityError("V1 controller tick line differs")
    return line

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

    )
    tick_line = _find_unique_emulator_tick_line(source)
    result = source
    for old, new in modifications:
        if result.count(old) != 1:
            raise V1BallWatchCompatibilityError(
                "V1 source layout mismatch; refuses anchor guessing")
        result = result.replace(old, new, 1)
    # The handler insertions are all BEFORE the tail coroutine, so the tick
    # line shifts. Identify it again in the new source, never guess line numbers.
    inserted_line = _find_unique_emulator_tick_line(result)
    lines = result.splitlines(keepends=True)
    original_tick = lines[inserted_line - 1]
    newline = "\r\n" if original_tick.endswith("\r\n") else "\n"
    injected = "    _wii_ball_watch_tick()" + newline
    lines.insert(inserted_line - 1, injected)
    result = "".join(lines)
    if result.count(BALL_WATCH_MARKER) != 1:
        raise V1BallWatchCompatibilityError("Watcher inserted more than once")
    # Reversibility check ensures only one read call + the two handler insertions.
    reverse_lines = result.splitlines(keepends=True)
    if reverse_lines[inserted_line - 1] != injected:
        raise V1BallWatchCompatibilityError("Cannot reverse watcher tick")
    del reverse_lines[inserted_line - 1]
    reconstructed = "".join(reverse_lines)
    for old, new in reversed(modifications):
        if reconstructed.count(new) != 1:
            raise V1BallWatchCompatibilityError("Failed source preservation check")
        reconstructed = reconstructed.replace(new, old, 1)
    if reconstructed != source or tick_line < 1:
        raise V1BallWatchCompatibilityError("Original V1 source was not preserved")
    return result
