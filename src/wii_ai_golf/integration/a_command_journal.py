"""Private client-side controller RPC journal for S001 continuity diagnosis.

This records outgoing RPC requests and acknowledgements, not actual game input.
No controller commands are added or reordered.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .a_continuity_audit import ButtonEvent, audit_a_continuity


class ACommandJournal:
    def __init__(self, rpc: Any):
        self.rpc = rpc
        self.events: list[ButtonEvent] = []
        self.requests: list[dict] = []
        self.uncertain = False
        self._idx = 0

    def _event(self, phase: str, a: bool) -> None:
        self.events.append(ButtonEvent(phase, self._idx, a))
        self._idx += 1

    def call(self, method: str, params: Any = None) -> Any:
        tracked = method in ("controller.set_wiimote_buttons", "trace.submit_swing",
                             "trace.status", "trace.abort")
        record = {"method": method, "ack": "pending"} if tracked else None
        if record is not None:
            self.requests.append(record)
        try:
            result = self.rpc.call(method, params)
        except BaseException:
            if record is not None:
                record["ack"] = "error"
                self.uncertain = True
            raise
        if record is not None:
            record["ack"] = "returned"
            if method == "trace.submit_swing":
                record["state"] = result.get("state") if isinstance(result, dict) else "invalid"
                if not isinstance(result, dict) or result.get("state") != "scheduled":
                    self.uncertain = True
            if method == "trace.status":
                record["state"] = result.get("state") if isinstance(result, dict) else "invalid"
                if not isinstance(result, dict) or result.get("state") not in ("scheduled", "running", "complete"):
                    self.uncertain = True
            if method == "trace.abort":
                self.uncertain = True
        if method == "controller.set_wiimote_buttons":
            try:
                held = params[1]["A"]
                if type(held) is not bool:
                    raise ValueError
                self._event("prehold" if held else "release", held)
            except (TypeError, KeyError, IndexError, ValueError):
                self.uncertain = True
        elif method == "trace.submit_swing":
            try:
                samples = params[1]
                if len(samples) != 89:
                    self.uncertain = True
                for index, sample in enumerate(samples):
                    a = sample[0]
                    if type(a) is not bool:
                        raise ValueError("nonboolean A state")
                    phase = ("setup" if index < 12 else "backswing" if index < 27 else
                             "forward" if index < 47 else "follow_through" if index < 77 else "release")
                    self._event(phase, a)
            except (TypeError, ValueError, IndexError):
                self.uncertain = True
        return result

    def report(self) -> dict:
        # An RPC response is not evidence that in-game inputs were applied.
        result = audit_a_continuity(self.events)
        if self.uncertain or not any(r["method"] == "trace.status" and r.get("state") == "complete"
                                    for r in self.requests):
            result["status"] = "unknown"
            result["reason"] = "unverified_or_incomplete_rpc"
        return {"schema": 1, "provenance": "client_rpc_requests_and_returns_only",
                "game_a_recognition_verified": False, "continuity": result,
                "requests": self.requests}

    def save_private(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as handle:
            json.dump(self.report(), handle, indent=2, allow_nan=False)
            handle.write("\n")
