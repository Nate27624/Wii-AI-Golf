"""Opt-in read-only live worker, reusing the repository's source-gated P0 packet.

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

_ALLOWED = frozenset({"memory.read_u32", "memory.read_bytes", "frame.get_count"})
ROOT = Path(__file__).resolve().parents[3]


class ReadOnlyRPC:
    """Fail closed if a reused source reader ever attempts game control/write."""
    def __init__(self, inner: object):
        self.inner = inner

    def call(self, method: str, args: list):
        if method not in _ALLOWED:
            raise PermissionError("Read-only inspector blocks all non-read RPC methods")
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


class LiveSampler:
    """Bounded queue + single background worker; no unattended reconnect."""
    def __init__(self, *, port: int = 55355, poll_pause_s: float = 0.15,
                 connector: Callable | None = None, packet_reader: Callable | None = None,
                 include_a_state: bool = False, source_gate: Callable | None = None):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("invalid local bridge port")
        self.port = port
        self.pause = max(0.0, min(float(poll_pause_s), 3.0))
        self.connector = connector
        self.packet_reader = packet_reader
        self.include_a_state = include_a_state
        self.source_gate = source_gate
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
                from p0_live_directional_aim_series import packet, end_epoch_matches
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
            with connector() as raw_rpc:
                rpc = ReadOnlyRPC(raw_rpc)
                index = 0
                while not self.stop_event.is_set():
                    data = packet(rpc, "LIVE", index)
                    actor = data["identity"]
                    if not isinstance(actor, (tuple, list)) or len(actor) != 14:
                        raise ValueError("source identity schema changed")
                    if identity is None:
                        identity = tuple(actor)
                    elif tuple(actor) != identity:
                        raise ValueError("source identity changed")
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
                    if self.include_a_state:
                        probe_start = time.monotonic_ns()
                        # Must be the selected record in qualified MEM2; only
                        # READ 51 words + independent post-record epoch/ball/aim.
                        record_addr, ball_addr = actor[6], actor[7]
                        if (type(record_addr) is not int or type(ball_addr) is not int
                                or not 0x90000000 <= record_addr <= 0x94000000 - RECORD_WORDS * 4
                                or not 0x90000000 <= ball_addr <= 0x94000000 - 0x3C):
                            raise ValueError("A probe selected record/ball range invalid")
                        candidate = tuple(rpc.call("memory.read_u32", [record_addr + i * 4])
                                          for i in range(RECORD_WORDS))
                        if any(type(bit) is not int or not 0 <= bit <= 0xFFFFFFFF for bit in candidate):
                            raise ValueError("A probe raw selected record invalid")
                        if not source_gate(rpc, tuple(actor)):
                            raise ValueError("A probe source epoch changed")
                        # The source-gated base packet was sampled BEFORE the
                        # 51-word scan: a moving ball/aim could otherwise be
                        # misclassified as an A transition.
                        ball_after = tuple(rpc.call("memory.read_u32", [ball_addr + 0x30 + 4*i])
                                           for i in range(3))
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
                    sample = Sample(index, "LIVE", index, start, end, words, owner_digest,
                                    True, "Read-only non-atomic source-qualified host sample", "complete", tuple(frames))
                    clock.append(time.monotonic())
                    rate = (len(clock) - 1) / (clock[-1] - clock[0]) if len(clock) >= 2 and clock[-1] > clock[0] else 0.0
                    self._emit(LiveEvent("sample", sample, int(actor[13]), int(actor[5]), rate,
                                         a_record=a_words, a_read_start_ns=probe_start))
                    index += 1
                    self.stop_event.wait(self.pause)
            self._emit(LiveEvent("disconnected", reason="Operator stopped or bridge closed"))
        except (OSError, ValueError, RuntimeError, TypeError, KeyError, ImportError, TimeoutError, PermissionError, IndexError) as exc:
            # Avoid leaking dynamic guest pointers or local private file paths into UI.
            self._emit(LiveEvent("error", reason=f"Read-only source/bridge failure ({type(exc).__name__}). No automatic retry."))
