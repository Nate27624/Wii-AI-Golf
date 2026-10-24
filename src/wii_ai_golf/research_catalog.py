"""Read-only research views: distinguish planned studies from observed outcomes.

No Dolphin, network, model imports or file writes. Queue status is a
planning hint, NEVER the current state of a separate worker or a proof
that an experiment succeeded.
"""
from __future__ import annotations

from pathlib import Path
import json

MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100_000


def _rows(path: Path, *, missing_ok: bool = False):
    if not path.is_file():
        if missing_ok:
            return
        raise ValueError(f"Research file not found: {path}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"Research input exceeds {MAX_FILE_BYTES} bytes: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, 1):
            if index > MAX_ROWS:
                raise ValueError(f"Research input has more than {MAX_ROWS} rows")
            if line.strip():
                yield index, line


def study_summary(path: Path) -> dict:
    studies = []
    seen = set()
    for index, raw in _rows(path):
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid queue JSON at line {index}: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Study at line {index} is not an object")
        ident = item.get("study_id")
        if not isinstance(ident, str) or not ident or ident in seen:
            raise ValueError(f"Invalid/duplicate study ID at line {index}")
        seen.add(ident)
        studies.append({
            "study_id": ident,
            "role": str(item.get("role") or "unassigned"),
            "title": str(item.get("title") or "(untitled)"),
            "status": str(item.get("status") or "unspecified"),
            "blocked_by": str(item.get("blocked_by") or "none declared"),
            "priority": item.get("priority"),
        })
    studies.sort(key=lambda row: (row["priority"] if isinstance(row["priority"], int) else 999,
                                  row["study_id"]))
    return {
        "source": str(path),
        "status_meaning": "Static research proposals, not live queue jobs or measured results",
        "studies": studies,
    }


def evidence_summary(path: Path) -> dict:
    result = {
        "source": str(path),
        "present": path.is_file(),
        "trials": 0,
        "dispatch_complete": 0,
        "ball_moved_yes": 0,
        "on_green_yes": 0,
        "invalid_lines": 0,
        "verified_scores": 0,
        "note": "Human reports are not calibrated game measurements; missing fields are unknown.",
    }
    for _, raw in _rows(path, missing_ok=True):
        try:
            item = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            result["invalid_lines"] += 1
            continue
        if not isinstance(item, dict):
            result["invalid_lines"] += 1
            continue
        result["trials"] += 1
        dispatch = item.get("dispatch")
        if isinstance(dispatch, dict) and dispatch.get("state") == "complete":
            result["dispatch_complete"] += 1
        if item.get("human_ball_moved") == "yes":
            result["ball_moved_yes"] += 1
        if item.get("human_on_green") == "yes":
            result["on_green_yes"] += 1
        # A non-null game_score by itself is NOT verified; only count
        # explicit independent validation with provenance.
        if item.get("score_validation") == "verified" and item.get("game_score") is not None:
            result["verified_scores"] += 1
    return result
