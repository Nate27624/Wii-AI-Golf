"""Auditable, deterministic scheduling of OBSERVED emulator savestate scenarios.

Does not create novel Wii Sports layouts, modify RAM, or assume captured states
are independent. Each scenario references an existing named Dolphin checkpoint.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import random
import re
from typing import Any

from .savestates import StateCatalog

_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_CHALLENGE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class Scenario:
    name: str
    checkpoint: str
    challenge: str
    shot_index: int | None = None
    variant: str = "unmeasured"
    conditions: dict[str, str] = field(default_factory=dict)
    visually_verified: bool = False

    def __post_init__(self) -> None:
        for label, value, pattern in (
            ("name", self.name, _NAME), ("checkpoint", self.checkpoint, _NAME),
            ("challenge", self.challenge, _CHALLENGE),
        ):
            if not isinstance(value, str) or not pattern.fullmatch(value):
                raise ValueError(f"invalid {label}: {value!r}")
        if self.shot_index is not None and (type(self.shot_index) is not int or not 1 <= self.shot_index <= 1000):
            raise ValueError("shot_index must be 1..1000, or omitted")
        if not isinstance(self.variant, str) or not self.variant or len(self.variant) > 100:
            raise ValueError("variant must be a nonempty descriptive label <=100 characters")
        if type(self.visually_verified) is not bool:
            raise ValueError("visually_verified must be boolean")
        if not isinstance(self.conditions, dict) or len(self.conditions) > 32:
            raise ValueError("conditions must be a dictionary with <=32 entries")
        if any(not isinstance(k, str) or not k or len(k) > 64 or
               not isinstance(v, str) or len(v) > 256 for k, v in self.conditions.items()):
            raise ValueError("invalid condition metadata")

    @property
    def group(self) -> str:
        """A shot index is a split unit: pin variants of a shot never cross splits."""
        return f"{self.challenge}/shot-{self.shot_index}" if self.shot_index is not None else f"{self.challenge}/{self.name}"


class ScenarioBank:
    def __init__(self, path: Path, catalog: StateCatalog):
        self.path = Path(path)
        self.catalog = catalog
        self.scenarios: dict[str, Scenario] = {}
        if self.path.exists():
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(payload.get("scenarios"), list):
                raise ValueError("scenario bank requires schema_version=1 and a scenarios list")
            for item in payload["scenarios"]:
                self.add(Scenario(**item))

    def add(self, scene: Scenario) -> None:
        self.catalog.get(scene.checkpoint)  # fail closed on missing local state profile
        if scene.name in self.scenarios:
            raise ValueError(f"scenario already registered: {scene.name}")
        key = (scene.challenge, scene.shot_index, scene.variant)
        if any((s.challenge, s.shot_index, s.variant) == key for s in self.scenarios.values()):
            raise ValueError("duplicate challenge/shot_index/variant; capture a distinct configuration first")
        self.scenarios[scene.name] = scene

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"schema_version": 1, "scenarios": [asdict(self.scenarios[k]) for k in sorted(self.scenarios)]}
        tmp = self.path.with_name(self.path.name + ".tmp")
        if tmp.exists():
            raise RuntimeError(f"stale temp file: {tmp}; inspect before proceeding")
        with tmp.open("x", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        tmp.replace(self.path)

    def plan(self, *, rounds: int, seed: int, balance: str = "shot",
             holdout_shots: frozenset[int] = frozenset(),
             verified_only: bool = True) -> dict[str, Any]:
        if type(rounds) is not int or not 1 <= rounds <= 100000:
            raise ValueError("rounds must be 1..100000")
        if type(seed) is not int:
            raise ValueError("seed must be an integer")
        if balance not in ("shot", "scenario"):
            raise ValueError("balance must be shot or scenario")
        if any(type(i) is not int or not 1 <= i <= 1000 for i in holdout_shots):
            raise ValueError("invalid held-out shot index")
        selected = [x for x in self.scenarios.values() if not verified_only or x.visually_verified]
        if not selected:
            raise ValueError("no eligible scenarios: register and visually verify captured checkpoints")
        if holdout_shots and not any(s.shot_index in holdout_shots for s in selected):
            raise ValueError("no eligible scenario matches held-out shot indices")
        splits = {"train": [], "holdout": []}
        for s in selected:
            splits["holdout" if s.shot_index in holdout_shots else "train"].append(s)
        if not splits["train"]:
            raise ValueError("no training scenarios remain after holdout")
        rng = random.Random(seed)
        records: list[dict[str, Any]] = []
        for split_name in ("train", "holdout"):
            group_map: dict[str, list[Scenario]] = {}
            for s in splits[split_name]:
                key = s.group if balance == "shot" else s.name
                group_map.setdefault(key, []).append(s)
            # Shuffle variants independently, then cycle through them. This is
            # balanced over observed shot groups, not unobserved possible pin states.
            cycles: dict[str, list[Scenario]] = {}
            for group in sorted(group_map):
                shuffled = sorted(group_map[group], key=lambda s: s.name)
                rng.shuffle(shuffled)
                cycles[group] = shuffled
            for round_index in range(rounds):
                choices = [(k, cycles[k][round_index % len(cycles[k])]) for k in sorted(cycles)]
                rng.shuffle(choices)
                for group, s in choices:
                    records.append({
                        "split": split_name, "round": round_index + 1,
                        "group": s.group, "scenario": s.name, "checkpoint": s.checkpoint,
                        "slot": self.catalog.get(s.checkpoint).slot,
                        "challenge": s.challenge, "shot_index": s.shot_index,
                        "variant": s.variant, "conditions": dict(s.conditions),
                    })
        seen_shots = sorted({s.shot_index for s in selected if s.challenge == "hitting-green" and s.shot_index is not None})
        return {
            "schema_version": 1, "source": "observed-local-savestate-bank-NOT-generated-game-randomness",
            "seed": seed, "rounds": rounds, "balance": balance,
            "verified_only": verified_only, "holdout_shots": sorted(holdout_shots),
            "seen_hitting_green_shots": seen_shots,
            "missing_hitting_green_shots": [i for i in range(1, 11) if i not in seen_shots],
            "train_count": sum(x["split"] == "train" for x in records),
            "holdout_count": sum(x["split"] == "holdout" for x in records),
            "attempts": [{"attempt": i + 1, **record} for i, record in enumerate(records)],
        }
