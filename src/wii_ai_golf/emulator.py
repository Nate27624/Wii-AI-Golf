"""Explicit integration boundary. No unverified Dolphin/Wii Remote API calls."""
from __future__ import annotations

from typing import Protocol

from .protocol import Observation, ShotAction, ShotResult


class DolphinBridge(Protocol):
    """Implementation must control an actual emulator and extract measured outcomes."""

    def load_scenario(self, scenario_id: str, seed: int) -> Observation:
        ...

    def perform_swing(self, action: ShotAction) -> None:
        ...

    def read_final_result(self) -> ShotResult:
        ...


class DolphinEnvironment:
    """Thin adapter around a validated bridge implementation supplied later."""

    def __init__(self, bridge: DolphinBridge):
        self.bridge = bridge
        self._ready = False

    def reset(self, scenario_id: str, *, seed: int) -> Observation:
        self._ready = False
        observation = self.bridge.load_scenario(scenario_id, seed)
        if not isinstance(observation, Observation):
            raise ValueError("Bridge reset did not return a validated Observation")
        if observation.scenario_id != scenario_id:
            raise ValueError("Bridge reset scenario does not match requested scenario")
        self._ready = True
        return observation

    def step(self, action: ShotAction) -> ShotResult:
        if not self._ready:
            raise RuntimeError("Call reset() before step()")
        self._ready = False
        self.bridge.perform_swing(action)
        return self.bridge.read_final_result()
