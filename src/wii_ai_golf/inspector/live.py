"""Opt-in read-only live worker, retaining source gates with batched reads.

All RPC calls are constrained to a memory-read allowlist; Dolphin is never
started or controlled. Tkinter is never touched from the sampling thread.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
from pathlib import Path
import queue
import sys
import threading
import time
from typing import Callable

from .replay import Sample
from .a_button import RECORD_WORDS
from .club import club_label

_ALLOWED = frozenset({"memory.read_u32", "memory.read_bytes", "frame.get_count"})
ROOT = Path(__file__).resolve().parents[3]

# Only known source-owner discontinuities are eligible for one bounded,
# in-connection transition. Malformed revision, transport/bridge failures,
# invalid data schema, frame ordering and guessed game states remain fatal.
_TRANSIENT_SOURCE_ERRORS = frozenset({
    "invalid source actor pointer",
    "not Golf scene",
    "not active Hitting-the-Green hole",
    "ambiguous selected player",
    "selected ball class mismatch",
    "scene source/owner mismatch",
    "source identity changed across packet",
    "invalid scene static",
    "invalid player manager type",
})
_TRANSITION_TIMEOUT_S = 30.0
_TRANSITION_POLL_S = 0.08


def _is_source_transition(exc: Exception) -> bool:
    return type(exc) is ValueError and str(exc) in _TRANSIENT_SOURCE_ERRORS


class ReadOnlyRPC:
    """Fail closed if a reused source reader ever attempts game control/write."""
    def __init__(self, inner: object):
        self.inner = inner
        self.calls = 0

    def call(self, method: str, args: list):
        if method not in _ALLOWED:
            raise PermissionError("Read-only inspector blocks all non-read RPC methods")
        self.calls += 1
        return self.inner.call(method, args)


@dataclass(frozen=True)
class LiveEvent:
    kind: str
    sample: Sample | None = None
    hole: int | None = None
    selected_player: int | None = None
    rate_hz: float = 0.0
    reason: str = ""
    a_record: tuple[int, ...] | None = None
    a_read_start_ns: int | None = None
    read_duration_ms: float = 0.0
    rpc_calls: int = 0
    club_index: int | None = None
    club_label: str = "UNKNOWN"


class LiveSampler:
    """Bounded queue + single background worker; no unattended reconnect."""
    def __init__(self, *, port: int = 55355, poll_pause_s: float = 0.0,
                 connector: Callable | None = None, packet_reader: Callable | None = None,
                 include_a_state: bool = False, source_gate: Callable | None = None,
                 use_batched_reads: bool = True,
                 allow_source_transitions: bool = False):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("invalid local bridge port")
        self.port = port
        self.pause = max(0.0, min(float(poll_pause_s), 3.0))
        self.connector = connector
        self.packet_reader = packet_reader
        self.include_a_state = include_a_state
        self.source_gate = source_gate
        self.use_batched_reads = use_batched_reads
        if type(allow_source_transitions) is not bool:
            raise ValueError("source transition recovery must be Boolean")
        # This opt-in applies ONLY to the built-in Rev1 packet reader.
        # Custom/injected readers retain strict fail-closed identity gates.
        self.allow_source_transitions = allow_source_transitions
        self.events: queue.Queue[LiveEvent] = queue.Queue(maxsize=24)
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread is not None:
            raise RuntimeError("live sampling already started")
        self.thread = threading.Thread(target=self._run, name="P0-inspector-readonly", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def drain(self) -> list[LiveEvent]:
        result = []
        while True:
            try:
                result.append(self.events.get_nowait())
            except queue.Empty:
                return result

    def _emit(self, event: LiveEvent) -> None:
        try:
            self.events.put_nowait(event)
        except queue.Full:
            # Drop oldest display sample, never grow RAM without bound.
            self.events.get_nowait()
            self.events.put_nowait(event)

    def _run(self) -> None:
        try:
            if self.packet_reader is None:
                # Import existing source-gated read-only reader on worker only.
                scripts = str(ROOT / "scripts")
                if scripts not in sys.path:
                    sys.path.insert(0, scripts)
                from p0_live_directional_aim_series import packet as canonical_packet, end_epoch_matches
                from .fast import packet as batched_packet
                packet = (lambda rpc, phase, index: batched_packet(
                    rpc, phase, index, include_a_state=self.include_a_state,
                    include_club_state=True
                )) if self.use_batched_reads else canonical_packet
                source_gate = self.source_gate or end_epoch_matches
            else:
                packet = self.packet_reader
                source_gate = self.source_gate
            if self.include_a_state and source_gate is None:
                raise ValueError("A record probe requires source-gated epoch recheck")
            if self.connector is None:
                from wii_ai_golf.integration.rpc import FelkRPC
                connector = lambda: FelkRPC(port=self.port, timeout_s=3.0)
            else:
                connector = self.connector
            identity = None
            clock = deque(maxlen=12)
            transition_start = None
            pending_identity = None
            pending_count = 0

            def begin_transition(reason: str) -> None:
                nonlocal transition_start, pending_identity, pending_count
                if transition_start is None:
                    transition_start = time.monotonic()
                    pending_identity = None
                    pending_count = 0
                    # Sanitized categories only: never leak source pointers.
                    self._emit(LiveEvent("transition", reason=reason))

            def check_transition_timeout() -> None:
                if (transition_start is not None
                        and time.monotonic()-transition_start > _TRANSITION_TIMEOUT_S):
                    raise ValueError("source transition not qualified within limit")
            with connector() as raw_rpc:
                rpc = ReadOnlyRPC(raw_rpc)
                index = 0
                while not self.stop_event.is_set():
                    cycle_start = time.monotonic_ns()
                    rpc_before = rpc.calls
                    try:
                        data = packet(rpc, "LIVE", index)
                    except ValueError as exc:
                        if (self.allow_source_transitions
                                and self.packet_reader is None
                                and self.use_batched_reads
                                and _is_source_transition(exc)):
                            begin_transition("Golf source temporarily unavailable / changing")
                            check_transition_timeout()
                            self.stop_event.wait(max(self.pause, _TRANSITION_POLL_S))
                            continue
                        raise
                    actor = data["identity"]
                    if not isinstance(actor, (tuple, list)) or len(actor) != 14:
                        raise ValueError("source identity schema changed")
                    actor = tuple(actor)
                    if identity is None and transition_start is None:
                        # Initial ready source: the built-in reader already
                        # independently validates beginning and end epochs.
                        identity = actor
                    elif transition_start is None and actor != identity:
                        if not (self.allow_source_transitions
                                and self.packet_reader is None
                                and self.use_batched_reads):
                            raise ValueError("source identity changed")
                        begin_transition("Golf selected owner / hole changed")
                        pending_identity = actor
                        pending_count = 1
                        self.stop_event.wait(max(self.pause, _TRANSITION_POLL_S))
                        continue
                    elif transition_start is not None:
                        # Two distinct complete, revalidated source packets
                        # must agree on all 14 identity fields before ANY
                        # A/club/ball or player proxy can be shown again.
                        if actor == pending_identity:
                            pending_count += 1
                        else:
                            pending_identity = actor
                            pending_count = 1
                        check_transition_timeout()
                        if pending_count < 2:
                            self.stop_event.wait(max(self.pause, _TRANSITION_POLL_S))
                            continue
                        identity = pending_identity
                        transition_start = None
                        pending_identity = None
                        pending_count = 0
                        clock.clear()
                        self._emit(LiveEvent("resumed", reason=(
                            "Two consecutive full source-qualified Golf packets agreed")))
                    raw_words = data["words"]
                    if not isinstance(raw_words, dict) or not raw_words:
                        raise ValueError("invalid source-qualified packet")
                    words = {}
                    for name, vector in raw_words.items():
                        if (not isinstance(name, str) or not isinstance(vector, (list, tuple))
                                or not 1 <= len(vector) <= 64
                                or any(type(bit) is not int or not 0 <= bit <= 0xFFFFFFFF for bit in vector)):
                            raise ValueError("invalid raw word types")
                        words[name] = tuple(vector)
                    start, end = data["start_ns"], data["end_ns"]
                    if type(start) is not int or type(end) is not int or start < 0 or end < start:
                        raise ValueError("invalid host time bracket")
                    frames = data.get("frame_bracket")
                    if (not isinstance(frames, (tuple, list)) or len(frames) != 2
                            or any(type(f) is not int or f < 0 for f in frames) or frames[1] < frames[0]):
                        raise ValueError("invalid bridge frame bracket")
                    owner_digest = hashlib.sha256(repr(identity).encode("ascii")).hexdigest()
                    a_words, probe_start = None, None
                    if self.include_a_state and self.use_batched_reads and self.packet_reader is None:
                        a_words = data.get('a_record')
                        if a_words is not None and (type(a_words) is not tuple
                                or len(a_words) != RECORD_WORDS
                                or any(type(bit) is not int or not 0 <= bit <= 0xFFFFFFFF for bit in a_words)):
                            raise ValueError('batched A record invalid')
                        probe_start = data['start_ns']
                    elif self.include_a_state:
                        probe_start = time.monotonic_ns()
                        # Must be the selected record in qualified MEM2; only
                        # READ 51 words + independent post-record epoch/ball/aim.
                        record_addr, ball_addr = actor[6], actor[7]
                        if (type(record_addr) is not int or type(ball_addr) is not int
                                or not 0x90000000 <= record_addr <= 0x94000000 - RECORD_WORDS * 4
                                or not 0x90000000 <= ball_addr <= 0x94000000 - 0x3C):
                            raise ValueError("A probe selected record/ball range invalid")
                        # One bounded, guest-BE byte range replaces 51 scalar
                        # bridge round trips. Decode each word; fail closed on
                        # malformed/short responses instead of silently falling
                        # back to different A semantics.
                        hex_words = rpc.call("memory.read_bytes", [record_addr, RECORD_WORDS * 4])
                        if type(hex_words) is not str or len(hex_words) != RECORD_WORDS * 8:
                            raise ValueError("A probe batched record invalid")
                        try:
                            raw_record = bytes.fromhex(hex_words)
                        except ValueError as exc:
                            raise ValueError("A probe batched record invalid hex") from exc
                        candidate = tuple(int.from_bytes(raw_record[i:i+4], "big")
                                          for i in range(0, len(raw_record), 4))
                        if not source_gate(rpc, tuple(actor)):
                            raise ValueError("A probe source epoch changed")
                        # The source-gated base packet was sampled BEFORE the
                        # 51-word scan: a moving ball/aim could otherwise be
                        # misclassified as an A transition.
                        ball_after_hex = rpc.call("memory.read_bytes", [ball_addr + 0x30, 12])
                        if type(ball_after_hex) is not str or len(ball_after_hex) != 24:
                            raise ValueError("A probe post-ball vector invalid")
                        try:
                            ball_after_bytes = bytes.fromhex(ball_after_hex)
                        except ValueError as exc:
                            raise ValueError("A probe post-ball vector invalid hex") from exc
                        ball_after = tuple(int.from_bytes(ball_after_bytes[i:i+4], "big") for i in (0, 4, 8))
                        aim_after = (rpc.call("memory.read_u32", [record_addr + 0x3C]),)
                        if any(type(bit) is not int or not 0 <= bit <= 0xFFFFFFFF
                               for bit in ball_after + aim_after):
                            raise ValueError("A probe post-scan word invalid")
                        if not source_gate(rpc, tuple(actor)):
                            raise ValueError("A probe source epoch changed on post-scan validation")
                        # Intra-scan movement -> UNKNOWN, but the ball viewer
                        # continues updating normally; no automatic reconnect.
                        if (ball_after == words.get("selected_ball_plus_0x30")
                                and aim_after == words.get("aim_candidate_plus_0x3c")):
                            a_words = candidate
                    # Only the built-in source/epoch-gated batched reader may
                    # supply a live selected-club label. Arbitrary injected
                    # packet readers cannot promote a fabricated index.
                    raw_club = (data.get('club_index')
                                if self.packet_reader is None and self.use_batched_reads
                                else None)
                    if raw_club is not None and (type(raw_club) is not int or not 0 <= raw_club <= 3):
                        raise ValueError('unqualified selected-club index')
                    selected_club_label = club_label(raw_club)
                    sample = Sample(index, "LIVE", index, start, end, words, owner_digest,
                                    True, "Read-only non-atomic source-qualified host sample", "complete", tuple(frames))
                    clock.append(time.monotonic())
                    rate = (len(clock) - 1) / (clock[-1] - clock[0]) if len(clock) >= 2 and clock[-1] > clock[0] else 0.0
                    self._emit(LiveEvent("sample", sample, int(actor[13]), int(actor[5]), rate,
                                         a_record=a_words, a_read_start_ns=probe_start,
                                         read_duration_ms=(time.monotonic_ns()-cycle_start)/1e6,
                                         rpc_calls=rpc.calls-rpc_before,
                                         club_index=raw_club, club_label=selected_club_label))
                    index += 1
                    self.stop_event.wait(self.pause)
            self._emit(LiveEvent("disconnected", reason="Operator stopped or bridge closed"))
        except (OSError, ValueError, RuntimeError, TypeError, KeyError, ImportError, TimeoutError, PermissionError, IndexError) as exc:
            # Avoid leaking dynamic guest pointers or local private file paths into UI.
            self._emit(LiveEvent("error", reason=f"Read-only source/bridge failure ({type(exc).__name__}). No automatic retry."))
