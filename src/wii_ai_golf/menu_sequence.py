"""Deterministic *requested-frame* button sequence for Hitting the Green menus.

A Felk bridge RPC override lasts only the current emulator frame. Sending
one awaited RPC per requested frame is the existing supported mechanism; it
does not prove that Wii Sports consumed the buttons or reached a target menu.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class RPCTransport(Protocol):
    def call(self, method: str, params: list[Any] | None = None) -> Any: ...


@dataclass(frozen=True)
class MenuPhase:
    label: str
    a: bool
    b: bool
    requests: int

    def __post_init__(self) -> None:
        if type(self.a) is not bool or type(self.b) is not bool:
            raise ValueError("button states must be booleans")
        if type(self.requests) is not int or not 1 <= self.requests <= 600:
            raise ValueError("each phase requires 1..600 frame requests")


def planned_menu_phases(*, startup: int = 90, a_press: int = 12,
                        between: int = 75, ab_press: int = 15,
                        gap: int = 8, final_a: int = 12,
                        settle: int = 120) -> tuple[MenuPhase, ...]:
    """Load pre-start checkpoint, then A, release/wait, A+B, release, A.

    Timings are calibration defaults, not verified navigation for all versions.
    Explicit release between A+B and final A creates a new press edge.
    """
    return (
        MenuPhase("state settle", False, False, startup),
        MenuPhase("first A", True, False, a_press),
        MenuPhase("wait", False, False, between),
        MenuPhase("A+B", True, True, ab_press),
        MenuPhase("release between presses", False, False, gap),
        MenuPhase("final A", True, False, final_a),
        MenuPhase("game transition", False, False, settle),
    )


def execute_menu_phases(rpc: RPCTransport, phases: tuple[MenuPhase, ...],
                        *, remote: int = 0) -> list[dict[str, Any]]:
    """Dispatch requested states sequentially; release A and B on exit.

    Each RPC is acknowledged before the next is sent. This normally spans
    at least one bridge emulation tick per request, but is NOT exact-frame
    playback. Timing and menu-state verification remain experimental.
    """
    if type(remote) is not int or remote not in range(4):
        raise ValueError("remote must be 0..3")
    if not phases or not all(isinstance(p, MenuPhase) for p in phases):
        raise ValueError("at least one valid phase required")
    reports: list[dict[str, Any]] = []
    try:
        for phase in phases:
            buttons = {"A": phase.a, "B": phase.b}
            for _ in range(phase.requests):
                rpc.call("controller.set_wiimote_buttons", [remote, buttons])
            reports.append({"phase": phase.label, "requested_frames": phase.requests,
                            "A": phase.a, "B": phase.b})
    finally:
        # Release even after a failed RPC. Do not mask the original error.
        for _ in range(3):
            try:
                rpc.call("controller.set_wiimote_buttons",
                         [remote, {"A": False, "B": False}])
            except Exception:
                break
    return reports
