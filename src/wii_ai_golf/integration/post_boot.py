"""Single owner for the post-boot S001 action handoff contract.

A dispatcher that has already completed the canonical Dolphin launch must
not start the probe's self-booting path for a second time.
"""
from __future__ import annotations

PROBE_SCRIPT = "probe_swing.py"
ATTACH_FLAG = "--attach-running"


def post_boot_action_args(script_name: str, arguments: list[str]) -> list[str]:
    """Return exact child arguments for a *completed* canonical first-shot boot.

    The attach flag is injected only for the self-booting S001 probe. A
    caller cannot explicitly request attach mode; this avoids ambiguous
    ownership of the already-running Dolphin session.
    """
    if not isinstance(arguments, list) or not all(isinstance(a, str) for a in arguments):
        raise ValueError("Post-boot action arguments must be a list of strings")
    if any(a.split("=", 1)[0] == ATTACH_FLAG for a in arguments):
        raise ValueError("Only the canonical post-boot dispatcher can authorize attach mode")
    return ([ATTACH_FLAG] if script_name == PROBE_SCRIPT else []) + arguments
