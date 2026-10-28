"""Single owner for the post-boot S001 action handoff contract.

A dispatcher that has already completed the canonical Dolphin launch must
not start the probe's self-booting path for a second time.
"""
from __future__ import annotations

PROBE_SCRIPT = "probe_swing.py"
WATCHED_SWING_COLLECTOR_SCRIPT = "record_selected_ball_swing_private.py"
V1_WATCHED_SWING_COLLECTOR_SCRIPT = "record_selected_ball_swing_v1_private.py"
STATIONARY_WATCH_QUALIFIER_SCRIPT = "qualify_v1_selected_watch_readonly.py"
ATTACH_FLAG = "--attach-running"


def post_boot_action_args(script_name: str, arguments: list[str]) -> list[str]:
    """Return exact child arguments for a *completed* canonical first-shot boot.

    The attach flag is injected only for reviewed S001 post-boot scripts. A
    caller cannot explicitly request attach mode; this avoids ambiguous
    ownership of the already-running Dolphin session.
    """
    if not isinstance(arguments, list) or not all(isinstance(a, str) for a in arguments):
        raise ValueError("Post-boot action arguments must be a list of strings")
    if any(a.split("=", 1)[0] == ATTACH_FLAG for a in arguments):
        raise ValueError("Only the canonical post-boot dispatcher can authorize attach mode")
    return ([ATTACH_FLAG] if script_name in (PROBE_SCRIPT, WATCHED_SWING_COLLECTOR_SCRIPT,
                                              V1_WATCHED_SWING_COLLECTOR_SCRIPT,
                                              STATIONARY_WATCH_QUALIFIER_SCRIPT) else []) + arguments
