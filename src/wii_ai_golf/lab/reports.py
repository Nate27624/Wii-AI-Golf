"""Index ONLY local sanitized S002 outcome summaries, not private RAM captures.

All claims here come from user-entered outcome labels, not game-score
verification or bridge dispatch completion.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .core import ROOT


def sanitized_reports(*, root: Path = ROOT, limit: int = 25) -> list[dict[str, Any]]:
    directory = root.parent / "Wii-AI-Golf-Data" / "captures"
    if not directory.is_dir():
        return []
    results = []
    paths = sorted(directory.glob("outcome-*-candidates.json"), reverse=True)
    for path in paths[:min(max(limit, 0), 100)]:
        try:
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            human = data.get("human_observation", {})
            if not isinstance(human, dict):
                human = {}
            wave = data.get("known_good_swing_request", {})
            if not isinstance(wave, dict):
                wave = {}
            result = {
                "path": str(path),
                "source": "sanitized_local_candidate_summary",
                "contact_human": human.get("contact_human", "unknown"),
                "green_human": human.get("finished_on_green_human", "unknown"),
                "distance_human": human.get("displayed_distance_human"),
                "unit_human": human.get("displayed_unit_human", "unknown"),
                "trace_sha256": wave.get("trace_sha256"),
                "a_prime_requests": wave.get("a_button_only_prime_requests"),
                "verified_game_score": False,
            }
            results.append(result)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return results
