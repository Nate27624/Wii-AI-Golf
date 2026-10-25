"""Offline, token-free export of allowlisted Lab execution statuses.

This is a handoff artifact for a separately authenticated GitHub connector,
NOT a network publisher and NOT a golf observation or verified score.
Never read logs, raw captures, ROMs, savestates, or arbitrary research files.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .publish import RUN_ID, public_record

KIND = "execution_status_bundle"
CLAIM = "PROCESS_STATUS_ONLY_NOT_A_GOLF_SCORE"
MAX_RECORDS = 100
MAX_SCAN = 2000
MAX_RUN_BYTES = 65_536
MAX_BUNDLE_BYTES = 65_536
BUNDLE_KEYS = frozenset(
    {"schema_version", "record_type", "claim", "record_count", "records", "sha256"}
)


def _canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def build_bundle(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Reject any non-public field, duplicate run, invalid ID or run status."""
    if type(records) is not list or len(records) > MAX_RECORDS:
        raise ValueError("Invalid number of export records")
    seen: set[str] = set()
    safe = []
    for item in records:
        if type(item) is not dict:
            raise ValueError("Export record must be an object")
        clean = public_record(item)
        if item != clean or set(item) != set(clean):
            raise ValueError("Export contains non-allowlisted fields")
        rid = clean["run_id"]
        if rid in seen:
            raise ValueError("Duplicate execution run ID")
        seen.add(rid)
        safe.append(clean)
    safe.sort(key=lambda row: row["run_id"])
    result = {
        "schema_version": 1,
        "record_type": KIND,
        "claim": CLAIM,
        "record_count": len(safe),
        "records": safe,
        "sha256": hashlib.sha256(_canonical(safe)).hexdigest(),
    }
    return result


def verify_bundle(bundle: Any) -> dict[str, Any]:
    if type(bundle) is not dict or set(bundle) != BUNDLE_KEYS:
        raise ValueError("Unrecognized export bundle schema")
    if (type(bundle["schema_version"]) is not int or bundle["schema_version"] != 1
        or bundle["record_type"] != KIND or bundle["claim"] != CLAIM
        or type(bundle["record_count"]) is not int):
        raise ValueError("Invalid export bundle header")
    rows = bundle["records"]
    if type(rows) is not list or len(rows) != bundle["record_count"]:
        raise ValueError("Export count mismatch")
    safe = build_bundle(rows)
    if bundle != safe:
        raise ValueError("Export bundle checksum, order or contents changed")
    return safe


def verify_export_file(path: Path) -> dict[str, Any]:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BUNDLE_BYTES:
        raise ValueError("Missing, linked or oversized export bundle")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("Export JSON could not be read") from exc
    return verify_bundle(data)


def _records_from_runs(data: Path, *, limit: int) -> tuple[list[dict[str, Any]], int]:
    if type(limit) is not int or not 1 <= limit <= MAX_RECORDS:
        raise ValueError("Export limit must be 1..100")
    folder = Path(data) / "runs"
    if not folder.is_dir():
        return [], 0
    selected = []
    skipped = 0
    candidates = sorted(folder.glob("*.json"), reverse=True)
    if len(candidates) > MAX_SCAN:
        raise ValueError("Too many local run records; archive older runs before export")
    for path in candidates:
        if len(selected) >= limit:
            break
        if (path.is_symlink() or not path.is_file() or
            not RUN_ID.fullmatch(path.stem) or path.stat().st_size > MAX_RUN_BYTES):
            skipped += 1
            continue
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            if type(item) is not dict or item.get("run_id") != path.stem:
                raise ValueError("Mismatched run identity")
            selected.append(public_record(item))  # allowlist ONLY; no private fields survive
        except (OSError, UnicodeError, ValueError, TypeError):
            skipped += 1
    return selected, skipped


def create_export(data: Path, *, limit: int = 20) -> tuple[Path, dict[str, Any], int]:
    """Construct, persist and re-read a token-free, privacy-allowlisted bundle."""
    safe, skipped = _records_from_runs(data, limit=limit)
    if not safe:
        raise ValueError("No finalized valid Lab runs available. Run 'golf lab run core.tests' first.")
    bundle = build_bundle(safe)
    verify_bundle(bundle)
    folder = Path(data) / "exports"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("status-bundle-" + bundle["sha256"] + ".json")
    payload = (json.dumps(bundle, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(payload) > MAX_BUNDLE_BYTES:
        raise ValueError("Export bundle exceeds safe size")
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        if path.is_symlink() or path.read_bytes() != payload:
            raise ValueError("Existing export path contains conflicting data")
    else:
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
    verify_export_file(path)
    return path, bundle, skipped


def latest_export(data: Path) -> Path:
    folder = Path(data) / "exports"
    options = [path for path in folder.glob("status-bundle-*.json")
               if path.is_file() and not path.is_symlink()] if folder.is_dir() else []
    if not options:
        raise ValueError("No local export yet. Run 'golf lab export' first.")
    return max(options, key=lambda path: path.stat().st_mtime_ns)
