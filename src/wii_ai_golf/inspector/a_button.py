"""Source-scoped, operator-calibrated A-state candidate, NOT a native A latch.

No RPC, guest writes, controller commands, persistence or automatic labels.
The operator supplies seven held/released windows; three read-only stable record
samples per window. Four calibration windows fit stable words and three withheld
windows must predict correctly, as in the separate #396 blind study.  An
ambiguous/changed field yields UNKNOWN, never a guessed binary state.
"""
from __future__ import annotations
from dataclasses import dataclass, field

SEQUENCE = ("R0", "H0", "R1", "H1", "R2", "H2", "R3")
LABELS = {phase: ("PRESSED" if phase.startswith("H") else "RELEASED") for phase in SEQUENCE}
RECORD_WORDS = 51
WINDOW_SIZE = 3


def stable_values(rows: list[tuple[int, ...]]) -> tuple[int | None, ...]:
    if len(rows) != WINDOW_SIZE or any(type(row) is not tuple or len(row) != RECORD_WORDS
                                      or any(type(v) is not int or not 0 <= v <= 0xFFFFFFFF for v in row)
                                      for row in rows):
        raise ValueError("invalid A study candidate words")
    return tuple(rows[0][i] if all(r[i] == rows[0][i] for r in rows) else None
                 for i in range(RECORD_WORDS))


def classify(record: tuple[int, ...] | None, model: tuple[tuple[int, int, int], ...]) -> str:
    if not model or record is None or type(record) is not tuple or len(record) != RECORD_WORDS:
        return "UNKNOWN"
    votes = []
    for i, released, pressed in model:
        if type(record[i]) is not int:
            return "UNKNOWN"
        votes.append("PRESSED" if record[i] == pressed else "RELEASED" if record[i] == released else "UNKNOWN")
    return votes[0] if votes[0] != "UNKNOWN" and len(set(votes)) == 1 else "UNKNOWN"


@dataclass
class AButtonStudy:
    """Explicit operator-staged, same-source/aim/ball state classifier."""
    windows: dict[str, list[tuple[int, ...]]] = field(default_factory=dict)
    phase_index: int = 0
    armed_since_ns: int | None = None
    phase_active: bool = False
    identity: tuple[str, tuple[int, ...], tuple[int, ...]] | None = None
    model: tuple[tuple[int, int, int], ...] = ()
    verified: bool = False
    history: list[str] = field(default_factory=list)
    failure: str = ""

    @property
    def next_phase(self) -> str | None:
        return SEQUENCE[self.phase_index] if self.phase_index < len(SEQUENCE) else None

    def arm(self, start_ns: int) -> str:
        if self.verified or self.failure or self.phase_active or self.next_phase is None:
            raise ValueError("reset the A study or finish current window")
        if type(start_ns) is not int or start_ns <= 0:
            raise ValueError("invalid host time")
        self.armed_since_ns = start_ns
        self.phase_active = True
        self.windows[self.next_phase] = []
        return self.next_phase

    def observe(self, record: tuple[int, ...] | None, source: str,
                ball: tuple[int, ...] | None, aim: tuple[int, ...] | None,
                read_start_ns: int) -> str:
        """Return window progress; does not infer A without all 7 windows."""
        if not self.phase_active or self.next_phase is None:
            return "not collecting"
        if read_start_ns < self.armed_since_ns:
            return "waiting for a new source-qualified read"
        if record is None or ball is None or aim is None or not source:
            return "waiting for stationary source-qualified A sample"
        if type(record) is not tuple or len(record) != RECORD_WORDS or any(
            type(x) is not int or not 0 <= x <= 0xFFFFFFFF for x in record
        ):
            return "waiting for valid 51-word record"
        context = (source, ball, aim)
        if self.identity is None:
            self.identity = context
        elif context != self.identity:
            self.invalidate("scene/aim/ball context changed during A calibration")
            return self.failure
        phase = self.next_phase
        self.windows[phase].append(record)
        n = len(self.windows[phase])
        if n < WINDOW_SIZE:
            return f"{phase}: {n}/{WINDOW_SIZE} candidate reads"
        self.phase_active = False
        self.armed_since_ns = None
        self.phase_index += 1
        if self.next_phase is not None:
            return f"{phase}: captured; next {self.next_phase}"
        self._finish()
        return "7 windows passed held-out calibration" if self.verified else self.failure

    def _finish(self) -> None:
        try:
            stable = {key: stable_values(self.windows[key]) for key in SEQUENCE}
        except (KeyError, ValueError):
            self.invalidate("invalid or missing A calibration windows")
            return
        model = []
        for i in range(RECORD_WORDS):
            r0, r1 = stable["R0"][i], stable["R1"][i]
            h0, h1 = stable["H0"][i], stable["H1"][i]
            if None not in (r0, r1, h0, h1) and r0 == r1 and h0 == h1 and r0 != h0:
                model.append((i, r0, h0))
        candidate = tuple(model)
        for phase in ("R2", "H2", "R3"):
            observed = stable[phase]
            # Every selected offset must be stable in heldout.
            if any(observed[i] is None for i, _, _ in candidate) or classify(
                tuple(-1 if v is None else v for v in observed), candidate
            ) != LABELS[phase]:
                self.invalidate("held-out validation disagreed or was unstable")
                return
        if not candidate:
            self.invalidate("no stable repeated A discriminator")
            return
        self.model = candidate
        self.verified = True

    def invalidate(self, reason: str) -> None:
        self.failure = reason
        self.model = ()
        self.verified = False
        self.phase_active = False
        self.armed_since_ns = None
        self.history.clear()

    def predict(self, record: tuple[int, ...] | None, source: str,
                ball: tuple[int, ...] | None, aim: tuple[int, ...] | None) -> str:
        if not self.verified or (source, ball, aim) != self.identity:
            self.history.clear()
            return "UNKNOWN"
        state = classify(record, self.model)
        if state == "UNKNOWN":
            self.history.clear()
            return state
        self.history.append(state)
        self.history[:] = self.history[-2:]
        return state if len(self.history) == 2 and len(set(self.history)) == 1 else "UNKNOWN"
