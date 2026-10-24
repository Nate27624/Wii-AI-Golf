"""Audited *best-effort* RPC motion rehearsal; not frame-accurate replay.

Sending A and accelerometer in separate RPCs can place them in different
emulator frames. A real training run requires atomic scheduled playback.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Protocol, Sequence


class RPCTransport(Protocol):
    def call(self, method: str, params: list[Any] | None = None) -> Any: ...


@dataclass(frozen=True)
class TraceEvent:
    """Schedule one one-frame action relative to the first frame observation.

    Trace events must have strictly increasing offsets. Units of acceleration
    are those expected by the Felk bridge (approximately g); NOT calibrated.
    """
    frame_offset: int
    acceleration: tuple[float, float, float]
    hold_a: bool = True

    def __post_init__(self) -> None:
        if type(self.frame_offset) is not int or not 0 <= self.frame_offset <= 3600:
            raise ValueError("frame_offset must be integer 0..3600")
        if len(self.acceleration) != 3 or not all(math.isfinite(v) and abs(v) <= 16.0 for v in self.acceleration):
            raise ValueError("acceleration must be three finite values within +-16 approximate g")
        if type(self.hold_a) is not bool:
            raise ValueError("hold_a must be boolean")


@dataclass(frozen=True)
class TraceReport:
    source: str
    bridge_version: str
    trace_sha256: str
    start_frame: int
    end_frame: int
    event_count: int
    events: tuple[dict[str, Any], ...]
    limitations: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class TraceRehearsal:
    """A research probe, **not** a production shot-control backend."""

    def __init__(self, transport: RPCTransport, *, port: int = 0, max_poll_calls: int = 300) -> None:
        if type(port) is not int or port not in range(4):
            raise ValueError("Wiimote port must be 0..3")
        if max_poll_calls < 1:
            raise ValueError("max_poll_calls must be positive")
        self.transport = transport
        self.port = port
        self.max_poll_calls = max_poll_calls

    def _frame(self) -> int:
        n = self.transport.call("frame.get_count")
        if type(n) is not int or n < 0:
            raise RuntimeError("Bridge frame count missing or invalid")
        return n

    def preflight(self) -> dict[str, Any]:
        version = self.transport.call("bridge.ping")
        if not isinstance(version, dict) or not isinstance(version.get("bridge_version"), str):
            raise RuntimeError("Expected Felk bridge.ping metadata")
        major_minor = version["bridge_version"].split(".")[:2]
        try:
            numeric = tuple(int(x) for x in major_minor)
        except ValueError as exc:
            raise RuntimeError("Unrecognized bridge version") from exc
        if len(numeric) != 2 or numeric < (0, 2):
            raise RuntimeError("Bridge >= v0.2.0 required for accelerometer methods")
        initial = self._frame()
        after = self._frame()
        return {"bridge_version": version["bridge_version"], "initial_frame": initial,
                "second_frame": after, "frame_progressed": after > initial}

    def run(self, events: Sequence[TraceEvent]) -> TraceReport:
        if not events or any(events[i].frame_offset >= events[i + 1].frame_offset for i in range(len(events) - 1)):
            raise ValueError("Provide events ordered by strictly increasing offsets")
        if len(events) > 200:
            raise ValueError("At most 200 events in a rehearsal")
        diagnostic = self.preflight()
        start = self._frame()
        seen: list[dict[str, Any]] = []
        try:
            for event in events:
                target = start + event.frame_offset
                current = self._frame()
                polls = 0
                while current < target:
                    if polls >= self.max_poll_calls:
                        raise TimeoutError("Emulator frames not advancing toward event deadline")
                    nxt = self._frame()
                    if nxt < current:
                        raise RuntimeError("Frame counter moved backwards during trace")
                    current = nxt
                    polls += 1
                # These calls CANNOT be simultaneous on a bridge polling once per frame.
                self.transport.call("controller.set_wiimote_buttons", [self.port, {"A": event.hold_a}])
                button_ack = self._frame()
                self.transport.call("controller.set_wiimote_acceleration", [self.port, *event.acceleration])
                accel_ack = self._frame()
                seen.append({"target_frame": target, "at_send_frame": current,
                             "button_ack_frame": button_ack, "accel_ack_frame": accel_ack,
                             "lateness_frames": max(0, current - target),
                             "command_gap_frames": accel_ack - button_ack})
        finally:
            # Best-effort safety release even on failure; not a guaranteed input reset.
            self.transport.call("controller.set_wiimote_buttons", [self.port, {"A": False}])
        end = self._frame()
        serialized = json.dumps([asdict(e) for e in events], sort_keys=True, separators=(",", ":"))
        return TraceReport(
            source="rpc-rehearsal-unverified-game", bridge_version=diagnostic["bridge_version"],
            trace_sha256=hashlib.sha256(serialized.encode()).hexdigest(),
            start_frame=start, end_frame=end, event_count=len(events), events=tuple(seen),
            limitations="Non-atomic sequential RPCs; timestamps are acknowledgements, not actual input application. Real Wii Sports scoring and motion recognition unverified.",
        )


class OfflineFelkBridge:
    """Deterministic JSON-RPC-shaped fake for tests. Never touches Dolphin."""

    def __init__(self) -> None:
        self.frame = 0
        self.commands: list[tuple[str, list[Any]]] = []

    def call(self, method: str, params: list[Any] | None = None) -> Any:
        args = [] if params is None else params
        self.commands.append((method, args))
        if method == "bridge.ping":
            return {"bridge_version": "0.2.0", "dolphin": "OFFLINE FAKE"}
        if method == "frame.get_count":
            self.frame += 1
            return self.frame
        if method in {"controller.set_wiimote_buttons", "controller.set_wiimote_acceleration"}:
            self.frame += 1
            return None
        raise ValueError(f"Unexpected method: {method}")
