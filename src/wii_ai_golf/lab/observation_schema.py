"""S002 human-observation publication schema, independent of capture internals.

Only explicitly enumerated scalar facts leave the private research directory.
This module makes NO network requests and can be adopted by the result publisher.
"""
from __future__ import annotations
import hashlib
import math
import re

HEX64 = re.compile(r"^[0-9a-f]{64}$")
LABELS = {"yes", "no", "unknown"}
UNITS = {"ft", "m", "yd", "unknown"}


def observation_v1(candidate: dict) -> dict:
    if not isinstance(candidate, dict):
        raise ValueError("S002 candidate must be a mapping")
    human = candidate.get("human_observation")
    swing = candidate.get("known_good_swing_request")
    if not isinstance(human, dict) or not isinstance(swing, dict):
        raise ValueError("Missing known S002 observation/trace records")
    contact = human.get("contact_human", "unknown")
    green = human.get("finished_on_green_human", "unknown")
    if contact not in LABELS or green not in LABELS:
        raise ValueError("Invalid human observation")
    unit = human.get("displayed_unit_human", "unknown")
    if unit not in UNITS:
        raise ValueError("Unsupported displayed-distance unit")
    distance = human.get("displayed_distance_human")
    if distance in (None, ""):
        distance = None
        unit = "unknown"
    else:
        if type(distance) not in (str, int, float):
            raise ValueError("Untrusted distance")
        try:
            value = float(distance)
        except (ValueError, OverflowError) as exc:
            raise ValueError("Distance must be numeric") from exc
        if not math.isfinite(value) or not 0 <= value <= 100000 or unit == "unknown":
            raise ValueError("Distance out of range or without units")
        distance = round(value, 3)
    trace = swing.get("trace_sha256")
    if not isinstance(trace, str) or not HEX64.fullmatch(trace):
        raise ValueError("Missing verifiable trace SHA-256")
    prime = swing.get("a_button_only_prime_requests")
    if prime is not None and (type(prime) is not int or not 0 <= prime <= 180):
        raise ValueError("Invalid A-prime request count")
    # Hash private trace fingerprint into a stable sanitized observation ID.
    basis = (trace + "|" + contact + "|" + green + "|" + str(distance) +
             "|" + unit + "|" + str(prime)).encode("ascii")
    return {"schema_version": 1, "record_type": "human_observation",
            "observation_id": hashlib.sha256(basis).hexdigest(),
            "contact_human": contact, "green_human": green,
            "distance_human": distance, "distance_unit_human": unit,
            "trace_sha256": trace, "a_prime_requests": prime,
            "verified_game_score": False,
            "claim": "HUMAN_LABELS_ONLY_NOT_VERIFIED_GAME_SCORE"}
