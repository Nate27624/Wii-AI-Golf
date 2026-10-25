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

TRIAL_ID = re.compile(r"(?:offline-|cohort-)?[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8,12}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
GIT_SHA = re.compile(r"(?:[a-f0-9]{40}|unavailable)\Z")
OFFSET = re.compile(r"\+0x[0-9A-F]{1,5}\Z")
PUBLIC_SIZE_LIMIT = 96_000
KINDS = frozenset({"test", "v1", "golf-memory-phase-differential",
                  "golf-memory-cohort-relative-words",
                  "golf_scene_root_candidate_triage",
                  "golf-golfer-control-specificity"})
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
    if type(value) not in (int, float) or not lo <= value <= hi:
        return False
    # Reject arbitrarily large integers before float conversion.
    return math.isfinite(float(value))


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
            if value is not None and (type(value) is not str or value not in enumerated[key]):
                raise ValueError("Unrecognized human observation label")
        elif key in ("displayed_distance_human", "displayed_power_percent_human"):
            ceiling = 100 if key == "displayed_power_percent_human" else 100_000
            if value is not None and not _number(value, 0, ceiling):
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
    if type(record.get("schema")) is not int or record["schema"] != 1 or record.get("verified_game_score") is not False:
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
            or type(item["phase"]) is not str or item["phase"] not in PHASES
            or type(item["observation"]) is not str or item["observation"] not in OBSERVATIONS):
            raise ValueError("Unrecognized human phase observation")
    rows = record.get("top_changed_relative_words")
    if type(rows) is not list or len(rows) > 300:
        raise ValueError("Invalid relative-offset ranking")
    for row in rows:
        if (type(row) is not dict or set(row) != {
            "region", "relative_offset", "documented_role", "within_phase_changes",
            "at_phase_boundary_changes", "pointer_like_changes", "float_like_changes"}
            or type(row["region"]) is not str or row["region"] not in REGIONS or type(row["relative_offset"]) is not str
            or not OFFSET.fullmatch(row["relative_offset"])
            or type(row["documented_role"]) is not str
            or row["documented_role"] not in ROLES):
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


COHORT_FIELDS = frozenset({
    "schema_version", "kind", "study_id", "id", "valid_independent_runs",
    "shared_changed_words_all_runs", "recurrent_changed_words_2plus_runs",
    "distinct_changed_words", "regions_with_changes_by_run_count",
    "recurrent_words", "no_gameplay_variable_verified", "warning",
    "excluded_invalid_or_incomplete_runs",
})
COHORT_WARNING = (
    "Repeated changes are not identified golf power, club pose, flight or score. "
    "Only already-recorded phase-aligned statistics are compared; "
    "frame timing and human labels may differ."
)


def _cohort_public(record):
    """Review the existing S002 cohort schema; never accept raw RAM/free text."""
    if (type(record) is not dict or set(record) != COHORT_FIELDS
        or type(record.get("schema_version")) is not int or record["schema_version"] != 1
        or record.get("study_id") != "S002-GOLF-MEMORY-COHORT"
        or record.get("no_gameplay_variable_verified") is not True
        or record.get("warning") != COHORT_WARNING
        or not record["id"].startswith("cohort-")):
        raise ValueError("Unrecognized S002 cohort public schema")
    count = record.get("valid_independent_runs")
    if not _integer(count, 2, 25):
        raise ValueError("Invalid cohort capture count")
    for name in ("shared_changed_words_all_runs", "recurrent_changed_words_2plus_runs",
                 "distinct_changed_words", "excluded_invalid_or_incomplete_runs"):
        if not _integer(record.get(name), 0, 100_000):
            raise ValueError("Invalid cohort aggregate count")
    if not (record["shared_changed_words_all_runs"]
            <= record["recurrent_changed_words_2plus_runs"]
            <= record["distinct_changed_words"]):
        raise ValueError("Inconsistent cohort summary counts")
    regions = record.get("regions_with_changes_by_run_count")
    if (type(regions) is not dict or not set(regions).issubset(REGIONS)
        or any(not _integer(v, 1, count) for v in regions.values())):
        raise ValueError("Invalid cohort region recurrence")
    rows = record.get("recurrent_words")
    if type(rows) is not list or len(rows) > 250:
        raise ValueError("Invalid cohort relative-offset rows")
    seen = set()
    for row in rows:
        if (type(row) is not dict or set(row) != {
            "region", "relative_offset", "runs_changed", "runs_within_phase",
            "runs_at_phase_boundary", "within_phase_events", "boundary_events"}
            or type(row["region"]) is not str or row["region"] not in REGIONS
            or type(row["relative_offset"]) is not str
            or not OFFSET.fullmatch(row["relative_offset"])):
            raise ValueError("Invalid cohort relative-offset entry")
        key = (row["region"], row["relative_offset"])
        if key in seen:
            raise ValueError("Duplicate cohort offset")
        seen.add(key)
        for name in ("runs_changed", "runs_within_phase", "runs_at_phase_boundary",
                     "within_phase_events", "boundary_events"):
            if not _integer(row[name], 0, 100_000):
                raise ValueError("Invalid cohort occurrence")
        if (not 2 <= row["runs_changed"] <= count
            or row["runs_within_phase"] > row["runs_changed"]
            or row["runs_at_phase_boundary"] > row["runs_changed"]):
            raise ValueError("Impossible cohort run recurrence")
    if len(rows) > record["recurrent_changed_words_2plus_runs"]:
        raise ValueError("Cohort ranked rows exceed summary count")
    return dict(record)


