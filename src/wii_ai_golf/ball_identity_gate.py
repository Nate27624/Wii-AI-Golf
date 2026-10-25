"""Evidence gate: block camera-sensitive transforms from ball-training labels.

This registry is a *negative* evidence ledger; no positive ball identity is inferred.
"""
from __future__ import annotations
from typing import Any

CAMERA_SENSITIVE = "0x925834D8"
CAMERA_OBJECT_BASE = "0x92583488"
NEGATIVE_CONTROL_RUN = "20261025T001441Z-edf86056"


def classify_candidate(address: str, conditions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Use matched idle / aim-only / swing summaries; never certify actual ball."""
    addr = str(address).upper()
    required = ("idle", "aim_only", "swing")
    missing = [v for v in required if v not in conditions]
    if missing:
        return {"address":addr,"training_eligible":False,
                "decision":"INSUFFICIENT_CONTROLS","missing":missing}
    counts = {}
    for name in required:
        data=conditions[name]
        n=data.get("samples_parsed")
        moves=data.get("moving_steps_below_reset")
        if type(n) is not int or type(moves) is not int or n < 1 or moves < 0 or moves > n:
            raise ValueError("invalid aggregate evidence for "+name)
        counts[name]={"samples":n,"moves":moves,"rate":round(moves/n,4)}
    camera_sensitive=counts["aim_only"]["moves"] >= 2 and counts["idle"]["moves"] == 0
    return {"address":addr,"training_eligible":False,
            "decision":("CAMERA_OR_AIM_SENSITIVE" if camera_sensitive else
                        "UNVERIFIED_REQUIRES_VISUAL_PHYSICS_IDENTITY"),
            "condition_metrics":counts,
            "warning":"No candidate is training-eligible without independent visual/physics verification"}


def known_rejected_candidate() -> dict[str, Any]:
    """The no-swing aim-control falsified a camera-invariant ball-world-position label."""
    return {"address":CAMERA_SENSITIVE,"object_base":CAMERA_OBJECT_BASE,
            "status":"EXCLUDE_AS_WORLD_BALL_GROUND_TRUTH",
            "reason":"Changes under aim/camera manipulation without swing",
            "negative_control_run":NEGATIVE_CONTROL_RUN,
            "training_eligible":False}
