"""Observed source-qualified ball trails for the PRIVATE Wii Golf inspector.

Builds bounded, read-only history of selected Ball+0x30 positions from a
single source-owner digest. A trail is a polyline through *observed* source
positions; it is neither interpolated game physics nor a predicted shot.
Invalid, incomplete, owner-changing or discontinuous packets never get joined.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from .replay import BALL

if TYPE_CHECKING:
    from .replay import Sample

Point = tuple[float, float, float]
MAX_TRACE_SAMPLES = 180
MAX_SAMPLE_GAP_NS = 2_000_000_000


@dataclass(frozen=True)
class BallTrace:
    segments: tuple[tuple[Point, ...], ...] = ()
    source_qualified: bool = False
    sample_count: int = 0


def _valid_position(sample: "Sample") -> Point | None:
    if (sample.state != "complete" or not sample.source_qualified
            or not sample.source_digest):
        return None
    xyz = sample.vec(BALL)
    if (xyz is None or len(xyz) != 3
            or not all(math.isfinite(x) and abs(x) < 1e7 for x in xyz)):
        return None
    return xyz


def observed_ball_trace(samples: tuple["Sample", ...] | list["Sample"],
                        index: int | None = None) -> BallTrace:
    """Visible prefix only, never a future replay point or another owner.

    The most recent 180 samples are considered. Repeated stationary readings
    do not add duplicate vertices. Qualified source gaps, host sampling gaps
    and frame ordering regressions break the visible line. A changed source
    owner ends the historical cohort entirely.
    """
    if not samples:
        return BallTrace()
    if index is None:
        index = len(samples) - 1
    if type(index) is not int or not 0 <= index < len(samples):
        return BallTrace()
    selected = samples[index]
    if _valid_position(selected) is None:
        return BallTrace()
    owner = selected.source_digest
    start = max(0, index+1-MAX_TRACE_SAMPLES)
    # Only the uninterrupted suffix of THIS selected owner is eligible.
    # No joining when a capture happens to return to a previous pointer.
    for i in range(index, start-1, -1):
        if samples[i].source_digest != owner:
            start = i+1
            break
    completed: list[tuple[Point, ...]] = []
    active: list[Point] = []
    previous = None
    accepted = 0

    def flush() -> None:
        nonlocal active
        if len(active) >= 2:
            completed.append(tuple(active))
        active = []

    for sample in samples[start:index+1]:
        xyz = _valid_position(sample)
        if xyz is None:
            flush()
            previous = None
            continue
        if previous is not None:
            if (previous.end_ns is not None and sample.start_ns is not None
                    and (sample.start_ns < previous.start_ns
                         if previous.start_ns is not None else False)):
                flush()
            elif (previous.end_ns is not None and sample.start_ns is not None
                  and sample.start_ns-previous.end_ns > MAX_SAMPLE_GAP_NS):
                flush()
            elif (previous.frame_bracket is not None
                  and sample.frame_bracket is not None
                  and sample.frame_bracket[1] < previous.frame_bracket[0]):
                flush()
        if not active or xyz != active[-1]:
            active.append(xyz)
            accepted += 1
        previous = sample
    flush()
    return BallTrace(tuple(completed), True, accepted)
