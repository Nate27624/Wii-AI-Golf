"""Shared explicit frame-measured Wii Remote A lead, before an existing trace.

This helper only presses A (through the S001 button API) and polls the emulated
frame counter. It does NOT launch Dolphin, reset savestates, send motion, or
prove game-side A recognition. The caller must run the ONE canonical fresh
Dolphin/savestate/menu sequence before invoking any live controller actions.

A request count != a duration. This gives reproducible frame evidence and
keeps an observed controller-timing hypothesis separate from swing waveform.
"""
from __future__ import annotations

import math
import time
from typing import Any, Callable

from wii_ai_golf.integration.button_prime import prime_a_button, release_buttons


def _count(rpc: Any) -> int:
    value = rpc.call("frame.get_count", [])
    if type(value) is not int or value < 0:
        raise RuntimeError("frame.get_count returned invalid frame number")
    return value


def hold_a_for_observed_frames(
    rpc: Any, *, frames: int, remote: int = 0,
    timeout_s: float = 7.0, max_polls: int = 600,
    poll_sleep_s: float = 0.012,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Press A and wait for >= frames observed emulated frames, NO swing API.

    On success, A remains requested as held so the next swing trace can take
    over. Caller MUST release buttons after the trace. On every failure,
    release_buttons is attempted by this helper (also safe if caller cleans up).

    Frame counting starts after the button RPC has returned. This yields a
    lower bound on Dolphin frame progression while A is requested, NOT a
    measured physical button edge or game-internal pressed-A latch.
    """
    if type(frames) is not int or not 1 <= frames <= 90:
        raise ValueError("frames must be an integer 1..90")
    if type(remote) is not int or remote not in range(4):
        raise ValueError("remote must be 0..3")
    if type(max_polls) is not int or not 1 <= max_polls <= 2000:
        raise ValueError("max_polls must be an integer 1..2000")
    if not math.isfinite(timeout_s) or not 0 < timeout_s <= 60:
        raise ValueError("timeout_s must be finite, >0 and <=60")
    if not math.isfinite(poll_sleep_s) or not 0 <= poll_sleep_s <= 0.1:
        raise ValueError("poll_sleep_s must be finite and between 0 and 0.1")
    # Only one A-button setter is needed; the persistent emulated input is
    # then held while the frame counter advances. Do not confuse RPC calls
    # with elapsed emulated frames.
    try:
        prime_a_button(rpc, remote=remote, requests=1)
        start = _count(rpc)
        beginning = clock()
        for poll in range(1, max_polls + 1):
            if clock() - beginning > timeout_s:
                break
            latest = _count(rpc)
            if latest < start:
                raise RuntimeError("Dolphin frame counter went backwards during A lead")
            if latest - start >= frames:
                return {
                    "a_button_only_requests": 1,
                    "remote": remote,
                    "requested_lead_frames": frames,
                    "start_frame_after_a_request": start,
                    "last_observed_frame": latest,
                    "observed_frame_delta": latest - start,
                    "polls": poll,
                    "game_a_recognition_verified": False,
                }
            sleep(poll_sleep_s)
        raise TimeoutError(
            f"Dolphin did not advance {frames} observed frames during A lead "
            f"(max polls {max_polls}; timeout {timeout_s}s)"
        )
    except BaseException:
        release_buttons(rpc, remote=remote)
        raise
