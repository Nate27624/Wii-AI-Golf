"""Offline-only audit of an existing V1/B1 lead-to-trace timing receipt.

Does not connect to Dolphin, start/stop a shot, inspect RAM, or claim that an
emulator bridge frame equals a guest physics step or game-recognized button A.
The launch and swing APIs remain under S001/S002/S000 ownership.
"""
from __future__ import annotations

from typing import Any, Mapping

# Original canonical 89-sample forward trace; absolute ticks are BRIDGE ticks.
# Changing these boundaries requires a new waveform identity/study.
V1_PHASES = (
    ("neutral_A", 0, 12),
    ("backswing_A", 12, 27),
    ("forward_A", 27, 47),
    ("followthrough_A", 47, 77),
    ("released_A", 77, 89),
)


def audit_b1_timing_receipt(child: Mapping[str, Any]) -> dict[str, Any]:
    """Return an allowlisted timing explanation, never a shot-success verdict.

    Input is the existing locally recorded child summary (not raw RAM).
    Missing/contradictory counters ABSTAIN; complete trace+counter arithmetic
    proves only a plausible bridge-dispatch timeline, not game-side contact.
    """
    result: dict[str, Any] = {
        "kind": "offline_v1_b1_bridge_timing_audit",
        "status": "abstain_missing_or_incomplete_receipt",
        "game_a_latch_verified": False,
        "guest_physics_frame_join_verified": False,
        "ball_contact_verified": False,
        "training_allowed": False,
    }
    if not isinstance(child, Mapping):
        return result
    request, trace = child.get("known_good_swing_request"), child.get("swing_dispatch")
    if not isinstance(request, Mapping) or not isinstance(trace, Mapping):
        return result
    if (request.get("preset") != "forward"
            or request.get("generated_trace_frames") != 89
            or trace.get("total_frames") != 89):
        result["status"] = "abstain_not_original_89_sample_forward_trace"
        return result
    if trace.get("state") != "complete" or trace.get("applied_frames") != 89:
        return result
    keys = {
        "lead_requested": request.get("a_lead_requested_frames"),
        "lead_observed": request.get("a_lead_observed_frame_delta"),
        "lead_start": request.get("a_lead_start_frame"),
        "lead_last": request.get("a_lead_last_observed_frame"),
        "trace_start": trace.get("start_frame"),
        "trace_completion": trace.get("completion_dispatch_frame"),
    }
    if any(type(v) is not int or v < 0 for v in keys.values()):
        return result
    if keys["lead_requested"] not in (45, 90):
        result["status"] = "abstain_unreviewed_A_lead"
        return result
    if (request.get("a_button_only_prime_requests") != 1
            or request.get("a_button_prime_applied") is not True
            or request.get("a_priming_evidence") !=
            "frame_observed_A_requested_not_game_verified"):
        return result
    if (keys["lead_last"] - keys["lead_start"] != keys["lead_observed"]
            or keys["lead_observed"] < keys["lead_requested"]
            or keys["trace_start"] <= keys["lead_last"]
            or keys["trace_completion"] < keys["trace_start"] + 89):
        result["status"] = "abstain_contradictory_bridge_counters"
        return result
    gap = keys["trace_start"] - keys["lead_last"] - 1
    result.update({
        "status": "bridge_counter_arithmetic_consistent_only",
        "requested_A_lead_bridge_frames": keys["lead_requested"],
        "observed_A_lead_bridge_frames": keys["lead_observed"],
        "unobserved_bridge_ticks_before_trace_start": gap,
        "trace_start_bridge_frame": keys["trace_start"],
        "trace_completion_bridge_frame": keys["trace_completion"],
        "trace_complete_dispatch_frames": 89,
        "trace_A_requested_samples": 77,
        "trace_A_released_samples": 12,
        "phase_start_bridge_frames": {
            name: keys["trace_start"] + begin for name, begin, _ in V1_PHASES
        },
        "note": "Bridge counters and requested controller samples, not "
                "game-applied frames, observed input latch, or ball contact.",
    })
    return result