SCENE_ROOT_FIELDS = frozenset({
    "schema_version", "kind", "study_id", "id", "game_id", "revision", "game_mode",
    "candidate_static_cells_checked", "pass_count", "max_sample_frame_span",
    "stable_golf_scene_chain_count", "stable_slot_indices",
    "vtable_in_golf_scene_data_count", "possible_main_pointer_ram_like_count",
    "confirmed_manager_singleton_address", "confirmed_golf_main_type",
    "confirmed_golf_power_address", "warning",
})
SCENE_ROOT_WARNING = (
    "Source-anchored 8-byte static-storage triage only; pointers were "
    "NOT type-proven, no game power or player RAM identified. "
    "No runtime addresses or byte values are included."
)


def _scene_root_public(record):
    """Approve only source-gated candidate COUNTS, never pointer values."""
    if (type(record) is not dict or set(record) != SCENE_ROOT_FIELDS
        or type(record.get("schema_version")) is not int
        or record["schema_version"] != 1
        or record.get("study_id") != "S002-GOLF-SCENE-ROOT-TRIAGE"
        or record.get("game_id") != "RSPE01"
        or not _integer(record.get("revision"), 1, 1)
        or not _integer(record.get("game_mode"), 4, 4)
        or not _integer(record.get("candidate_static_cells_checked"), 2, 2)
        or not _integer(record.get("pass_count"), 2, 2)
        or not _integer(record.get("max_sample_frame_span"), 0, 40)
        or record.get("warning") != SCENE_ROOT_WARNING):
        raise ValueError("Unrecognized source-gated scene-root public schema")
    count = record.get("stable_golf_scene_chain_count")
    if not _integer(count, 0, 2):
        raise ValueError("Invalid stable scene-root count")
    indices = record.get("stable_slot_indices")
    if (type(indices) is not list or len(indices) != count
        or any(not _integer(index, 0, 1) for index in indices)
        or len(set(indices)) != len(indices)
        or indices != sorted(indices)):
        raise ValueError("Invalid stable scene-root slot indices")
    for name in ("vtable_in_golf_scene_data_count",
                 "possible_main_pointer_ram_like_count"):
        if not _integer(record.get(name), 0, count):
            raise ValueError("Invalid scene-root candidate support count")
    for name in ("confirmed_manager_singleton_address", "confirmed_golf_main_type",
                 "confirmed_golf_power_address"):
        if record.get(name) is not False:
            raise ValueError("Scene-root probe cannot claim verified address/type/power")
    return dict(record)



# PR #135's OFFLINE projection from local PR #129 RAW-PRIVATE samples.
# Never accept runtime addresses, RAM hex, arbitrary nested keys or private paths.
GOLFER_CONTROLS_FIELDS = frozenset({
    "schema_version", "kind", "id", "study_id", "sample_count",
    "idle_samples", "aim_samples", "idle_opportunities", "aim_opportunities",
    "max_non_atomic_frame_span", "timing_limited", "candidate_child_regions",
    "changed_word_count", "top_relative_words", "truncated_changed_words",
    "power_verified", "club_pose_verified", "warning",
})
GOLFER_CONTROLS_ROW = frozenset({
    "region", "relative_offset", "idle_changes", "idle_opportunities",
    "aim_changes", "aim_opportunities", "control_class",
})
GOLFER_CONTROLS_WARNING = (
    "Controls only: dynamic offsets are NOT game swing-power, pose or ball "
    "decoders; private memory and absolute pointers remain local."
)
GOLFER_CONTROL_CLASSES = frozenset({
    "background_dynamic", "aim_enriched_control_candidate",
    "aim_only_weak", "idle_dynamic", "mixed_control_change",
})


