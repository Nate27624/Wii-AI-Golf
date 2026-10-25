"""Research-only S001/S002 event-frame timing oracle; NO live capture or power decoding.

The input describes an *untrusted declaration* of bridge-side frame markers and
bounded source-reviewed RAM reads. This checks internal consistency only.
An observed bridge callback is NOT proof of game-recognized input, player
identity, physical contact, or numeric in-game power.
"""
from __future__ import annotations

from math import ceil
import re

PHASES = ("pre_a", "a_hold", "backswing", "forward", "follow_through", "release", "post")
REQUIRED_READS = frozenset(("a_hold", "backswing", "forward", "follow_through"))
FIELDS = frozenset((
    "schema_version", "kind", "game_id", "revision", "game_mode", "boot_id",
    "shot_id", "bridge_sha256", "trace_sha256", "event_provenance", "events", "reads",
))
EVENT_FIELDS = frozenset(("phase", "emulated_frame", "a_requested"))
READ_FIELDS = frozenset(("phase", "frame_start", "frame_end"))
MAX_READS = 80
MAX_SPAN = 240


def _frame(x: object) -> bool:
    return type(x) is int and 0 <= x <= 2**31 - 1


def _token(x: object) -> bool:
    return type(x) is str and re.fullmatch(r"[A-Za-z0-9_-]{8,64}", x) is not None


def _digest(x: object) -> bool:
    return type(x) is str and re.fullmatch(r"[0-9a-f]{64}", x) is not None


def audit_bridge_timing_fixture(record: dict) -> dict:
    """Fail closed on fabricated frame overlap/unsafe fields; report TIMING only.

    This is a proposed producer fixture schema, not an approved publication kind
    and not a substitute for S003's strict same-shot join (#123).
    """
    if type(record) is not dict or set(record) != FIELDS:
        raise ValueError("Unreviewed or missing timing fixture fields")
    if (type(record["schema_version"]) is not int or record["schema_version"] != 1
        or record["kind"] != "proposed-bridge-timing-fixture"
        or record["game_id"] != "RSPE01" or type(record["revision"]) is not int
        or record["revision"] != 1 or type(record["game_mode"]) is not int
        or record["game_mode"] != 4 or not _token(record["boot_id"])
        or not _token(record["shot_id"]) or not _digest(record["bridge_sha256"])
        or not _digest(record["trace_sha256"])):
        raise ValueError("Invalid gameplay or opaque same-shot provenance")
    if record["event_provenance"] != "bridge_callback_emulated_frame":
        raise ValueError("Client RPC acknowledgements are not bridge frame anchors")

    events = record["events"]
    if type(events) is not list or len(events) != len(PHASES):
        raise ValueError("Need exactly seven predeclared phase events")
    timeline = {}
    prior = -1
    expected_a = (False, True, True, True, True, False, False)
    for phase, a, event in zip(PHASES, expected_a, events):
        if (type(event) is not dict or set(event) != EVENT_FIELDS
            or event["phase"] != phase or not _frame(event["emulated_frame"])
            or event["emulated_frame"] <= prior
            or type(event["a_requested"]) is not bool
            or event["a_requested"] is not a):
            raise ValueError("Phase order, emulated frame or requested A continuity invalid")
        prior = event["emulated_frame"]
        timeline[phase] = prior

    reads = record["reads"]
    if type(reads) is not list or not 1 <= len(reads) <= MAX_READS:
        raise ValueError("Bounded phase-bracketed watchlist reads required")
    prior_end = -1
    counts = {p: 0 for p in PHASES}
    spans = []
    for read in reads:
        if type(read) is not dict or set(read) != READ_FIELDS:
            raise ValueError("Unsafe or incomplete watchlist read")
        phase, start, end = read["phase"], read["frame_start"], read["frame_end"]
        if (phase not in PHASES or not _frame(start) or not _frame(end)
            or start > end or end - start > MAX_SPAN or start < prior_end):
            raise ValueError("Invalid or overlapping emulated-frame brackets")
        if start < timeline[phase]:
            raise ValueError("Read begins before its declared phase")
        index = PHASES.index(phase)
        if index + 1 < len(PHASES) and end >= timeline[PHASES[index + 1]]:
            raise ValueError("Read crosses a controller phase boundary")
        # There is no next event after 'post'. Do not silently infer a shot end
        # or a ball-settlement frame from this last stage marker.
        prior_end = end
        counts[phase] += 1
        spans.append(end - start)

    ordered = sorted(spans)
    p95 = ordered[ceil(0.95 * len(ordered)) - 1]
    missing = sorted(REQUIRED_READS - {k for k, n in counts.items() if n})
    timing_ok = not missing and p95 <= 2 and max(spans) <= 2
    return {
        "kind": "bridge-timing-fixture-audit", "schema_version": 1,
        "read_count": len(spans), "read_span_p95": p95, "read_span_max": max(spans),
        "missing_essential_phases": missing,
        "timing_fixture_passes": timing_ok,
        "reason": ("timing_only_no_physics_claim" if timing_ok else
                   "missing_essential_phase_reads" if missing else "non_atomic_reads_too_slow"),
        "bridge_source_independently_verified": False,
        "game_applied_input_verified": False, "club_object_verified": False,
        "game_power_verified": False, "physical_contact_verified": False,
        "same_shot_link_verified": False, "observer_noninterference_verified": False,
        "ready_for_power_regression": False,
    }
