"""Run a bridge-callback 45-frame A-only lead plus frozen 89-frame swing.

One atomic scheduled action, no host-side frame-count polling between phases.
The loaded bridge must acknowledge this exact opt-in capability *before* input.
"""
from __future__ import annotations

from typing import Any, Sequence

from .swing_client import SwingSample, SwingTraceClient


class AtomicA45SwingTraceClient(SwingTraceClient):
    @staticmethod
    def require_capability(rpc: Any) -> None:
        try:
            status = rpc.call("trace.atomic_a45_capabilities", [])
        except Exception as exc:
            raise RuntimeError(
                "Loaded Dolphin bridge lacks atomic A45. Do not swing with stale V1."
            ) from exc
        if (type(status) is not dict
                or status.get("atomic_a45_protocol") != 1
                or status.get("lead_frames") != 45
                or status.get("button_only_lead") is not True
                or status.get("atomic_swing_followup") is not True):
            raise RuntimeError("Atomic A45 bridge capability mismatch; no swing")

    def submit(self, samples: Sequence[SwingSample]) -> dict[str, Any]:
        if len(samples) != 89 or any(not isinstance(s, SwingSample) for s in samples):
            raise ValueError("Atomic A45 requires frozen 89-frame SwingSample trace")
        if any(s.hold_a is not (i < 77) for i, s in enumerate(samples)):
            raise ValueError("Atomic A45 requires 77-held/12-released original A pattern")
        payload = [
            [s.hold_a, *s.direction, s.distance_m,
             s.speed_m_s, s.return_speed_m_s, s.angle_rad]
            for s in samples
        ]
        status = self.rpc.call("trace.submit_atomic_a45", [self.port, payload])
        if (type(status) is not dict or status.get("state") != "scheduled"
                or status.get("kind") != "atomic_a45_swing"
                or status.get("prehold_requested_frames") != 45
                or status.get("applied_frames") != 0
                or type(status.get("id")) is not int):
            raise RuntimeError("Atomic A45 schedule acknowledgement invalid")
        return status

    def run(self, samples: Sequence[SwingSample]) -> dict[str, Any]:
        self.require_capability(self.rpc)
        result = super().run(samples)
        if (type(result.get("prehold_applied_frames")) is not int
                or result["prehold_applied_frames"] != 45
                or result.get("kind") != "atomic_a45_swing"
                or type(result.get("prehold_start_frame")) is not int
                or type(result.get("last_prehold_frame")) is not int
                or type(result.get("trace_start_frame")) is not int
                or result["last_prehold_frame"] != result["prehold_start_frame"] + 44
                or result["trace_start_frame"] != result["prehold_start_frame"] + 45
                or result.get("game_a_recognition_verified") is not False):
            raise RuntimeError("Atomic A45 completion receipt incomplete/inconsistent")
        return result