def _golfer_controls_public(record):
    """Typed bounded safety gate, no live controller/score claims allowed."""
    if (type(record) is not dict or set(record) != GOLFER_CONTROLS_FIELDS
        or record.get("schema_version") != 1
        or record.get("kind") != "golf-golfer-control-specificity"
        or record.get("study_id") != "S002-GOLFER-CONTROL-SPECIFICITY"
        or record.get("warning") != GOLFER_CONTROLS_WARNING
        or record.get("power_verified") is not False
        or record.get("club_pose_verified") is not False):
        raise ValueError("Unknown golfer-control public observation")
    total = record.get("sample_count")
    idle = record.get("idle_samples")
    aim = record.get("aim_samples")
    no = record.get("idle_opportunities")
    na = record.get("aim_opportunities")
    if (not _integer(total, 4, 60) or not _integer(idle, 2, 58)
        or not _integer(aim, 2, 58) or idle + aim != total
        or not _integer(no, 1, idle - 1) or no < idle - 2
        or not _integer(na, 1, aim - 1) or na != aim - 1
        or not _integer(record.get("max_non_atomic_frame_span"), 0, 240)
        or type(record.get("timing_limited")) is not bool
        or record["timing_limited"] != (record["max_non_atomic_frame_span"] > 12)
        or not _integer(record.get("candidate_child_regions"), 0, 16)
        or not _integer(record.get("changed_word_count"), 0, 576)
        or type(record.get("truncated_changed_words")) is not bool):
        raise ValueError("Invalid golfer-control sampling counts")
    changed = record["changed_word_count"]
    rows = record.get("top_relative_words")
    if (type(rows) is not list or len(rows) != min(changed, 100)
        or record["truncated_changed_words"] != (changed > 100)):
        raise ValueError("Golfer-control candidate count inconsistent")
    seen = set()
    for row in rows:
        if type(row) is not dict or set(row) != GOLFER_CONTROLS_ROW:
            raise ValueError("Unsafe candidate control row")
        region = row.get("region")
        if region == "main":
            extent = 0x100
        elif type(region) is str:
            match = re.fullmatch(r"child_at_main\\+0x([0-9A-F]{3})", region)
            if match is None or int(match.group(1), 16) > 0xFC or int(match.group(1), 16) % 4:
                raise ValueError("Invalid bounded child region")
            extent = 0x80
            if record["candidate_child_regions"] == 0:
                raise ValueError("Missing child region evidence")
        else:
            raise ValueError("Invalid candidate region")
        offset = row.get("relative_offset")
        if type(offset) is not str or not re.fullmatch(r"\\+0x[0-9A-F]{3}", offset):
            raise ValueError("Invalid relative candidate offset")
        pos = int(offset[3:], 16)
        if pos >= extent or pos % 4 or (region, pos) in seen:
            raise ValueError("Invalid or duplicated candidate word")
        seen.add((region, pos))
        if (row.get("idle_opportunities") != no
            or row.get("aim_opportunities") != na
            or not _integer(row.get("idle_changes"), 0, no)
            or not _integer(row.get("aim_changes"), 0, na)
            or row["idle_changes"] + row["aim_changes"] == 0
            or row.get("control_class") not in GOLFER_CONTROL_CLASSES):
            raise ValueError("Invalid golfer-control phase counts/label")
    return dict(record)



def public_observation(record):
    """Only known schema and typed public facts may reach the Git writer."""
    if type(record) is not dict or not isinstance(record.get("id"), str):
        raise ValueError("Missing observation ID")
    if not TRIAL_ID.fullmatch(record["id"]):
        raise ValueError("Unsafe or invalid observation ID")
    kind = record.get("kind")
    if type(kind) is not str or kind not in KINDS:
        raise ValueError("Unsupported public observation kind")
    if kind == "golf-golfer-control-specificity":
        if record["id"].startswith(("cohort-", "offline-")):
            raise ValueError("Invalid control-study record ID")
        safe = _golfer_controls_public(record)
    elif kind == "golf_scene_root_candidate_triage":
        if record["id"].startswith(("cohort-", "offline-")):
            raise ValueError("Invalid scene-root record identifier")
        safe = _scene_root_public(record)
    elif kind == "golf-memory-cohort-relative-words":
        safe = _cohort_public(record)
    elif kind == "golf-memory-phase-differential":
        if record["id"].startswith("cohort-"):
            raise ValueError("Cohort ID cannot identify an individual capture")
        safe = _memory_public(record)
    else:
        if record["id"].startswith(("cohort-", "offline-")):
            raise ValueError("Invalid legacy trial identifier prefix")
        safe = _legacy_public(record)
    encoded = json.dumps(safe, sort_keys=True, allow_nan=False).encode("utf-8")
    if len(encoded) > PUBLIC_SIZE_LIMIT:
        raise ValueError("Public observation exceeds maximum safe size")
    return safe
