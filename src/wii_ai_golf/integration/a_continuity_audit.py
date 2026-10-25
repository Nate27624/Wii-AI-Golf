"""Read-only logical A-button continuity audit for a single golf swing.

This audits controller COMMANDS, not physical Wii Sports input or observed button state.
No Dolphin access, networking, or changes to the authoritative swing scheduler.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ButtonEvent:
    phase: str
    index: int
    a: bool
    source: str = "client_command"

    def __post_init__(self) -> None:
        if not isinstance(self.phase, str) or not self.phase:
            raise ValueError("phase must be nonempty")
        if type(self.index) is not int or self.index < 0:
            raise ValueError("index must be a nonnegative integer")
        if type(self.a) is not bool:
            raise ValueError("A state must be boolean")
        if self.source not in ("client_command", "bridge_dispatch"):
            raise ValueError("unrecognized observation source")


def audit_a_continuity(events: Iterable[ButtonEvent]) -> dict:
    """Expect uninterrupted A from prehold through swing, then one final release.

    Strictly ordered command indices. An empty or partial trace is UNKNOWN, not
    success; an unexpected release is a FAIL. A clean command trace is not proof
    of in-game reception.
    """
    items = list(events)
    if not items:
        return {"status": "unknown", "reason": "no_events", "unexpected_releases": 0,
                "transitions": [], "observed_events": 0}
    if any(not isinstance(e, ButtonEvent) for e in items):
        raise ValueError("all entries must be ButtonEvent")
    if len({e.source for e in items}) != 1:
        raise ValueError("cannot mix client commands and bridge dispatches")
    if any(b.index <= a.index for a, b in zip(items, items[1:])):
        raise ValueError("event indices must increase strictly")
    transitions = [
        {"index": item.index, "phase": item.phase, "a": item.a}
        for i, item in enumerate(items)
        if i == 0 or item.a != items[i - 1].a
    ]
    releases = [e for e in items if not e.a and e.phase != "release"]
    unexpected = len(releases)
    phases = {e.phase for e in items}
    required = {"prehold", "backswing", "forward", "follow_through", "release"}
    # A release may be followed by additional commands; any A=False during an
    # active phase is an error, even if A subsequently becomes True.
    invalid_active = any(not e.a and e.phase != "release" for e in items)
    invalid_release = any(e.a and e.phase == "release" for e in items)
    if invalid_active or invalid_release or items[0].a is False or (
        items[-1].phase == "release" and items[-1].a is not False
    ):
        status, reason = "fail", "unexpected_a_transition"
    elif not required.issubset(phases) or items[-1].phase != "release":
        status, reason = "unknown", "incomplete_trace"
    elif transitions != [
        {"index": items[0].index, "phase": items[0].phase, "a": True},
        {"index": next(e.index for e in items if e.phase == "release"), "phase": "release", "a": False},
    ]:
        status, reason = "fail", "extra_transition"
    else:
        status, reason = "pass", "command_sequence_continuous"
    return {"status": status, "reason": reason,
            "unexpected_releases": unexpected,
            "transitions": transitions, "observed_events": len(items),
            "source": items[0].source, "game_verified": False}


def expected_v1_events(samples, *, prehold_frames: int = 45) -> list[ButtonEvent]:
    """Create an EXPECTED trace from the intended 89-frame sample program.

    This deliberately does not claim the bridge emitted those commands.
    """
    if type(prehold_frames) is not int or prehold_frames < 0:
        raise ValueError("prehold_frames must be nonnegative")
    result = [ButtonEvent("prehold", i, True) for i in range(prehold_frames)]
    phases = ("setup", "backswing", "forward", "follow_through", "release")
    if len(samples) != 89:
        raise ValueError("expected V1 trace must have exactly 89 samples")
    for i, sample in enumerate(samples):
        # Intended original waveform: 12 setup, 15 back, 20 forward,
        # 30 follow-through, 12 released.
        phase = phases[0] if i < 12 else phases[1] if i < 27 else (
            phases[2] if i < 47 else phases[3] if i < 77 else phases[4])
        result.append(ButtonEvent(phase, prehold_frames + i, sample.hold_a))
    return result
