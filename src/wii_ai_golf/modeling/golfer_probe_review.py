"""S003 read-only triage of S002 candidate RPGolMain probe summaries.

Consumes PUBLIC-SHAPE / locally sanitized JSON dictionaries only. Never reads
Dolphin, bytes, private pointers, or a game file. No address or power decoder.
The S002 probe is currently unmerged; this is a downstream interface review.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
import re

_ID = re.compile(r"[A-Za-z0-9_.-]{1,90}\Z")
_OFFSET = re.compile(r"\+0x([0-9A-Fa-f]{1,3})\Z")
# The source note only names the expected candidate chain; it is NOT a proof.
_SOURCE_NOTE = ("EGG::SceneManager +0xC scene, +0x18 scene ID; "
                "RPSportsBaseScene +0x54 sport; RPGolScene +0x9C RPGolMain")
_ALLOWED_PHASES = frozenset(("idle", "aim_only"))


def _integer(x: object, lo: int, hi: int) -> bool:
    return type(x) is int and lo <= x <= hi


def _valid_id(s: object) -> bool:
    return isinstance(s, str) and bool(_ID.fullmatch(s))


def _accept_sanitized_summary(item: Mapping) -> tuple[list[dict], str | None]:
    if (item.get("kind") != "local-golfer-memory-audit"
            or type(item.get("schema_version")) is not int
            or item.get("schema_version") != 1
            or not _valid_id(item.get("id"))):
        return [], "invalid_identity_or_schema"
    if (item.get("candidate_only") is not True
            or item.get("source_claim") != _SOURCE_NOTE
            or item.get("game_id") != "RSPE01"
            or type(item.get("revision")) is not int
            or item["revision"] != 1
            or type(item.get("game_mode")) is not int
            or item["game_mode"] != 4):
        return [], "invalid_source_revision_or_mode"
    if (type(item.get("matched_scene_chains")) is not int
            or item.get("matched_scene_chains") != 1
            or item.get("observed_creator_scene_id_matches_golf") is not True):
        return [], "scene_chain_not_fully_gated"
    if (not _integer(item.get("global_pointer_candidates"), 1, 512)
            or not _integer(item.get("samples"), 4, 60)
            or not _integer(item.get("changed_candidate_words"), 0, 64)):
        return [], "invalid_capture_counts"
    phases = item.get("phase_sample_counts")
    if (not isinstance(phases, Mapping) or set(phases) != _ALLOWED_PHASES
            or any(not _integer(n, 2, 60) for n in phases.values())
            or sum(phases.values()) != item["samples"]):
        return [], "missing_or_invalid_idle_camera_controls"
    if not _integer(item.get("max_non_atomic_frame_span"), 0, 240):
        return [], "invalid_capture_frame_span"
    rows = item.get("top_relative_changes")
    if (not isinstance(rows, list) or len(rows) > 64
            or len(rows) != item["changed_candidate_words"]):
        return [], "truncated_or_invalid_change_rows"
    seen = set()
    allowed = []
    for row in rows:
        if not isinstance(row, Mapping):
            return [], "invalid_relative_word"
        label = row.get("offset")
        match = _OFFSET.fullmatch(label) if isinstance(label, str) else None
        if match is None:
            return [], "invalid_relative_word"
        offset = int(match.group(1), 16)
        if offset % 4 or offset > 0xFC or offset in seen:
            return [], "invalid_relative_word"
        seen.add(offset)
        within = row.get("within_stage_changes")
        between = row.get("between_stage_changes")
        floatlike = row.get("plausible_float_changes")
        if (not _integer(within, 0, item["samples"] - 1)
                or not _integer(between, 0, item["samples"] - 1)
                or not _integer(floatlike, 0, item["samples"] - 1)
                or within + between > item["samples"] - 1
                or floatlike > within + between
                or within + between == 0):
            return [], "invalid_relative_change_counts"
        allowed.append({"relative_offset": f"+0x{offset:03X}",
                        "within_stage_changes": within,
                        "between_stage_changes": between,
                        "plausible_float_changes": floatlike})
    return allowed, None


def review_golfer_probe_summaries(reports: Iterable[Mapping], *,
                                  max_reports: int = 32,
                                  frame_span_advisory: int = 12) -> dict:
    """Classify source-gated candidate snapshots; NEVER predict shot power.

    A snapshot made during idle/camera is a NEGATIVE CONTROL, not a real
    swing observation. Recurrence across files is not proof of distinct boots.
    """
    if (not _integer(max_reports, 1, 100)
            or not _integer(frame_span_advisory, 0, 120)):
        raise ValueError("invalid report limits")
    data = list(reports)
    if len(data) > max_reports:
        raise ValueError("too many report records")
    ids = Counter(row.get("id") for row in data if isinstance(row, Mapping)
                  and _valid_id(row.get("id")))
    rejects = Counter()
    diagnostic_counts = Counter()
    counts = defaultdict(lambda: {"capture_files": 0, "within_stage": 0,
                                  "between_stage": 0, "float_shaped": 0})
    accepted = slow = static_captures = 0
    for item in data:
        if not isinstance(item, Mapping):
            rejects["not_a_dictionary"] += 1
            continue
        # The S002 no-unique diagnostic has no valid gameplay bytes.
        if item.get("diagnostic") == "no_unique_golfer_pointer_chain":
            n = item.get("candidate_chains")
            diagnostic_counts["zero" if n == 0 else "ambiguous" if
                              _integer(n, 2, 512) else "invalid"] += 1
            continue
        if _valid_id(item.get("id")) and ids[item["id"]] > 1:
            rejects["duplicate_capture_id"] += 1
            continue
        words, reason = _accept_sanitized_summary(item)
        if reason:
            rejects[reason] += 1
            continue
        accepted += 1
        if item["max_non_atomic_frame_span"] > frame_span_advisory:
            slow += 1
        if not words:
            static_captures += 1
        for word in words:
            slot = counts[word["relative_offset"]]
            slot["capture_files"] += 1
            slot["within_stage"] += word["within_stage_changes"]
            slot["between_stage"] += word["between_stage_changes"]
            slot["float_shaped"] += word["plausible_float_changes"]
    ranked = [{"relative_offset": off,
               "candidate_class": "idle_or_camera_confounder_not_club_power",
               **nums, "verified_power": False}
              for off, nums in counts.items()]
    ranked.sort(key=lambda z: (-z["capture_files"], -z["within_stage"],
                               z["relative_offset"]))
    if diagnostic_counts["zero"] or diagnostic_counts["ambiguous"]:
        next_action = ("S002: source-confirm scene-manager singleton/pointer "
                       "ownership; no gameplay field or address established "
                       "by a nonunique candidate census.")
    elif not accepted:
        next_action = ("S002: validate revision/scene-creator/mode safety "
                       "and capture one canonical read-only source-gated "
                       "idle/camera diagnostic before any swings.")
    elif static_captures == accepted:
        next_action = ("S002: candidate RPGolMain first 0x100 bytes stayed "
                       "unchanged under existing idle/camera controls; inspect "
                       "source-owned member pointers offline before extending "
                       "bounded capture, not a blind power sweep.")
    else:
        next_action = ("S002: candidate gameplay words changed in idle/camera "
                       "controls; discriminate scene/aim/timing effects with "
                       "per-stage, frame-bracketed negative controls before "
                       "linking to a real swing; no power inference.")
    return {
        "schema_version": 1,
        "kind": "offline-golfer-probe-negative-control-review",
        "input_reports": len(data),
        "accepted_sanitized_candidate_reports": accepted,
        "unverified_independent_boot_count": True,
        "no_unique_chain_diagnostics": dict(sorted(diagnostic_counts.items())),
        "rejection_reasons": dict(sorted(rejects.items())),
        "slow_frame_span_advisory_reports": slow,
        "unchanged_candidate_window_reports": static_captures,
        "candidate_offsets": ranked[:64],
        "output_must_remain_local_until_S000_allowlist": True,
        "observed_real_swing_sample_count": 0,
        "verified_golfer_instance_identity": False,
        "verified_club_angle_signal": False,
        "verified_game_power_signal": False,
        "memory_power_model_ready": False,
        "estimated_power_percent": None,
        "next_action": next_action,
        "warning": ("Candidate object and float-shaped changing words are "
                    "not golfer power. Idle/camera controls cannot identify "
                    "backswing, impact, ball flight or physical carry. "
                    "Never reinterpret off-green 100.0ft as flight distance.")
    }
