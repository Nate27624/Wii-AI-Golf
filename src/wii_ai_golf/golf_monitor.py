"""Unattended READ-ONLY Hitting the Green telemetry.

Polls version-gated scene translation hypotheses. No automatic swing,
score reader, savestate loading, screenshot extraction or game writes.
The moving golf ball and shot/result phase are currently unknown.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from typing import Any, Callable

from .golf_collection import make_run_id, publish_sanitized, read_stage
from .scenario_inference import StableSceneTracker

TRACKED = ("current_pin_obj_ptr", "current_start_obj_ptr", "cup_obj_ptr")


def _position(sample: dict[str, Any], name: str) -> tuple[float, float, float] | None:
    obj = sample.get("objects", {}).get(name, {})
    raw = obj.get("translation_xyz_unverified")
    if not isinstance(raw, (tuple, list)) or len(raw) != 3:
        return None
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in raw):
        return None
    return tuple(float(v) for v in raw)


def changed_fields(before: dict[str, Any] | None,
                   after: dict[str, Any], tolerance: float = 0.05) -> list[str]:
    """Scene-state changes, NEVER a determination that the ball was struck."""
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("positive finite position tolerance required")
    if before is None:
        return ["initial"]
    result: list[str] = []
    for key in ("mode", "current_hole_raw", "game_id", "disc_revision"):
        if before.get(key) != after.get(key):
            result.append(key + "_changed")
    for key in TRACKED:
        p = _position(before, key)
        q = _position(after, key)
        if p is None and q is None:
            continue
        if p is None or q is None or math.dist(p, q) >= tolerance:
            result.append(key + "_translation_changed")
    return result


def build_public_report(run_id: str, *, started_utc: str,
                        samples: int, events: list[dict[str, Any]],
                        heartbeats: list[dict[str, Any]],
                        errors: list[dict[str, Any]], local_complete: bool) -> dict[str, Any]:
    """Whitelisted numeric sample reports only; upload is a separate function."""
    return {
        "schema_version": 1, "study_id": "S002-HG-CONTINUOUS",
        "source": "live-Dolphin-read-only-observation; scene-hypotheses-unverified",
        "run_id": run_id, "started_utc": started_utc,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "sample_count": samples, "local_series_complete": local_complete,
        "recorded_events": events[-500:],
        "events_truncated_before_recent_500": len(events) > 500,
        "periodic_samples": heartbeats[-120:],
        "periodic_samples_truncated_before_recent_120": len(heartbeats) > 120,
        "recent_errors": errors[-20:],
        "limitations": [
            "Pin, cup and start are candidate static map-object translations, not measured ball positions.",
            "Scene changes do NOT prove any shot occurred; full swing detection and score extraction remain unknown.",
            "Coordinates are unverified game units, NOT meters.",
            "Felk RPC samples span many game frames and cannot reconstruct frame-perfect ball trajectory.",
            "No Wii Remote commands, savestate resets or memory writes were executed by this monitor.",
            "Shot labels are empirical tee-position matches from one observed RSPE01 Rev1 dataset; NOT the authoritative game shot counter.",
            "Pin and cup must agree and a scene repeat for 3 samples; staggered tee/pin transitions can still produce tentative pairs.",
        ],
    }


def run_monitor(
    *, code_root: Path, local_dir: Path, port: int = 55355,
    interval_s: float = 1.0, max_minutes: float = 15.0, max_samples: int = 0,
    upload: bool = True, sample_reader: Callable[[int], dict[str, Any]] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
    upload_fn: Callable[[dict[str, Any], Path], str] = publish_sanitized,
    heartbeat_s: float = 10.0,
) -> tuple[Path, str | None]:
    if not (0.2 <= interval_s <= 3600) or not math.isfinite(interval_s):
        raise ValueError("interval_s must be finite and >=0.2 and <=3600 seconds")
    if not (0 <= max_minutes <= 1440) or not math.isfinite(max_minutes):
        raise ValueError("max_minutes must be finite between 0 and 1440")
    if type(max_samples) is not int or max_samples < 0:
        raise ValueError("max_samples must be >=0")
    if not math.isfinite(heartbeat_s) or heartbeat_s <= 0:
        raise ValueError("heartbeat_s must be positive and finite")
    if sample_reader is None:
        from .integration.rpc import FelkRPC

        def sample_reader(_i: int) -> dict[str, Any]:
            return read_stage(FelkRPC, port, "continuous-read",
                              allow_result_transition=True)
    run_id = make_run_id()
    now = datetime.now(timezone.utc).isoformat()
    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    path = local_dir / ("hitting-green-monitor-" + run_id + ".jsonl")
    events: list[dict[str, Any]] = []
    heartbeat: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    tracker = StableSceneTracker(required_samples=3)
    previous: dict[str, Any] | None = None
    samples = 0
    consecutive_errors = 0
    start = monotonic_fn()
    next_heartbeat = start
    link: str | None = None
    print("Recording READ-ONLY Wii Sports spatial observations; no Enter needed.")
    print("Swing manually, then advance through the shots normally.")
    print("Press Ctrl+C to stop and upload a compact report.")
    print(f"Saving complete local sample history: {path}")
    try:
        with path.open("x", encoding="utf-8") as log:
            while (not max_samples or samples < max_samples) and (
                not max_minutes or monotonic_fn() - start < max_minutes * 60
            ):
                tick = monotonic_fn()
                try:
                    sample = sample_reader(samples)
                    if sample.get("game_id") != "RSPE01" or sample.get("disc_revision") != 1:
                        raise RuntimeError("Wii Sports RSPE01 disc revision 1 required")
                    sample["scene_inference"] = tracker.feed(sample)
                    triggers = changed_fields(previous, sample)
                    if sample["scene_inference"]["new_configuration"]:
                        triggers.append("stable_empirical_tee_pin_configuration")
                        print("  candidate shot position:", sample["scene_inference"]["tee_index_observed"],
                              "| pin variant:", sample["scene_inference"]["pin_variant_observed"],
                              "(empirical coordinates, NOT actual game shot counter)")
                    envelope = {"sample_index": samples + 1,
                                "seconds_from_start": round(tick - start, 3),
                                "changes": triggers, "state": sample}
                    log.write(json.dumps(envelope, sort_keys=True, allow_nan=False) + "\n")
                    log.flush()
                    samples += 1
                    consecutive_errors = 0
                    if triggers:
                        events.append(envelope)
                        print(f"[{samples}] {', '.join(triggers)} | mode={sample.get('mode')} "
                              f"raw-hole={sample.get('current_hole_raw')}")
                    if tick >= next_heartbeat:
                        heartbeat.append(envelope)
                        next_heartbeat = tick + heartbeat_s
                        print(f"  active: {samples} samples, {len(events)} scene events; "
                              "moving ball & final score not decoded")
                    previous = sample
                except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
                    consecutive_errors += 1
                    error = {"sample_attempt": samples + 1,
                             "seconds_from_start": round(tick - start, 3),
                             "error_type": type(exc).__name__,
                             "warning": "read-only capture error; no game input sent"}
                    errors.append(error)
                    log.write(json.dumps(error, sort_keys=True) + "\n")
                    log.flush()
                    print(f"Read-only RPC error ({consecutive_errors}/5): {type(exc).__name__}")
                    if consecutive_errors >= 5:
                        print("Too many consecutive capture errors; stopping safely.")
                        break
                elapsed = monotonic_fn() - tick
                delay = max(0.0, interval_s - elapsed)
                if delay:
                    sleep_fn(delay)
    except KeyboardInterrupt:
        print("\nStopped by Ctrl+C; preparing the compact results report.")
    public = build_public_report(run_id, started_utc=now, samples=samples,
                                 events=events, heartbeats=heartbeat,
                                 errors=errors, local_complete=True)
    summary_path = local_dir / ("hitting-green-monitor-" + run_id + "-summary.json")
    with summary_path.open("x", encoding="utf-8") as handle:
        json.dump(public, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    if upload and samples:
        try:
            link = upload_fn(public, code_root)
            print(f"GitHub report: {link}")
        except (OSError, RuntimeError) as exc:
            print(f"GitHub upload failed ({type(exc).__name__}); "
                  f"report saved locally: {summary_path}")
    print(f"Samples: {samples} | scene-change events: {len(events)} | local: {path}")
    return path, link
