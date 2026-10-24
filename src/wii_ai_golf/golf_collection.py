"""Guided human-in-the-loop Hitting the Green observation collection.

Shots and UI navigation are performed by the human, NOT by this module.
Raw emulator memory, screenshots, file paths and savestates are never uploaded.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
from typing import Any, Callable

from .observation_capture import capture
from .spatial_probe import capture_spatial_rev1

REPOSITORY = "Nate27624/Wii-AI-Golf"
_GIT_REMOTE = re.compile(r"github\.com[:/]Nate27624/Wii-AI-Golf(?:\.git)?$", re.IGNORECASE)
_OBJECTS = ("current_pin_obj_ptr", "current_start_obj_ptr", "cup_obj_ptr",
            "course_obj_ptr", "minimap_course_obj_ptr")
_STATES = {"green", "missed", "unknown"}


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)


def session_steps(*, start_shot: int = 1, shots: int = 10,
                  plan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Without a plan: sequential manual shot prompts. Never invent pin variants."""
    if type(start_shot) is not int or type(shots) is not int or not 1 <= start_shot <= 10 or not 1 <= shots <= 10:
        raise ValueError("shot numbers and count must be integers in 1..10")
    if plan is None:
        if start_shot + shots > 11:
            raise ValueError("requested shot range exceeds ten Hitting the Green shots")
        return [{"shot_index": i, "attempt": i, "checkpoint": None,
                 "scenario": None, "variant": "not-observed"} for i in range(start_shot, start_shot + shots)]
    if not isinstance(plan, dict) or plan.get("schema_version") != 1 or not isinstance(plan.get("attempts"), list):
        raise ValueError("expected a schema_version=1 scenario plan with attempts")
    steps: list[dict[str, Any]] = []
    for row in plan["attempts"]:
        if not isinstance(row, dict) or row.get("challenge") != "hitting-green":
            raise ValueError("plan must contain Hitting the Green attempts only")
        index = row.get("shot_index")
        if type(index) is not int or not 1 <= index <= 10:
            raise ValueError("every planned scenario needs a 1..10 shot index")
        if type(row.get("attempt")) is not int:
            raise ValueError("plan attempt number required")
        steps.append({"shot_index": index, "attempt": row["attempt"],
                      "checkpoint": row.get("checkpoint"), "scenario": row.get("scenario"),
                      "variant": row.get("variant", "unknown"),
                      "split": row.get("split"), "plan_seed": plan.get("seed")})
    if not steps:
        raise ValueError("plan has no observed scenarios to collect")
    return steps[:shots]


def _xyz(item: dict[str, Any], key: str) -> list[float] | None:
    value = item.get(key, {}).get("xyz_raw")
    return value if isinstance(value, list) and len(value) == 3 and all(
        isinstance(x, (int, float)) and math.isfinite(x) for x in value) else None


def summarize(snapshot: dict[str, Any], spatial: dict[str, Any]) -> dict[str, Any]:
    """Explicit whitelist so no memory bytes, local paths or screenshots leak."""
    objects: dict[str, dict[str, Any]] = {}
    for key in _OBJECTS:
        data = spatial.get("map_objects", {}).get(key, {})
        objects[key] = {
            "translation_xyz_unverified": _xyz(data, "inline_translation_offset_0x30"),
            "scale_xyz_unverified": _xyz(data, "inline_scale_offset_0x3c"),
        }
    # Metadata only; never include raw screens, memory dumps, local filenames.
    return {
        "captured_utc": snapshot["captured_utc"],
        "frame_start": snapshot["frame_start"], "frame_end": snapshot["frame_end"],
        "game_id": spatial["game_id"], "disc_revision": spatial["disc_revision"],
        "mode": spatial.get("mode_label"), "current_hole_raw": spatial.get("current_hole_raw"),
        "objects": objects,
        "geometry_unverified": spatial.get("relative_geometry_unverified"),
        "controller": {
            "buttons": snapshot.get("controller", {}).get("buttons", {}),
            "acceleration_m_s2": snapshot.get("controller", {}).get("acceleration_m_s2"),
            "angular_velocity_rad_s": snapshot.get("controller", {}).get("angular_velocity_rad_s"),
        },
    }


