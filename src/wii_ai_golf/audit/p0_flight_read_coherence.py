"""Pure, offline coherence check for source-aliased, non-atomic golf ball reads.

The selected ball +0x30 and nested +0x4C -> +0x30 readers can resolve to
the same address but return different values when sequentially sampled in
flight. Never infer two objects or game-frame velocity from such packets.
This module has no Dolphin, RAM, controller, filesystem, or network access.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence


class EvidenceAbstain(ValueError):
    """Unverifiable or contradictory evidence; never guess."""


_TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
_HEX32 = re.compile(r"^[0-9a-fA-F]{8}$")
_REQUIRED = frozenset({
    "sample_index", "run_token", "shot_token", "scene_token", "hole_token",
    "source_epoch_digest", "alias_attested", "start_ns", "end_ns",
    "selected_be32", "nested_be32", "cc_be32",
})


def _words(value: object, field: str) -> tuple[int, int, int]:
    if type(value) not in (list, tuple) or len(value) != 3:
        raise EvidenceAbstain(f"invalid_{field}")
    if not all(type(x) is str and _HEX32.fullmatch(x) for x in value):
        raise EvidenceAbstain(f"invalid_{field}")
    return (int(value[0], 16), int(value[1], 16), int(value[2], 16))


def audit_sequential_flight_reads(packets: Sequence[Mapping[str, object]]) -> dict:
    """Audit source-aliased non-atomic reads without promoting ball semantics.

    Upstream must independently source-qualify the SAME-address alias and
    shot/owner epoch. Per-packet host brackets are not guest physics frames.
    A CC word triple equal to a future current triple is a single-shot
    temporal pattern, never a verified landing prediction.
    """
    if type(packets) not in (list, tuple) or not 2 <= len(packets) <= 80:
        raise EvidenceAbstain("invalid_bounded_packet_count")

    validated = []
    first_identity = None
    prior_end = None
    durations = []
    for index, packet in enumerate(packets):
        if not isinstance(packet, Mapping) or frozenset(packet) != _REQUIRED:
            raise EvidenceAbstain("invalid_packet_schema")
        identity = tuple(packet[field] for field in (
            "run_token", "shot_token", "scene_token", "hole_token",
            "source_epoch_digest",
        ))
        if not all(type(x) is str and _TOKEN.fullmatch(x) for x in identity):
            raise EvidenceAbstain("invalid_identity_token")
        if first_identity is None:
            first_identity = identity
        elif identity != first_identity:
            raise EvidenceAbstain("run_shot_scene_hole_or_epoch_changed")
        if type(packet["sample_index"]) is not int or packet["sample_index"] != index:
            raise EvidenceAbstain("missing_or_reordered_sample")
        if packet["alias_attested"] is not True:
            raise EvidenceAbstain("same_address_alias_not_attested")
        start, end = packet["start_ns"], packet["end_ns"]
        if (type(start) is not int or type(end) is not int or start < 0
                or end <= start or (prior_end is not None and start < prior_end)):
            raise EvidenceAbstain("invalid_or_overlapping_host_brackets")
        durations.append((end - start) / 1_000_000)
        prior_end = end
        validated.append((
            _words(packet["selected_be32"], "selected_be32"),
            _words(packet["nested_be32"], "nested_be32"),
            _words(packet["cc_be32"], "cc_be32"),
        ))

    mismatches = [i for i, (current, nested, _) in enumerate(validated)
                  if current != nested]
    transitions = sum(validated[i][0] != validated[i - 1][0]
                      for i in range(1, len(validated)))
    forward_matches = []
    for i, (current, _, cache) in enumerate(validated[:-1]):
        if cache == current:
            continue
        for j in range(i + 1, len(validated)):
            if validated[j][0] == cache:
                forward_matches.append({
                    "cc_packet_index": i,
                    "later_current_packet_index": j,
                })
                break

    return {
        "status": "SOURCE_ALIASED_NONATOMIC_FLIGHT_CANDIDATE_ONLY",
        "packet_count": len(validated),
        "source_address_alias_claimed_by_upstream": True,
        "alias_independently_verified_here": False,
        "same_address_disagreement_packet_indices": mismatches,
        "non_atomic_mismatch_possible": bool(mismatches),
        "different_ball_objects_inferred": False,
        "selected_current_adjacent_packet_transitions": transitions,
        "cc_forward_exact_matches": forward_matches,
        "cc_forward_match_count": len(forward_matches),
        "single_shot_cache_prediction_verified": False,
        "guest_physics_step_verified": False,
        "rendered_actor_generation_verified": False,
        "game_contact_frame_verified": False,
        "host_packet_duration_max_ms": round(max(durations), 3),
        "physical_velocity_or_units_verified": False,
        "training_approved": False,
    }
