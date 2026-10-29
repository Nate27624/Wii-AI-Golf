"""Offline-only canonical V1 trace phase manifest for future SAME-SHOT RAM sampling.

This reads the existing S001 89-sample waveform; it does not build or send a
second trace. Sample indices are NOT validated elapsed/emulator frames, and
NONE of the labels implies game-side recognition or ball contact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from probe_swing import build_probe
from wii_ai_golf.integration.swing_client import SwingSample

PHASES = ("a_held_neutral", "backswing", "forward", "followthrough", "a_release")
LENGTHS = (12, 15, 20, 30, 12)
TOTAL = sum(LENGTHS)
PROBE_EVENT_INDICES = (0, 11, 12, 26, 27, 46, 47, 76, 77, 88)
# Published human-contact baseline, 1.0 speed, 1.0 backswing, A lead 45.
# research/observations/20261025T023456Z-15d1c97c12.json
EXPECTED_BASELINE_SHA256 = "b63a1818ba5086c64b0fe7338236a498240e4be97bbd111809a772d783699891"


def _phase(sample: SwingSample) -> str:
    if type(sample.hold_a) is not bool:
        raise ValueError("Invalid command-only A label")
    if not sample.hold_a:
        if sample.direction != (0.0, 0.0, 0.0) or (
            sample.distance_m or sample.speed_m_s or
            sample.return_speed_m_s or sample.angle_rad):
            raise ValueError("Release must have no commanded motion")
        return "a_release"
    if sample.direction == (0.0, -1.0, 0.0):
        return "backswing"
    if sample.direction == (0.0, 1.0, 0.0):
        return "forward"
    if sample.direction == (0.0, 0.0, 0.0) and not (
        sample.distance_m or sample.speed_m_s or
        sample.return_speed_m_s or sample.angle_rad):
        return "a_held_neutral"
    raise ValueError("Unregistered direction/phase; cannot plan live probe")


def _payload(samples):
    return [[s.hold_a, *s.direction, s.distance_m, s.speed_m_s,
             s.return_speed_m_s, s.angle_rad] for s in samples]


def plan(samples: list[SwingSample], *, observed_a_lead_requested: int = 45):
    if type(observed_a_lead_requested) is not int or observed_a_lead_requested != 45:
        raise ValueError("Only the operator-tested 45-frame A lead is preregistered")
    if not isinstance(samples, list) or len(samples) != TOTAL:
        raise ValueError("Not the frozen 89-sample V1 trace")
    if any(type(sample) is not SwingSample for sample in samples):
        raise ValueError("Unexpected waveform sample type")
    classes = [_phase(sample) for sample in samples]
    intervals = []
    start = 0
    while start < len(classes):
        end = start + 1
        while end < len(classes) and classes[end] == classes[start]:
            end += 1
        intervals.append((classes[start], start, end - 1))
        start = end
    # Direction alone cannot distinguish a_held_neutral versus followthrough.
    if [x[0] for x in intervals] != [
        "a_held_neutral", "backswing", "forward", "a_held_neutral", "a_release"
    ]:
        raise ValueError("Unexpected command phase order")
    if tuple(last - first + 1 for _, first, last in intervals) != LENGTHS:
        raise ValueError("Unexpected phase lengths in source waveform")
    named = [{"phase": PHASES[i], "sample_start_zero_based": first,
              "sample_end_zero_based": last, "commanded_hold_a": i < 4}
             for i, (_, first, last) in enumerate(intervals)]
    events = [
        {"sample_index_zero_based": index,
         "phase": next(p["phase"] for p in named if
                       p["sample_start_zero_based"] <= index <= p["sample_end_zero_based"]),
         "marker_role": ("boundary" if index in (0, 12, 27, 47, 77) else "phase_end"),
         "memory_read_semantics": "pre_dispatch_if_added_to_bridge_tick"}
        for index in PROBE_EVENT_INDICES
    ]
    payload = _payload(samples)
    fingerprint = hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()
    if fingerprint != EXPECTED_BASELINE_SHA256:
        raise ValueError("Trace digest differs from approved human-contact V1 baseline")
    return {
        "schema_version": 1,
        "kind": "offline_v1_swing_memory_event_manifest",
        "study_id": "S001-S002-SAME-SHOT-MEMORY-PREFLIGHT",
        "trace_source": "canonical_probe_swing.build_probe_forward",
        "trace_sha256": fingerprint,
        "trace_samples": TOTAL,
        "button_only_a_lead_requested_frames": observed_a_lead_requested,
        "a_lead_game_verified": False,
        "game_frame_alignment_verified": False,
        "golf_power_field_verified": False,
        "phases": named,
        "proposed_tick_read_markers": events,
        "warning": ("Commanded trace sample indices, NOT emulated frame timestamps "
                    "or game-applied A. Source/golfer RAM identity remains unverified; "
                    "any future in-bridge read must be opt-in, bounded, privacy-gated "
                    "and demonstrated not to perturb the known-good swing."),
    }


def main() -> int:
    manifest = plan(build_probe("forward", follow_through_frames=30,
                                a_setup_frames=12))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