def read_stage(rpc_factory: Callable[..., Any], port: int, label: str) -> dict[str, Any]:
    """Read-only RPC calls; require the version-gated training screen."""
    with rpc_factory(port=port, timeout_s=15) as rpc:
        spatial = capture_spatial_rev1(rpc)
        if not spatial.get("supported") or spatial.get("mode_label") != "GAMEMODE_TR_NEARPIN":
            raise RuntimeError("Not confirmed as US Rev1 Hitting the Green; no shot recorded")
        snap = capture(rpc, label, [])
    return summarize(snap, spatial)


def _ask(prompt: str, input_fn: Callable[[str], str]) -> str:
    return input_fn(prompt).strip()


def human_result(input_fn: Callable[[str], str]) -> dict[str, Any]:
    recognized = _ask("Did the ball visibly get struck? [y/n/?]: ", input_fn).lower()
    while recognized not in ("y", "n", "?"):
        recognized = _ask("Enter y, n, or ?: ", input_fn).lower()
    outcome = "unknown"
    if recognized == "y":
        outcome = _ask("Landed on green? [green/missed/unknown]: ", input_fn).lower() or "unknown"
        while outcome not in _STATES:
            outcome = _ask("Enter green, missed or unknown: ", input_fn).lower()
    value: float | None = None
    unit: str | None = None
    if recognized == "y":
        while True:
            raw = _ask("Displayed distance/score number (blank if not visible): ", input_fn)
            if not raw:
                break
            try:
                value = float(raw)
                if not math.isfinite(value) or value < 0:
                    raise ValueError()
                break
            except ValueError:
                print("Please enter a finite nonnegative number or leave blank.")
        if value is not None:
            unit = _ask("Unit exactly as displayed [m/ft/yd/other/unknown]: ", input_fn).lower()
            while unit not in ("m", "ft", "yd", "other", "unknown"):
                unit = _ask("Enter m, ft, yd, other or unknown: ", input_fn).lower()
    return {
        "ball_struck_human_observed": {"y": True, "n": False, "?": None}[recognized],
        "landing_human_observed": outcome,
        "score_number_human_unverified": value,
        "score_unit_as_displayed": unit,
    }


def persist_local(report: dict[str, Any], folder: Path) -> Path:
    """Atomic local checkpoint after each completed step; not a Git operation."""
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / ("hitting-green-" + report["run_id"] + ".json")
    temp = destination.with_suffix(".json.tmp")
    if temp.exists():
        raise RuntimeError(f"Existing temporary capture file; inspect it: {temp}")
    try:
        with temp.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        temp.replace(destination)
    finally:
        if temp.exists():
            temp.unlink()
    return destination


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        # Avoid displaying raw Git remote URLs (possibly credential-bearing).
        raise RuntimeError(f"Git command failed: {args[0]}; local report was preserved.")
    return proc.stdout.strip()


def publish_sanitized(report: dict[str, Any], root: Path) -> str:
    """Push one small JSON to an isolated data branch without changing current HEAD.

    Requires the user's existing Git remote credentials/commit identity. If the
    push fails, the separately saved local report is still available.
    """
    remote = _git(root, "remote", "get-url", "origin")
    if not _GIT_REMOTE.search(remote):
        raise RuntimeError("Git origin must be Nate27624/Wii-AI-Golf on github.com; upload refused")
    _git(root, "fetch", "origin", "main")
    run_id = report["run_id"]
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}", run_id):
        raise ValueError("invalid run identifier")
    git_branch = f"data/hitting-green-{run_id}"
    relative = Path("research/results/hitting-green") / (run_id + ".json")
    with tempfile.TemporaryDirectory(prefix="golf-publish-") as tmp:
        workspace = Path(tmp) / "checkout"
        _git(root, "worktree", "add", "--detach", str(workspace), "origin/main")
        try:
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
                handle.write("\n")
            _git(workspace, "add", "--", relative.as_posix())
            _git(workspace, "commit", "-m", f"data: human-observed Hitting the Green run {run_id}")
            # A unique branch avoids collisions and does not modify main or PR #14.
            _git(workspace, "push", "origin", f"HEAD:refs/heads/{git_branch}")
        finally:
            _git(root, "worktree", "remove", "--force", str(workspace))
    url = f"https://github.com/{REPOSITORY}/blob/{git_branch}/{relative.as_posix()}"
    # Optional discoverability: publish only a link, not raw data, to S002.
    if shutil.which("gh") is not None:
        subprocess.run(["gh", "issue", "comment", "3", "--repo", REPOSITORY,
                        "--body", f"Human-in-the-loop Hitting the Green observations: {url}\n"
                                  "Raw score units and spatial translations are unverified; no auto-swing inferred."],
                       capture_output=True, text=True, check=False)
    return url


