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
    source_segment: int = 0


# Source-transition errors are expected while Golf replaces the active
# shot/scene. They may interrupt a verified packet, but must NOT be treated
# as game corruption, and must NEVER be promoted into a sample.
# Other ValueErrors (malformed bytes, wrong Rev1 image, schema changes)
# remain fatal. The no-source interval is explicitly bounded.
_TRANSIENT_READ_REASONS = frozenset({
    "source identity changed across packet",
    "not Golf scene",
    "scene source/owner mismatch",
    "not active Hitting-the-Green hole",
    "invalid scene static",
    "invalid player manager type",
    "ambiguous selected player",
    "selected ball class mismatch",
    "invalid source actor pointer",
    "invalid source-scoped block",
})
_TRANSITION_MAX_SECONDS = 20.0
_TRANSITION_PAUSE_SECONDS = 0.12


class LiveSampler:
    """Bounded queue + single background worker; no unattended reconnect."""
    def __init__(self, *, port: int = 55355, poll_pause_s: float = 0.0,
                 connector: Callable | None = None, packet_reader: Callable | None = None,
                 include_a_state: bool = False, source_gate: Callable | None = None,
                 use_batched_reads: bool = True):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("invalid local bridge port")
        self.port = port
        self.pause = max(0.0, min(float(poll_pause_s), 3.0))
        self.connector = connector
        self.packet_reader = packet_reader
        self.include_a_state = include_a_state
        self.source_gate = source_gate
        self.use_batched_reads = use_batched_reads
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
            source_segment = 1
            transitioning = False
            transition_start: float | None = None
            tentative_identity = None
            tentative_count = 0
            clock = deque(maxlen=12)
            with connector() as raw_rpc:
                rpc = ReadOnlyRPC(raw_rpc)
                index = 0
                while not self.stop_event.is_set():
                    cycle_start = time.monotonic_ns()
                    rpc_before = rpc.calls
                    try:
                        data = packet(rpc, "LIVE", index)
                    except ValueError as exc:
                        # While Dolphin changes the current shot/scene, the
                        # previous verified source roots can disappear. Keep
                        # this SAME read-only connection open briefly, but
                        # never show the previous ball/club as still live.
                        if (self.packet_reader is not None
                                or str(exc) not in _TRANSIENT_READ_REASONS):
                            raise
                        if not transitioning:
                            transitioning = True
                            transition_start = time.monotonic()
                            tentative_identity = None
                            tentative_count = 0
                            self._emit(LiveEvent(
                                "transition", reason="SOURCE_TEMPORARILY_UNAVAILABLE",
                                source_segment=source_segment))
                        if (transition_start is not None
                                and time.monotonic() - transition_start
                                > _TRANSITION_MAX_SECONDS):
                            raise ValueError("source transition timed out") from None
                        self.stop_event.wait(max(self.pause,
                                                 _TRANSITION_PAUSE_SECONDS))
                        continue
                    actor = data["identity"]
                    if not isinstance(actor, (tuple, list)) or len(actor) != 14:
                        raise ValueError("source identity schema changed")
                    # Strictly verify the entire new packet first. Only
                    # AFTER complete source+time+type gating may its
                    # identity become a candidate for a new shot segment.
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
                    # The final source-segment digest is assigned BELOW,
                    # after any identity transition has been confirmed.
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
                    qualified_identity = tuple(actor)
                    if identity is None and not transitioning:
                        identity = qualified_identity
                    elif not transitioning and qualified_identity != identity:
                        if self.packet_reader is not None:
                            # Synthetic/custom readers lack the built-in
                            # original Rev1 source/epoch validation needed
                            # to establish a new owner identity.
                            raise ValueError("source identity changed")
                        transitioning = True
                        transition_start = time.monotonic()
                        tentative_identity = qualified_identity
                        tentative_count = 1
                        self._emit(LiveEvent(
                            "transition", reason="VERIFIED_SOURCE_IDENTITY_CHANGED",
                            source_segment=source_segment))
                        continue
                    if transitioning:
                        if (transition_start is not None
                                and time.monotonic() - transition_start
                                > _TRANSITION_MAX_SECONDS):
                            raise ValueError("source transition timed out")
                        if qualified_identity == tentative_identity:
                            tentative_count += 1
                        else:
                            tentative_identity = qualified_identity
                            tentative_count = 1
                        # Two independently source-qualified packets must
                        # agree before the UI accepts the new segment.
                        if tentative_count < 2:
                            self.stop_event.wait(max(self.pause, 0.01))
                            continue
                        identity = qualified_identity
                        source_segment += 1
                        transitioning = False
                        transition_start = None
                        tentative_identity = None
                        tentative_count = 0
                        clock.clear()
                    owner_digest = hashlib.sha256(
                        repr((source_segment, identity)).encode("ascii")
                    ).hexdigest()
                    sample = Sample(index, "LIVE", index, start, end, words,
                                    owner_digest, True,
                                    "Read-only non-atomic source-qualified host sample "
                                    f"· source segment {source_segment}; shot number NOT verified",
                                    "complete", tuple(frames))
                    clock.append(time.monotonic())
                    rate = (len(clock) - 1) / (clock[-1] - clock[0]) if len(clock) >= 2 and clock[-1] > clock[0] else 0.0
                    self._emit(LiveEvent("sample", sample, int(actor[13]), int(actor[5]), rate,
                                         a_record=a_words, a_read_start_ns=probe_start,
                                         read_duration_ms=(time.monotonic_ns()-cycle_start)/1e6,
                                         rpc_calls=rpc.calls-rpc_before,
                                         club_index=raw_club, club_label=selected_club_label,
                                         source_segment=source_segment))
                    index += 1
                    self.stop_event.wait(self.pause)
            self._emit(LiveEvent("disconnected", reason="Operator stopped or bridge closed"))
        except (OSError, ValueError, RuntimeError, TypeError, KeyError, ImportError, TimeoutError, PermissionError, IndexError) as exc:
            # Avoid leaking dynamic guest pointers or local private file paths into UI.
            # Report a bounded reason class, not guest pointers or paths.
            safe_codes = {
                "source transition timed out": "TRANSITION_TIMEOUT",
                "not Wii Sports USA Rev1": "WRONG_GAME_REVISION",
                "invalid revision header": "INVALID_REVISION_HEADER",
                "malformed bounded read": "MALFORMED_BRIDGE_READ",
                "invalid BE bytes": "MALFORMED_BRIDGE_READ",
                "short bounded read": "SHORT_BRIDGE_READ",
                "invalid bridge frame bracket": "INVALID_BRIDGE_FRAME",
                "invalid frame bracket": "INVALID_BRIDGE_FRAME",
                "invalid bridge ordering": "INVALID_BRIDGE_FRAME",
                "source identity changed": "CUSTOM_READER_SOURCE_SWAP",
                "source identity schema changed": "SOURCE_IDENTITY_SCHEMA",
                "invalid source-qualified packet": "SOURCE_PACKET_SCHEMA",
            }
            category = safe_codes.get(
                str(exc), "UNEXPECTED_SOURCE_OR_BRIDGE_FAILURE")
            self._emit(LiveEvent(
                "error", reason=f"Read-only source/bridge failure: {category} "
                f"({type(exc).__name__}). No automatic reconnect."))
