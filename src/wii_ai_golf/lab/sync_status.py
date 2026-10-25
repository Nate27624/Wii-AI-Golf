"""Offline explanation of Lab sync lock blockers; never removes lock files."""
from __future__ import annotations

import json
from pathlib import Path


def lock_blockers(lab_data: Path) -> list[str]:
    """Return actionable details, using only the known two lockfile names."""
    results = []
    for name in ("run-session.lock", "live-session.lock"):
        path = Path(lab_data) / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            pid = data.get("pid")
            when = data.get("utc")
            if type(pid) is int and pid > 0:
                results.append(f"{name}: recorded PID {pid}, started {when or 'unknown'}")
            else:
                results.append(f"{name}: invalid PID; requires manual inspection")
        except (OSError, ValueError, UnicodeError):
            results.append(f"{name}: unreadable/invalid lock; requires manual inspection")
    return results
