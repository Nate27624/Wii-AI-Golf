"""Client for the EXPERIMENTAL version-pinned atomic Felk bridge extension."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Protocol, Sequence


class RPCTransport(Protocol):
    def call(self, method: str, params: list[Any] | None = None) -> Any: ...


@dataclass(frozen=True)
class AtomicSample:
    a: bool
    accel: tuple[float, float, float]

    def __post_init__(self) -> None:
        if type(self.a) is not bool or len(self.accel) != 3:
            raise ValueError("a must be bool and accel a 3-tuple")
        if not all(type(v) in (float, int) and math.isfinite(v) and abs(v) <= 16 for v in self.accel):
            raise ValueError("accel must be finite within +-16 approx g")


class AtomicTraceClient:
    """No data extraction. Handles only frame batch submit/status/abort."""

    def __init__(self, rpc: RPCTransport, port: int = 0, max_polls: int = 900) -> None:
        if type(port) is not int or port not in range(4):
            raise ValueError("port must be 0..3")
        if max_polls < 1:
            raise ValueError("max_polls must be positive")
        self.rpc = rpc
        self.port = port
        self.max_polls = max_polls

    def submit(self, samples: Sequence[AtomicSample]) -> dict[str, Any]:
        if not 1 <= len(samples) <= 600:
            raise ValueError("1..600 frame samples required")
        payload = [[s.a, *s.accel] for s in samples]
        reply = self.rpc.call("trace.submit", [self.port, payload])
        if not isinstance(reply, dict) or reply.get("state") != "scheduled":
            raise RuntimeError("Invalid atomic trace acknowledgement")
        return reply

    def status(self) -> dict[str, Any]:
        result = self.rpc.call("trace.status", [])
        if not isinstance(result, dict) or "state" not in result:
            raise RuntimeError("Invalid trace status")
        return result

    def abort(self) -> dict[str, Any]:
        result = self.rpc.call("trace.abort", [])
        if not isinstance(result, dict):
            raise RuntimeError("Invalid abort acknowledgement")
        return result

    def run(self, samples: Sequence[AtomicSample]) -> dict[str, Any]:
        initial = self.submit(samples)
        try:
            for _ in range(self.max_polls):
                status = self.status()
                if status.get("id") != initial.get("id"):
                    raise RuntimeError("Trace ID changed during execution")
                if status["state"] == "complete":
                    if status.get("applied_frames") != len(samples):
                        raise RuntimeError("Incomplete trace despite completion status")
                    return status
                if status["state"] not in ("scheduled", "running"):
                    raise RuntimeError(f"Trace failed: {status['state']}")
            raise TimeoutError("Trace did not complete within bounded polls; emulator may be paused")
        except Exception:
            try:
                self.abort()
            except Exception:
                pass
            raise
