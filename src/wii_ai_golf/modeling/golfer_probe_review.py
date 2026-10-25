"""S003 read-only triage for current S002 #129 bounded candidate object graph.

Only reads locally SANITIZED dictionaries. Distinguishes every first-level
child region by its parent offset. Never assumes a candidate child means the
club or that any float-shaped change is calibrated game power.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from itertools import islice
import re

_ID = re.compile(r"[A-Za-z0-9_.-]{1,90}\Z")
_OFFSET = re.compile(r"\+0x([0-9A-Fa-f]{1,3})\Z")
_CHILD = re.compile(r"child_at_main\+0x([0-9A-Fa-f]{3})\Z")
_SOURCE_NOTE = ("RPSysSceneMgr .sbss 0x804BF4D8..0x804BF4DF; "
                "EGG::SceneManager +0xC/+0x18; EGG::Scene +0x1C/+0x20; "
                "RPSportsBaseScene +0x54; RPGolScene +0x9C")
_PRIVATE_KEYS = frozenset(("bytes_hex", "child_windows", "raw_data",
                           "runtime_scene_address", "runtime_golf_main_address",
                           "watched_child_addresses", "private_path", "filesystem"))
_VALID_PHASES = frozenset(("idle", "aim_only"))


def _int(value: object, lo: int, hi: int) -> bool:
    return type(value) is int and lo <= value <= hi


def _safe_id(value: object) -> bool:
    return isinstance(value, str) and bool(_ID.fullmatch(value))


def _contains_private_keys(value: Mapping) -> bool:
    if any(k in _PRIVATE_KEYS for k in value):
        return True
    rows = value.get("top_relative_changes")
    return isinstance(rows, list) and any(
        isinstance(row, Mapping) and any(k in _PRIVATE_KEYS for k in row)
        for row in rows)


def _check_summary(item: Mapping) -> tuple[list[dict], bool, str | None]:
    if (item.get("kind") != "local-golfer-memory-audit"
            or type(item.get("schema_version")) is not int
            or item.get("schema_version") != 2
            or not _safe_id(item.get("id"))):
        return [], False, "invalid_identity_or_outdated_schema"
    if _contains_private_keys(item):
        return [], False, "raw_or_private_input_rejected"
    if (item.get("candidate_only") is not True
            or item.get("source_claim") != _SOURCE_NOTE
            or item.get("game_id") != "RSPE01"
            or type(item.get("revision")) is not int or item["revision"] != 1
            or type(item.get("game_mode")) is not int or item["game_mode"] != 4):
        return [], False, "invalid_source_revision_or_mode"
    if (not _int(item.get("source_static_slot_count"), 2, 2)
            or not _int(item.get("global_pointer_candidates"), 1, 2)
            or not _int(item.get("matched_scene_chains"), 1, 1)
            or item.get("actual_scene_id_verified") is not True
            or item.get("manager_backlink_verified") is not True
            or item.get("creator_scene_id_role") != "previous_scene_not_current_scene_id"
            or type(item.get("observed_creator_scene_id_matches_golf")) is not bool):
        return [], False, "scene_source_or_backlink_not_verified"
    # A different creator/previous scene ID is a legitimate Golf scene.
    if (not _int(item.get("samples"), 4, 60)
            or not _int(item.get("changed_candidate_words"), 0, 1024)
            or not _int(item.get("census_frame_span"), 0, 100000)
            or not _int(item.get("max_non_atomic_frame_span"), 0, 240)):
        return [], False, "invalid_sample_or_frame_counts"
    count = item.get("first_level_child_watch_count")
    truncated_child = item.get("first_level_child_watch_truncated")
    if not _int(count, 0, 16) or type(truncated_child) is not bool:
        return [], False, "invalid_child_watchlist"
    phases = item.get("phase_sample_counts")
    if (not isinstance(phases, Mapping) or set(phases) != _VALID_PHASES
            or any(not _int(n, 2, 60) for n in phases.values())
            or sum(phases.values()) != item["samples"]):
        return [], False, "missing_idle_or_camera_controls"
    changes = item.get("top_relative_changes")
    total = item["changed_candidate_words"]
    if (not isinstance(changes, list) or len(changes) > 100
            or len(changes) != min(100, total)):
        return [], False, "truncated_or_inconsistent_change_rows"
    seen = set()
    eligible = []
    for row in changes:
        if not isinstance(row, Mapping):
            return [], False, "invalid_candidate_row"
        region = row.get("region")
        if region == "main":
            extent = 0x100
        elif isinstance(region, str):
            match = _CHILD.fullmatch(region)
            if match is None:
                return [], False, "invalid_region_or_offset"
            parent = int(match.group(1), 16)
            if parent % 4 or parent > 0xFC or count == 0:
                return [], False, "invalid_region_or_offset"
            extent = 0x80
        else:
            return [], False, "invalid_region_or_offset"
        off_str = row.get("offset")
        offset = _OFFSET.fullmatch(off_str) if isinstance(off_str, str) else None
        if offset is None:
            return [], False, "invalid_region_or_offset"
        pos = int(offset.group(1), 16)
        if pos % 4 or pos >= extent or (region, pos) in seen:
            return [], False, "invalid_region_or_offset"
        seen.add((region, pos))
        within, boundary, floatshape = (row.get(k) for k in
                    ("within_stage_changes", "between_stage_changes",
                     "plausible_float_changes"))
        if (not _int(within, 0, item["samples"] - 1)
                or not _int(boundary, 0, item["samples"] - 1)
                or not _int(floatshape, 0, item["samples"] - 1)
                or within + boundary == 0
                or within + boundary > item["samples"] - 1
                or floatshape > within + boundary):
            return [], False, "invalid_change_counts"
        eligible.append({"region": region, "relative_offset": f"+0x{pos:03X}",
                         "within_stage_changes": within,
                         "between_stage_changes": boundary,
                         "float_shaped_changes": floatshape})
    return eligible, total > 100 or truncated_child, None


def review_golfer_probe_summaries(reports: Iterable[Mapping], *,
                                  max_reports: int = 32,
                                  frame_span_advisory: int = 12) -> dict:
    """Triage already-published-shape S002 local controls, not real swing data.

    This intentionally cannot train or rank candidate fields as club power.
    Multiple captures from an unknown boot are not independent trials.
    """
    if (not _int(max_reports, 1, 100)
            or not _int(frame_span_advisory, 0, 120)):
        raise ValueError("invalid review limits")
    data = list(islice(reports, max_reports + 1))
    if len(data) > max_reports:
        raise ValueError("too many reports")
    ids = Counter(x.get("id") for x in data
                  if isinstance(x, Mapping) and _safe_id(x.get("id")))
    reject = Counter()
    diagnostics = Counter()
    ranked = defaultdict(lambda: {"capture_files": 0, "within_stage": 0,
                                   "between_stage": 0, "float_shaped": 0})
    accepted = static = slow = truncated = 0
    for item in data:
        if not isinstance(item, Mapping):
            reject["not_a_dict"] += 1
            continue
        if _contains_private_keys(item):
            reject["raw_or_private_input_rejected"] += 1
            continue
        if item.get("diagnostic") == "no_unique_golfer_pointer_chain":
            n = item.get("candidate_chains")
            diagnostics["zero" if n == 0 else
                        "ambiguous" if _int(n, 2, 2) else "invalid"] += 1
            continue
        if _safe_id(item.get("id")) and ids[item["id"]] > 1:
            reject["duplicate_capture_id"] += 1
            continue
        rows, partial, reason = _check_summary(item)
        if reason:
            reject[reason] += 1
            continue
        accepted += 1
        if item["max_non_atomic_frame_span"] > frame_span_advisory:
            slow += 1
        if partial:
            truncated += 1
        if item["changed_candidate_words"] == 0:
            static += 1
        for w in rows:
            key = (w["region"], w["relative_offset"])
            s = ranked[key]
            s["capture_files"] += 1
            s["within_stage"] += w["within_stage_changes"]
            s["between_stage"] += w["between_stage_changes"]
            s["float_shaped"] += w["float_shaped_changes"]
    candidates = [{"region": region, "relative_offset": pos,
                   "candidate_class": "idle_or_aim_negative_control_not_power",
                   **stats, "verified_power": False}
                  for (region, pos), stats in ranked.items()]
    candidates.sort(key=lambda x: (-x["capture_files"], -x["within_stage"],
                                   x["region"], x["relative_offset"]))
    if diagnostics["zero"] or diagnostics["ambiguous"]:
        action = ("S002: source-validate scene-manager singleton, no unique "
                  "live RPGolMain identified. Do not dereference guessed addresses.")
    elif not accepted:
        action = ("S002: fix source/mode/scene safety gates before real-game use.")
    elif static == accepted:
        action = ("S002: bounded candidate parent/child windows had no "
                  "changed words under idle/aim controls. Inspect actual golfer "
                  "member ownership offline; do not infer absent physics.")
    else:
        action = ("S002: changed candidate parent/child words were seen during "
                  "idle/aim controls. Use negative-control timing and source "
                  "member ownership before any same-shot club-power comparison.")
    return {
        "schema_version": 2,
        "kind": "offline-golfer-candidate-negative-control-review",
        "reports_received": len(data),
        "accepted_candidate_reports": accepted,
        "invalid_report_reasons": dict(sorted(reject.items())),
        "nonunique_root_diagnostics": dict(sorted(diagnostics.items())),
        "candidate_changes_truncated_reports": truncated,
        "slow_non_atomic_frame_reports": slow,
        "unchanged_candidate_reports": static,
        "candidate_regions": candidates[:100],
        "candidate_files_are_not_verified_independent_boots": True,
        "real_swing_observations": 0,
        "confirmed_club_position": False,
        "confirmed_game_power": False,
        "ready_for_power_regression": False,
        "estimated_power_percent": None,
        "requires_S000_public_schema_review": True,
        "next_action": action,
        "warning": ("Source-gated candidate RPGolMain and its first-level "
                    "pointer-shaped children are NOT proven club/power fields. "
                    "Idle/aim changes are controls. Do not use 100ft off-green "
                    "penalty as physical ball carry.")
    }
