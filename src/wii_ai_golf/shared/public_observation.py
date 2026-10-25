"""Fail-closed public observation gate for the existing Git-credential publisher.

The capture owner produces observations; this module validates only the
small, versioned public contract immediately before a Git write. It never
reads private captures, talks to Dolphin or contacts the network.
"""
from __future__ import annotations

from datetime import datetime
import json
import math
import re

TRIAL_ID = re.compile(r"(?:offline-)?[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8,12}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
GIT_SHA = re.compile(r"(?:[a-f0-9]{40}|unavailable)\Z")
OFFSET = re.compile(r"\+0x[0-9A-F]{1,5}\Z")
PUBLIC_SIZE_LIMIT = 96_000
KINDS = frozenset({"test", "v1", "golf-memory-phase-differential"})
PHASES = frozenset({"idle", "aim_only", "a_hold", "club_motion",
                    "shot_attempt", "settled", "pre", "post"})
OBSERVATIONS = frozenset({"unchanged", "camera_moved", "club_moved",
                          "ball_hit", "no_contact", "unknown"})
REGIONS = frozenset({"golf_config", "golf_field", "sports_sequence",
                     "minimap_ball_effect", "minimap_player_effect",
                     "minimap_shot_line_effect"})
ROLES = frozenset({"unknown", "hole_score_storage", "game_mode",
                   "current_hole", "golf_score_storage", "sport",
                   "sequence", "training_game", "golf_final_hole",
                   "golf_mode", "shadow_pointer", "tree_shadow_timer",
                   "current_pin_pointer", "current_start_pointer",
                   "cup_pointer", "green_slope_opacity",
                   "minimap_player_effect_pointer",
                   "minimap_shot_line_effect_pointer",
                   "minimap_ball_effect_pointer", "minimap_rendering_unknown"})
V1_BASE = frozenset({"schema", "id", "kind", "started_utc", "git_commit",
                     "process_exit_code", "verified_game_score"})
V1_EXTRA = frozenset({"requested_a_lead_frames", "requested_motion_scale",
                      "requested_speed_scale", "requested_backswing_scale",
                      "study_id", "trial_index", "trial_count", "bridge_sha256",
                      "capture_status", "human", "controller",
                      "settled_screen_observation", "warning"})
HUMAN = frozenset({"contact_human", "initial_club_pose_human",
                   "finished_on_green_human", "displayed_distance_human",
                   "displayed_unit_human", "shot_start_frame_before_controller_trace",
                   "displayed_power_percent_human", "motion_timing_human"})
CONTROLLER = frozenset({"trace_sha256", "generated_trace_frames",
                        "a_lead_requested_frames", "a_lead_observed_frame_delta",
                        "motion_scale", "speed_scale", "backswing_scale"})
MEMORY_FIELDS = frozenset({"schema_version", "kind", "study_id", "id", "scope",
                           "sample_count", "phase_sample_counts",
                           "max_non_atomic_frame_span", "mean_non_atomic_frame_span",
                           "skipped_relocated_windows", "changed_word_count",
                           "top_changed_relative_words", "human_observations",
                           "confirmed_power_address", "confirmed_club_pose_address",
                           "confirmed_ball_position_address", "warning", "origin"})


def _number(value, lo=0, hi=1_000_000):
    return type(value) in (int, float) and math.isfinite(value) and lo <= value <= hi


def _integer(value, lo=0, hi=1_000_000):
    return type(value) is int and lo <= value <= hi


def _keys(row, allowed):
    if type(row) is not dict or not set(row).issubset(allowed):
        raise ValueError("Public record has unexpected or private fields")


def _valid_human(values):
    _keys(values, HUMAN)
    enumerated = {
        "contact_human": {"yes", "no", "unknown"},
        "finished_on_green_human": {"yes", "no", "unknown"},
        "initial_club_pose_human": {"back", "center", "forward", "unknown"},
        "displayed_unit_human": {"ft", "yd", "m", "unknown", "not-visible"},
        "motion_timing_human": {"early", "late", "on-time", "unknown"},
    }
    for key, value in values.items():
        if key in enumerated:
            if value is not None and value not in enumerated[key]:
                raise ValueError("Unrecognized human observation label")
        elif key in ("displayed_distance_human", "displayed_power_percent_human"):
            if value is not None and not _number(value, 0, 100_000):
                raise ValueError("Unrecognized human numeric observation")
        elif value is not None and not _integer(value, 0, 1_000_000):
            raise ValueError("Unrecognized human frame value")


def _valid_controller(values):
    _keys(values, CONTROLLER)
    for key, value in values.items():
        if key == "trace_sha256":
            if value is not None and (type(value) is not str or not SHA.fullmatch(value)):
                raise ValueError("Invalid public controller trace")
        elif key.endswith("_scale"):
            if value is not None and not _number(value, 0, 4):
                raise ValueError("Invalid public controller scale")
        elif value is not None and not _integer(value, 0, 100_000):
            raise ValueError("Invalid public controller count")


def _legacy_public(record):
    if record.get("schema") != 1 or record.get("verified_game_score") is not False:
        raise ValueError("Unverified execution record must not claim a game score")
    if not _integer(record.get("process_exit_code"), 0, 65_535):
        # A process may legitimately exit nonzero; preserve the observed fact.
        if not _integer(record.get("process_exit_code"), -65_535, 65_535):
            raise ValueError("Invalid process exit code")
    git = record.get("git_commit")
    if type(git) is not str or not GIT_SHA.fullmatch(git):
        raise ValueError("Invalid Git revision")
    utc = record.get("started_utc")
    if type(utc) is not str or len(utc) > 48:
        raise ValueError("Missing UTC timestamp")
    try:
        if datetime.fromisoformat(utc).tzinfo is None:
            raise ValueError("Missing timestamp timezone")
    except ValueError as exc:
        raise ValueError("Invalid UTC timestamp") from exc
    if record["kind"] == "test":
        _keys(record, V1_BASE | {"test_pattern", "outcome"})
        if record.get("outcome") not in ("pass", "fail") or (
            record["outcome"] == "pass") != (record["process_exit_code"] == 0):
            raise ValueError("Test outcome contradicts process exit")
        if record.get("test_pattern") not in ("test_*.py",) and (
            type(record.get("test_pattern")) is not str
            or not re.fullmatch(r"test_[A-Za-z0-9_*?-]{1,64}\.py", record["test_pattern"])):
            raise ValueError("Unsafe test pattern")
        return dict(record)
    _keys(record, V1_BASE | V1_EXTRA)
    if not _integer(record.get("requested_a_lead_frames"), 0, 90):
        raise ValueError("Invalid A lead")
    for key in ("requested_motion_scale", "requested_speed_scale",
                "requested_backswing_scale"):
        if not _number(record.get(key), 0, 4):
            raise ValueError("Invalid requested controller scale")
    if "study_id" in record and record["study_id"] != "S003-POWER-MAP-10-V1":
        raise ValueError("Unexpected study ID")
    if ("trial_index" in record) != ("trial_count" in record):
        raise ValueError("Incomplete study index")
    if "trial_index" in record:
        if not _integer(record["trial_index"], 1, 10) or record["trial_count"] != 10:
            raise ValueError("Invalid preregistered trial")
    if "bridge_sha256" in record and record["bridge_sha256"] is not None:
        if type(record["bridge_sha256"]) is not str or not SHA.fullmatch(record["bridge_sha256"]):
            raise ValueError("Invalid public bridge fingerprint")
    capture = record.get("capture_status")
    if capture is not None and capture not in (
        "none_or_ambiguous", "summary_too_large", "unexpected_summary_source",
        "unexpected_summary_shape", "sanitized_human_annotation_only",
        "unreadable_summary", "human_fallback_after_missing_collector_summary"):
        raise ValueError("Unknown capture status")
    if "human" in record:
        _valid_human(record["human"])
    if "controller" in record:
        _valid_controller(record["controller"])
    # The nested free-text screen observation and fallback warning remain
    # in LOCAL metadata only; they are never allowed into the public result.
    return {k: v for k, v in record.items()
            if k not in ("settled_screen_observation", "warning")}


def _memory_public(record):
    _keys(record, MEMORY_FIELDS)
    if (record.get("schema_version") != 1
        or record.get("study_id") != "S002-GOLF-MEMORY-PHASES"
        or record.get("scope") not in ("focused", "broad")):
        raise ValueError("Unknown memory observation schema")
    if record.get("origin") not in (None, "existing_private_S002_outcome_capture"):
        raise ValueError("Untrusted memory observation provenance")
    for key in ("confirmed_power_address", "confirmed_club_pose_address",
                "confirmed_ball_position_address"):
        if record.get(key) is not False:
            raise ValueError("Unverified RAM field cannot be asserted as confirmed")
    for key in ("sample_count", "max_non_atomic_frame_span",
                "skipped_relocated_windows", "changed_word_count"):
        if not _integer(record.get(key), 0, 100_000):
            raise ValueError("Invalid memory count")
    if not 2 <= record["sample_count"] <= 240:
        raise ValueError("Invalid capture sample count")
    if not _number(record.get("mean_non_atomic_frame_span"), 0, 1_000):
        raise ValueError("Invalid non-atomic frame span")
    counts = record.get("phase_sample_counts")
    if type(counts) is not dict or not set(counts).issubset(PHASES) or not counts:
        raise ValueError("Invalid memory phase counts")
    if any(not _integer(value, 1, 240) for value in counts.values()) or (
        sum(counts.values()) != record["sample_count"]):
        raise ValueError("Memory phase counts disagree with sample count")
    observations = record.get("human_observations")
    if type(observations) is not list or len(observations) > 8:
        raise ValueError("Invalid human phase annotations")
    for item in observations:
        if type(item) is not dict or set(item) != {"stage", "phase", "observation"}:
            raise ValueError("Unexpected human phase annotation")
        if (not _integer(item["stage"], 0, 7)
            or item["phase"] not in PHASES or item["observation"] not in OBSERVATIONS):
            raise ValueError("Unrecognized human phase observation")
    rows = record.get("top_changed_relative_words")
    if type(rows) is not list or len(rows) > 300:
        raise ValueError("Invalid relative-offset ranking")
    for row in rows:
        if (type(row) is not dict or set(row) != {
            "region", "relative_offset", "documented_role", "within_phase_changes",
            "at_phase_boundary_changes", "pointer_like_changes", "float_like_changes"}
            or row["region"] not in REGIONS or type(row["relative_offset"]) is not str
            or not OFFSET.fullmatch(row["relative_offset"]) or row["documented_role"] not in ROLES):
            raise ValueError("Unsafe memory offset row")
        for key in ("within_phase_changes", "at_phase_boundary_changes",
                    "pointer_like_changes", "float_like_changes"):
            if not _integer(row[key], 0, 240):
                raise ValueError("Invalid memory delta count")
    if type(record.get("warning")) is not str or not record["warning"].startswith(
        "Exploratory non-atomic snapshots. Relative offsets are not identified gameplay fields; human observations are not verified by RAM."):
        raise ValueError("Unrecognized warning label")
    # A fixed warning replaces any arbitrary free-text tail at publication.
    sanitized = dict(record)
    sanitized["warning"] = (
        "Exploratory non-atomic snapshots. Relative offsets are not identified gameplay fields; "
        "human observations are not verified by RAM.")
    return sanitized


def public_observation(record):
    """Only known schema and typed public facts may reach the Git writer."""
    if type(record) is not dict or not isinstance(record.get("id"), str):
        raise ValueError("Missing observation ID")
    if not TRIAL_ID.fullmatch(record["id"]):
        raise ValueError("Unsafe or invalid observation ID")
    kind = record.get("kind")
    if type(kind) is not str or kind not in KINDS:
        raise ValueError("Unsupported public observation kind")
    safe = _memory_public(record) if kind == "golf-memory-phase-differential" else _legacy_public(record)
    encoded = json.dumps(safe, sort_keys=True, allow_nan=False).encode("utf-8")
    if len(encoded) > PUBLIC_SIZE_LIMIT:
        raise ValueError("Public observation exceeds maximum safe size")
    return safe
