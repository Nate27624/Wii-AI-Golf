"""True A-button-only prehold before scheduling any Felk swing primitive.

Unlike neutral `SwingSample` frames, these requests call ONLY
controller.set_wiimote_buttons, never set_wiimote_swing. User observation
showed that a swing primitive (even with zero vector) may run before the
game recognizes the A press. Dispatch does not prove game-side recognition.
"""
from __future__ import annotations

from typing import Any, Protocol


class ButtonRPC(Protocol):
    def call(self, method: str, params: list[Any] | None = None) -> Any: ...


def prime_a_button(rpc: ButtonRPC, *, remote: int = 0,
                   requests: int = 60) -> dict[str, int]:
    """Send A-only RPC requests before the swing trace.

    Preserve pressed A at end; the downstream swing trace continues holding A.
    This is a requested-frame count, NOT a verified in-game hold duration.
    """
    if type(remote) is not int or remote not in range(4):
        raise ValueError("remote must be 0..3")
    if type(requests) is not int or not 0 <= requests <= 180:
        raise ValueError("button-only A prime must be 0..180 requests")
    completed = 0
    try:
        for _ in range(requests):
            rpc.call("controller.set_wiimote_buttons",
                     [remote, {"A": True, "B": False}])
            completed += 1
    except Exception:
        release_buttons(rpc, remote=remote)
        raise
    return {"button_only_requests": completed, "remote": remote}


def release_buttons(rpc: ButtonRPC, *, remote: int = 0) -> None:
    """Best-effort cleanup; does not mask a failed swing or interrupted prime."""
    if type(remote) is not int or remote not in range(4):
        raise ValueError("remote must be 0..3")
    for _ in range(3):
        try:
            rpc.call("controller.set_wiimote_buttons",
                     [remote, {"A": False, "B": False}])
        except Exception:
            break