def collect(*, steps: list[dict[str, Any]], port: int, data_dir: Path,
            code_root: Path, upload: bool = True,
            rpc_factory: Callable[..., Any] | None = None,
            input_fn: Callable[[str], str] = input) -> tuple[Path | None, str | None]:
    """Interactive collection; saves a partial report if interrupted or an error occurs."""
    if rpc_factory is None:
        from .integration.rpc import FelkRPC
        rpc_factory = FelkRPC
    report: dict[str, Any] = {
        "schema_version": 1,
        "study_id": "S002-HG-HUMAN-OBS",
        "source": "user-operated-emulator-and-human-scoring-unverified",
        "run_id": make_run_id(),
        "notes": "Manual swings, not AI-controlled shots. Positions are candidate game units. Human score number and displayed unit are not validated.",
        "attempts": [],
    }
    saved: Path | None = None
    published: str | None = None
    try:
        for ix, step in enumerate(steps, 1):
            number = step["shot_index"]
            print(f"\n--- Attempt {ix}/{len(steps)}: Hitting the Green, SHOT {number} ---")
            if step.get("scenario"):
                print(f"Scenario: {step['scenario']} | savestate: {step['checkpoint']} | variant: {step['variant']}")
                print("Manually load/check the listed state. This script does NOT reset Dolphin.")
            else:
                print(f"Navigate to the screen immediately BEFORE shot {number}.")
                print("Keep the game on this shot until its before-state is recorded.")
            ready = _ask("Press ENTER when shot is ready (q = finish and upload collected shots): ", input_fn)
            if ready.lower() == "q":
                break
            pre = read_stage(rpc_factory, port, f"shot-{number}-before")
            print("Before-state captured.")
            print("SWING NOW using your Wii Remote. Wait until ball lands/result appears.")
            _ask("Press ENTER on the result screen to capture after-state: ", input_fn)
            row: dict[str, Any] = {"attempt_number": step["attempt"], "shot_index": number,
                                   "scenario": step.get("scenario"), "checkpoint": step.get("checkpoint"),
                                   "variant": step.get("variant"), "split": step.get("split"),
                                   "before": pre, "after": None, "human_result": None,
                                   "capture_complete": False}
            report["attempts"].append(row)
            saved = persist_local(report, data_dir)
            post = read_stage(rpc_factory, port, f"shot-{number}-after")
            row["after"] = post
            row["human_result"] = human_result(input_fn)
            row["capture_complete"] = True
            saved = persist_local(report, data_dir)
            print(f"Shot {number} recorded locally: {saved.name}")
    except (KeyboardInterrupt, EOFError):
        print("\nSession interrupted; preserving observations so far.")
    finally:
        if report["attempts"]:
            saved = persist_local(report, data_dir)
            if upload:
                try:
                    published = publish_sanitized(report, code_root)
                    print(f"\nUploaded sanitized report to GitHub:\n{published}")
                except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                    print(f"\nGitHub upload failed: {exc}")
                    print(f"Local observations are preserved: {saved}")
                    print("To retry later, use a GitHub-authenticated git remote; no data was discarded.")
        else:
            print("No shots captured, so nothing was uploaded.")
    return saved, published
