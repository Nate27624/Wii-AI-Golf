"""Named, auditable slot-based Dolphin savestate profiles.

A profile is a *local label* for a Felk savestate slot; it is not a copy of
an emulator savestate. Only the Felk Dolphin instance owns the actual bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Protocol

NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
# Felk scripting-preview4's savestate.pyi documents slots 0..99.
MAX_SLOT = 99


class RPCTransport(Protocol):
    def call(self, method: str, params: list[Any] | None = None) -> Any: ...


@dataclass(frozen=True)
class StateProfile:
    name: str
    slot: int
    description: str = ""
    game_id: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not NAME.fullmatch(self.name):
            raise ValueError("profile names must match [a-z][a-z0-9_-]{0,63}")
        if type(self.slot) is not int or not 0 <= self.slot <= MAX_SLOT:
            raise ValueError(f"Felk savestate slot must be 0..{MAX_SLOT}")
        if not isinstance(self.description, str) or len(self.description) > 512:
            raise ValueError("description must be at most 512 characters")
        if not isinstance(self.game_id, str) or len(self.game_id) > 64:
            raise ValueError("game_id must be at most 64 characters")


class StateCatalog:
    """Atomic JSON manifest; local state profiles are never game save files."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.profiles: dict[str, StateProfile] = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("profiles"), list):
                raise ValueError("unsupported savestate catalog schema")
            for record in data["profiles"]:
                self.add(StateProfile(**record))

    def add(self, profile: StateProfile) -> None:
        if profile.name in self.profiles:
            raise ValueError(f"profile already exists: {profile.name}")
        for other in self.profiles.values():
            if other.slot == profile.slot:
                raise ValueError(f"slot {profile.slot} already belongs to {other.name}")
        self.profiles[profile.name] = profile

    def get(self, name: str) -> StateProfile:
        try:
            return self.profiles[name]
        except KeyError as exc:
            raise ValueError(f"unknown savestate profile: {name}") from exc

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"schema_version": 1, "profiles": [vars(p) for p in sorted(self.profiles.values(), key=lambda x: x.name)]}
        target = self.path.with_name(self.path.name + ".tmp")
        try:
            with target.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(data, handle, indent=2)
                handle.write("\n")
            os.replace(target, self.path)
        finally:
            if target.exists():
                target.unlink()


class StateManager:
    def __init__(self, transport: RPCTransport) -> None:
        self.transport = transport

    def _preflight(self) -> None:
        info = self.transport.call("bridge.ping")
        if not isinstance(info, dict) or not isinstance(info.get("bridge_version"), str):
            raise RuntimeError("not connected to the expected Felk bridge")

    def request_capture(self, profile: StateProfile, *, allow_overwrite: bool = False) -> dict[str, Any]:
        if not allow_overwrite:
            raise ValueError("saving overwrites the target emulator slot; pass allow_overwrite=True")
        self._preflight()
        self.transport.call("savestate.save_to_slot", [profile.slot])
        return {"action": "capture_requested", "name": profile.name, "slot": profile.slot,
                "warning": "Bridge returned after requesting save; verify Dolphin persisted state before relying on it"}

    def request_load(self, profile: StateProfile) -> dict[str, Any]:
        self._preflight()
        self.transport.call("savestate.load_from_slot", [profile.slot])
        return {"action": "load_requested", "name": profile.name, "slot": profile.slot,
                "warning": "Bridge acknowledgement is not visual verification that the game restored correctly"}
