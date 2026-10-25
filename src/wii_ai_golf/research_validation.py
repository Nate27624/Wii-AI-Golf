"""Static preregistration checks for falsification-first studies.

Plans only: never executes a shot, reads private captures, or interprets
queue state as completed measurement. Standard library only.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .research_catalog import _rows

CATEGORY = "evidence-validation-v1"
ID = re.compile(r"VAL-[A-Z]+-[0-9]{2}\Z")
MODES = {"offline", "read-only", "approved-shot"}
STATES = {"proposed", "blocked", "in_progress", "completed"}
BUDGET_FIELDS = {"offline_records", "read_only_sessions", "approved_shots"}
REQUIRED = {
    "study_id", "category", "status", "role", "owner", "priority",
    "title", "mode", "depends_on", "budget", "hypothesis",
    "null_hypothesis", "measurement", "controls", "falsification",
    "stop_rule", "blocked_by", "independence_unit", "success_criteria",
    "evidence_now",
}
TEXT = {
    "title", "role", "owner", "hypothesis", "null_hypothesis", "measurement",
    "falsification", "stop_rule", "blocked_by", "independence_unit",
    "success_criteria", "evidence_now",
}


def validation_studies(path: Path) -> list[dict[str, Any]]:
    """Fail closed on ambiguous, contradictory or cyclic study proposals."""
    all_ids = set()
    relevant = []
    for lineno, line in _rows(path):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid study JSON at line {lineno}") from exc
        if type(item) is not dict:
            raise ValueError(f"Non-object study at line {lineno}")
        name = item.get("study_id")
        if type(name) is not str or name in all_ids:
            raise ValueError(f"Invalid or repeated study identifier at line {lineno}")
        all_ids.add(name)
        if item.get("category") != CATEGORY:
            continue
        if not ID.fullmatch(name) or set(item) != REQUIRED:
            raise ValueError(f"Invalid or incomplete validation-study schema: {name}")
        if item["status"] not in STATES or item["mode"] not in MODES:
            raise ValueError(f"Unrecognized study state/mode: {name}")
        if type(item["priority"]) is not int or not 0 <= item["priority"] <= 9:
            raise ValueError(f"Invalid study priority: {name}")
        if any(type(item[k]) is not str or not item[k].strip() or len(item[k]) > 1500
               for k in TEXT):
            raise ValueError(f"Missing or oversized preregistration field: {name}")
        controls, deps, budget = item["controls"], item["depends_on"], item["budget"]
        if (type(controls) is not list or len(controls) < 2 or
            any(type(v) is not str or not v.strip() or len(v) > 500 for v in controls)):
            raise ValueError(f"Study lacks distinct negative controls: {name}")
        if (type(deps) is not list or len(deps) != len(set(deps))
            or any(type(d) is not str or not ID.fullmatch(d) for d in deps)
            or name in deps):
            raise ValueError(f"Invalid dependency edge: {name}")
        if type(budget) is not dict or set(budget) != BUDGET_FIELDS:
            raise ValueError(f"Unknown study budget dimension: {name}")
        if any(type(v) is not int or not 0 <= v <= 200 for v in budget.values()):
            raise ValueError(f"Invalid study budget: {name}")
        if item["mode"] == "offline" and (budget["read_only_sessions"] or budget["approved_shots"]):
            raise ValueError(f"Offline study includes a live action: {name}")
        if item["mode"] == "read-only" and budget["approved_shots"]:
            raise ValueError(f"Read-only study includes a golf shot: {name}")
        if budget["approved_shots"] and (item["mode"] != "approved-shot" or
                                         budget["approved_shots"] > 6):
            raise ValueError(f"Unbounded or unlabeled live shot budget: {name}")
        if item["status"] == "completed":
            raise ValueError(f"Planning queue cannot independently prove a completed study: {name}")
        relevant.append(item)
    lookup = {item["study_id"]: item for item in relevant}
    for item in relevant:
        if any(dep not in lookup for dep in item["depends_on"]):
            raise ValueError(f"Unknown validation-study dependency: {item['study_id']}")
    visited = set()
    visiting = set()

    def visit(ident: str) -> None:
        if ident in visiting:
            raise ValueError("Cycle in validation study dependencies")
        if ident in visited:
            return
        visiting.add(ident)
        for dep in lookup[ident]["depends_on"]:
            visit(dep)
        visiting.remove(ident)
        visited.add(ident)

    for name in lookup:
        visit(name)
    return sorted(relevant, key=lambda s: (s["priority"], s["study_id"]))


def validation_report(path: Path) -> dict[str, Any]:
    studies = validation_studies(path)
    return {
        "kind": "validation_study_plans",
        "count": len(studies),
        "execution_performed": False,
        "game_score_verified": False,
        "note": "Static proposals only; not queued unattended jobs or permission to launch Dolphin.",
        "studies": studies,
    }
