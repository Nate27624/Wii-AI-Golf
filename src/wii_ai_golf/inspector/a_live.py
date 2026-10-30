"""Automatic, conservative source-scoped A button *candidate* for UI only.

Published #396 blind study found these eight selected-player record offsets
correlated with human HELD vs RELEASED labels in one session (3/3 blind), not
an independently typed game-owned button latch. No input, no prompts, no
hardcoded human's private RAM words. An automatic fallback assumes A is
RELEASED for the first two stable, idle samples after Connect. Do not use for
training, frame synchronization, contacts, or controlling a real player.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .a_reference import AReference, PassiveAIndicator

PUBLISHED_OFFSETS = (0x74, 0x94, 0x9C, 0xA0, 0xA8, 0xB0, 0xB8, 0xC0)


@dataclass
class LiveAIndicator:
    reference: AReference | None = None
    base: tuple[int, ...] | None = None
    context: tuple[str, tuple[int, ...], tuple[int, ...]] | None = None
    recent: list[tuple[int, ...]] = field(default_factory=list)
    mode: str = "awaiting first released samples"
    blocked: bool = False
    private: PassiveAIndicator = field(init=False)

    def __post_init__(self) -> None:
        self.private = PassiveAIndicator(self.reference)

    def clear(self) -> None:
        self.base = None
        self.context = None
        self.recent.clear()
        self.mode = "awaiting first released samples"
        self.blocked = False
        self.private.clear()

    def observe(self, record: tuple[int, ...] | None, source: str | None,
                ball: tuple[int, ...] | None, aim: tuple[int, ...] | None) -> str:
        if self.blocked:
            self.mode = 'selected scene/actor changed: reconnect for source safety'
            return 'UNKNOWN'
        if not source or record is None or type(record) is not tuple or len(record) != 51 or any(
                type(x) is not int or not 0 <= x <= 0xFFFFFFFF for x in record):
            self.mode = 'missing qualified A record'
            self.recent.clear()
            return 'UNKNOWN'
        if type(ball) is not tuple or type(aim) is not tuple or not ball or len(aim) != 1:
            self.mode = 'missing stable source/ball/aim'
            self.recent.clear()
            return 'UNKNOWN'
        ctx = (source, ball, aim)
        if self.context is None:
            self.context = ctx
        elif source != self.context[0]:
            # A new actor/scene/selected owner invalidates all previous A
            # candidate evidence; never silently rebootstrap from held state.
            self.blocked = True
            self.recent.clear()
            self.mode = 'selected scene/actor changed: reconnect for source safety'
            return 'UNKNOWN'
        elif (ball, aim) != self.context[1:]:
            # Ball trajectories and aim adjustments are NORMAL play, not
            # evidence of a changed selected player. Do not permanently lock
            # the A display or infer a new RELEASED baseline from motion.
            # Only classify again after consecutive stable new readings.
            self.context = ctx
            self.recent.clear()
            self.private.clear()
            self.mode = 'ball/aim moved: waiting for stable A candidate readings'
            return 'UNKNOWN'

        if self.reference is not None and source == self.reference.source_digest:
            exact = self.private.observe(record, source, ball, aim)
            if exact != 'UNKNOWN':
                self.mode = 'SHA-verified prior trial (same source)'
                return exact
        # Automatic *session-local*, no-controller baseline. This is a pattern
        # discriminator only; if operator connected while holding A, the
        # RELEASED assumption is wrong. First 2 stable reads must be obtained
        # after connection while A is actually released.
        vector = tuple(record[o//4] for o in PUBLISHED_OFFSETS)
        self.recent.append(vector)
        self.recent[:] = self.recent[-2:]
        if len(self.recent) < 2 or self.recent[-1] != self.recent[-2]:
            self.mode = 'waiting for two identical source-scoped reads'
            return 'UNKNOWN'
        if self.base is None:
            self.base = vector
            self.mode = 'automatic baseline (assumed A released at Connect)'
            return 'RELEASED'
        if vector == self.base:
            self.mode = 'auto eight-offset baseline match (candidate)'
            return 'RELEASED'
        if all(a != b for a, b in zip(vector, self.base)):
            self.mode = 'auto eight-offset synchronized change (candidate)'
            return 'PRESSED'
        self.mode = 'partial A signature; abstaining'
        return 'UNKNOWN'
