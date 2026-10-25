"""Read-only audit of already-public, strictly sanitized Wii Golf observations.

This never ingests private RAM captures, infers scores, or executes Dolphin.
A successful RPC/process and changed minimap effects do not imply ball contact.
"""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

ID = re.compile(r"[0-9]{8}T[0-9]{6}Z-[a-z0-9_-]{4,48}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
MAX_FILE_BYTES = 32_768
MAX_FILES = 500
PUBLIC_KINDS = frozenset(("v1", "test", "automated-minimap-effect",
                          "swing-power-calibration"))
POWER_VARIANTS = frozenset((
    "baseline", "shorter", "slower", "faster", "longer-backswing"))
HUMAN_CONTACT = frozenset(("yes", "no", "unknown"))
UNITS = frozenset(("ft", "yd", "m", "unknown", "not-visible"))


def _int(v: Any, *, lo: int = 0, hi: int = 1_000_000) -> int | None:
    return v if type(v) is int and lo <= v <= hi else None


def _sha(v: Any) -> str | None:
    return v if isinstance(v, str) and SHA.fullmatch(v) else None


def _distance(v: Any) -> float | None:
    if type(v) not in (float, int):
        return None
    num = float(v)
    return num if math.isfinite(num) and 0 <= num <= 1_000_000 else None


def load_public_observations(directory: Path) -> list[dict[str, Any]]:
    """Only direct small JSONs from the APPROVED research/observations folder.

    Caller obtains these public summaries through the trusted results branch.
    Reject RAW-PRIVATE candidates and never include arbitrary input payloads
    or filesystem paths in the produced research report.
    """
    directory = Path(directory)
    if not directory.is_dir() or directory.name != "observations" or directory.parent.name != "research":
        raise ValueError("Expected isolated public research/observations directory")
    entries: list[dict[str, Any]] = []
    files = sorted(directory.glob("*.json"))
    if len(files) > MAX_FILES:
        raise ValueError("Too many observation JSON files for one read-only review")
    for path in files:
        if path.is_symlink() or not path.is_file() or not ID.fullmatch(path.stem):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or data.get("id") != path.stem:
            continue
        if type(data.get("kind")) is not str or data["kind"] not in PUBLIC_KINDS:
            continue
        entries.append(data)
    return entries


def review_public_observations(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts grouped by provenance, never scores or extrapolated hit rates."""
    seen: set[str] = set()
    v1: dict[tuple[str, str, int], dict[str, Any]] = {}
    minimap: dict[str, dict[str, Any]] = {
        key: {"runs": 0, "changes_seen": 0, "zero_change_runs": 0, "offsets": set()}
        for key in ("idle_control", "swing")
    }
    tests = {"pass": 0, "fail": 0}
    power: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    power_rejected = 0
    unknown_or_failed_v1 = 0
    malformed = 0
    ignored = 0
    total = 0

    for r in records:
        total += 1
        if not isinstance(r, Mapping) or not isinstance(r.get("id"), str) or not ID.fullmatch(r["id"]):
            malformed += 1
            continue
        identifier = r["id"]
        if identifier in seen:
            ignored += 1
            continue
        seen.add(identifier)
        kind = r.get("kind")
        if kind == "test":
            status = r.get("outcome")
            exit_code = _int(r.get("process_exit_code"), hi=255)
            if type(status) is str and ((status == "pass" and exit_code == 0) or (
                    status == "fail" and exit_code is not None and exit_code != 0)):
                tests[status] += 1
            else:
                malformed += 1
            continue
        if kind == "automated-minimap-effect":
            condition = r.get("condition")
            samples = _int(r.get("samples"), lo=2, hi=1000)
            count = _int(r.get("adjacent_changes"), hi=1000)
            offsets = r.get("changed_byte_offsets")
            if (type(condition) is not str or condition not in minimap or samples is None or count is None
                or count >= samples or not isinstance(offsets, list)
                or len(offsets) > 128 or
                any(_int(offset, hi=127) is None for offset in offsets)
                or (count == 0 and offsets)):
                malformed += 1
                continue
            cell = minimap[condition]
            cell["runs"] += 1
            cell["changes_seen"] += bool(count)
            cell["zero_change_runs"] += count == 0
            cell["offsets"].update(offsets)
            continue
        if kind == "swing-power-calibration":
            variant = r.get("variant")
            trace_sha = _sha(r.get("trace_sha256"))
            frames = _int(r.get("trace_frames"), lo=1, hi=500)
            contact = r.get("contact_human")
            observed_power = r.get("power_percent_human")
            scale = _distance(r.get("parameter_multiplier"))
            if (type(variant) is not str or variant not in POWER_VARIANTS
                or trace_sha is None or frames is None
                or type(contact) is not str or contact not in HUMAN_CONTACT
                or scale is None or not 0 < scale <= 2
                or (observed_power is not None and
                    (_distance(observed_power) is None
                     or _distance(observed_power) > 100))
                or r.get("power_verified_by_memory") is not False
                or r.get("contact_verified_by_memory") is not False):
                power_rejected += 1
                continue
            bridge_sha = _sha(r.get("bridge_sha256"))
            pose = r.get("initial_club_pose_human")
            pose = pose if type(pose) is str and pose in (
                "back", "center", "forward", "unknown") else "unrecorded"
            key = (variant, trace_sha, bridge_sha or "missing", pose)
            entry = power.setdefault(key, {
                "variant": variant, "trace_sha256": trace_sha,
                "bridge_sha256": bridge_sha,
                "initial_club_pose_human": pose,
                "human_labeled_trials": 0, "human_hit_yes": 0,
                "human_hit_no": 0, "human_hit_unknown": 0,
                "human_power_percent": [],
                "missing_bridge_sha256_count": 0,
                "missing_starting_pose_count": 0,
                "ball_power_or_score_verified": False,
            })
            entry["human_labeled_trials"] += 1
            entry["human_hit_" + contact] += 1
            if observed_power is not None:
                entry["human_power_percent"].append(float(observed_power))
            if bridge_sha is None:
                entry["missing_bridge_sha256_count"] += 1
            if pose == "unrecorded":
                entry["missing_starting_pose_count"] += 1
            continue
        if kind == "v1":
            if (_int(r.get("process_exit_code"), hi=255) != 0 or
                r.get("capture_status") != "sanitized_human_annotation_only"):
                unknown_or_failed_v1 += 1
                continue
            human, controller = r.get("human"), r.get("controller")
            if not isinstance(human, Mapping) or not isinstance(controller, Mapping):
                unknown_or_failed_v1 += 1
                continue
            contact = human.get("contact_human")
            lead = _int(controller.get("a_lead_observed_frame_delta"), hi=90)
            if type(contact) is not str or contact not in HUMAN_CONTACT or lead is None:
                unknown_or_failed_v1 += 1
                continue
            bridge_sha = _sha(r.get("bridge_sha256"))
            trace_sha = _sha(controller.get("trace_sha256"))
            if not bridge_sha or not trace_sha:
                unknown_or_failed_v1 += 1
                continue
            key = (bridge_sha, trace_sha, lead)
            entry = v1.setdefault(key, {
                "bridge_sha256": bridge_sha, "trace_sha256": trace_sha,
                "observed_a_lead_frames": lead, "human_labeled_trials": 0,
                "human_hit_yes": 0, "human_hit_no": 0, "human_hit_unknown": 0,
                "human_distances": [], "initial_pose_counts": {},
            })
            entry["human_labeled_trials"] += 1
            entry["human_hit_" + contact] += 1
            pose = human.get("initial_club_pose_human")
            if pose in ("back", "center", "forward", "unknown"):
                entry["initial_pose_counts"][pose] = entry["initial_pose_counts"].get(pose, 0) + 1
            distance = _distance(human.get("displayed_distance_human"))
            unit = human.get("displayed_unit_human")
            if distance is not None and type(unit) is str and unit in UNITS:
                entry["human_distances"].append({"distance": distance, "unit": unit})
            continue
        ignored += 1

    groups = sorted(v1.values(), key=lambda x: (x["observed_a_lead_frames"],
                                                  x["bridge_sha256"], x["trace_sha256"]))
    changes = {k: {
        "runs": v["runs"],
        "with_any_adjacent_changes": v["changes_seen"],
        "with_no_adjacent_changes": v["zero_change_runs"],
        "changed_byte_offsets_union": sorted(v["offsets"]),
    } for k, v in minimap.items()}
    power_groups = sorted(power.values(), key=lambda x: (
        x["variant"], x["trace_sha256"],
        x["bridge_sha256"] or "", x["initial_club_pose_human"]))
    # A single idle/swing pair can justify replication, not a detector.
    minimap_ready = all(v["runs"] >= 3 for v in minimap.values())
    v1_ready = any(x["human_labeled_trials"] >= 3 for x in groups)
    return {
        "schema_version": 1,
        "evidence_grade": "exploratory_human_and_effect_observations_only",
        "verified_game_scores": 0,
        "records_seen": total,
        "unique_records_processed": len(seen),
        "malformed_records": malformed,
        "duplicate_or_unsupported_records": ignored,
        "offline_unit_test_exits": tests,
        "v1_incomplete_or_failed_runs": unknown_or_failed_v1,
        "v1_by_bridge_trace_and_observed_a_lead": groups,
        "power_variant_by_waveform": power_groups,
        "power_records_rejected": power_rejected,
        "minimap_by_condition": changes,
        "gates": {
            "three_matched_human_trials_any_v1_condition": v1_ready,
            "three_independent_runs_each_minimap_condition": minimap_ready,
            "physics_ball_or_score_identity_verified": False,
            "controller_power_calibrated": False,
            "power_trials_have_complete_bridge_and_pose_provenance": (
                bool(power_groups) and
                all(e["missing_bridge_sha256_count"] == 0 and
                    e["missing_starting_pose_count"] == 0
                    for e in power_groups)),
        },
        "next_step": (
            "Repeat the human-confirmed historical V1 trace with 45 observed A-lead "
            "frames under the identical bridge and starting pose, before changing "
            "power. Run more idle/swing minimap controls. Keep each live trial "
            "separate, consented, and record negative outcomes."
        ),
        "limitations": (
            "Groups are not interchangeable across bridge SHA, waveform SHA, "
            "or measured A-lead. New S002 power variants are grouped by trace "
            "without inventing missing bridge/pose provenance. "
            "Minimap byte changes are visual effects, not "
            "verified physical ball motion. Human distances are not memory scores."
        ),
    }
