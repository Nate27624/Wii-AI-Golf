"""Private/local-only temporal triage of S002 golfer candidate RAM.

Reads an operator's existing -RAW-PRIVATE.jsonl and separately delivered
sanitized S002 summary. Exports ONLY relative offset/counter-pattern
classifications. Never exports raw word values, deltas, pointers, frame
timestamps, local paths, or numerical power; never uploads to GitHub.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import struct

MAX_ROWS = 60
MAX_BYTES = 2 * 1024 * 1024
MAIN_SIZE = 0x100
CHILD_SIZE = 0x80


def _strict_int(v, low, high):
    return type(v) is int and low <= v <= high


def _offset(text, extent):
    if (not isinstance(text, str) or not text.startswith("+0x")
            or len(text) != 6):
        raise ValueError("Invalid relative memory offset")
    try:
        value = int(text[3:], 16)
    except ValueError as e:
        raise ValueError("Invalid relative memory offset") from e
    if value % 4 or value >= extent or f"+0x{value:03X}" != text:
        raise ValueError("Unaligned/out-of-bounds relative memory offset")
    return value


def _window(row, region):
    if region == "main":
        hexdata = row.get("bytes_hex")
        size = MAIN_SIZE
    elif isinstance(region, str) and region.startswith("child_at_main"):
        ptr_offset = region[len("child_at_main"):]
        _offset(ptr_offset, MAIN_SIZE)
        hexdata = row.get("child_windows", {}).get(ptr_offset)
        size = CHILD_SIZE
    else:
        raise ValueError("Unknown candidate object region")
    if not isinstance(hexdata, str) or len(hexdata) != 2 * size:
        raise ValueError("Incomplete or incorrect private capture window")
    try:
        return bytes.fromhex(hexdata)
    except ValueError as e:
        raise ValueError("Malformed private capture bytes") from e


def analyze_private_trajectory(rows, report):
    """Only computed booleans/group labels escape. No numeric RAM content."""
    if (not isinstance(rows, list) or len(rows) < 6 or len(rows) > MAX_ROWS
            or type(report) is not dict or
            report.get("schema_version") != 2 or
            report.get("kind") != "local-golfer-memory-audit" or
            report.get("candidate_only") is not True or
            report.get("game_id") != "RSPE01" or
            report.get("revision") != 1 or
            report.get("game_mode") != 4 or
            report.get("actual_scene_id_verified") is not True or
            report.get("manager_backlink_verified") is not True or
            report.get("creator_scene_id_not_used_for_identity") is not True or
            report.get("matched_scene_chains") != 1 or
            report.get("samples") != len(rows)):
        raise ValueError("Source/revision/mode/scene/capture gate failed")
    positions = report.get("first_level_child_parent_offsets")
    if (not isinstance(positions, list) or
            len(positions) != report.get("first_level_child_watch_count") or
            len(set(positions)) != len(positions)):
        raise ValueError("Child batch provenance invalid")
    for x in positions:
        _offset(x, MAIN_SIZE)
    words = report.get("top_relative_changes")
    if (not isinstance(words, list)
            or len(words) != report.get("changed_candidate_words")
            or len(words) > 100):
        raise ValueError("Only full, untruncated candidate change reports accepted")
    parsed = []
    previous = None
    counts = Counter()
    max_span = 0
    last_frame = -1
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed private sample")
        start, end, phase, stage = (row.get("frame_start"), row.get("frame_end"),
                                     row.get("phase"), row.get("stage"))
        if (not _strict_int(start, 0, 2**63-1)
                or not _strict_int(end, start, 2**63-1)
                or start <= last_frame
                or not _strict_int(stage, 0, 3)
                or phase not in ("idle", "aim_only")):
            raise ValueError("Invalid chronological frame/stage record")
        if previous:
            old_stage, old_phase = previous
            if stage not in (old_stage, old_stage + 1) or (
                stage == old_stage and phase != old_phase):
                raise ValueError("Stages are not monotonic or phase changed within stage")
        last_frame = start
        previous = (stage, phase)
        max_span = max(max_span, end-start)
        counts[phase] += 1
        parsed.append((row, stage, start))
    if dict(counts) != report.get("phase_sample_counts"):
        raise ValueError("Private stage counts disagree with sanitized S002 report")
    if max_span != report.get("max_non_atomic_frame_span"):
        raise ValueError("Snapshot frame-span mismatch")
    unique_regions = set()
    trajectories = []
    for entry in words:
        if not isinstance(entry, dict):
            raise ValueError("Malformed sanitized changed-word row")
        region, off = entry.get("region"), entry.get("offset")
        size = MAIN_SIZE if region == "main" else CHILD_SIZE
        idx = _offset(off, size)
        if region != "main":
            if not isinstance(region, str) or not region.startswith("child_at_main"):
                raise ValueError("Unexpected child region")
            if region[len("child_at_main"):] not in positions:
                raise ValueError("Child wasn't in captured source batch")
        key = (region, off)
        if key in unique_regions:
            raise ValueError("Duplicate candidate word")
        unique_regions.add(key)
        values = [struct.unpack_from(">I", _window(raw, region), idx)[0]
                  for raw, _stage, _frame in parsed]
        signed_deltas = []
        for old, new in zip(values, values[1:]):
            delta = (new - old) & 0xFFFFFFFF
            signed_deltas.append(delta if delta < 2**31 else delta - 2**32)
        boundary = sum(signed_deltas[i-1] != 0 and
                       parsed[i][1] != parsed[i-1][1]
                       for i in range(1, len(parsed)))
        within = sum(signed_deltas[i-1] != 0 and
                     parsed[i][1] == parsed[i-1][1]
                     for i in range(1, len(parsed)))
        if (within != entry.get("within_stage_changes")
                or boundary != entry.get("between_stage_changes")):
            raise ValueError("Private RAM changes differ from sanitized S002 evidence")
        frame_deltas = [parsed[i][2] - parsed[i-1][2]
                        for i in range(1, len(parsed))]
        same_frame_ratio = bool(signed_deltas) and all(
            d * frame_deltas[0] == signed_deltas[0] * frames
            for d, frames in zip(signed_deltas, frame_deltas))
        positive = all(x > 0 for x in signed_deltas)
        negative = all(x < 0 for x in signed_deltas)
        trajectories.append({
            "region": region, "relative_offset": off,
            "changes_all_transitions": within + boundary == len(rows) - 1,
            "constant_integer_step": len(set(signed_deltas)) == 1
                                      and signed_deltas[0] != 0,
            "one_direction_monotonic": positive or negative,
            "integer_step_proportional_to_frame_gap": same_frame_ratio,
            # Pure equivalence class: no signed deltas or raw bits leave memory.
            "_delta_signature": tuple(signed_deltas),
            "candidate_interpretation": "idle_camera_continuous_control_not_power"
                if within + boundary == len(rows)-1 else
                "idle_camera_control_not_power",
        })
    signature_ids = {}
    for trajectory in trajectories:
        sig = trajectory.pop("_delta_signature")
        if sig not in signature_ids:
            signature_ids[sig] = len(signature_ids)+1
        trajectory["delta_pattern_group"] = signature_ids[sig]
    return {
        "schema_version": 1,
        "kind": "local-golfer-private-temporal-sanitized",
        "source": "S002_RSPE01_rev1_mode4_readonly_candidate",
        "samples": len(rows),
        "analyzed_changed_words": len(words),
        "distinct_delta_patterns": len(signature_ids),
        "max_non_atomic_frame_span": max_span,
        "frame_span_over_12_frames": max_span > 12,
        "batch_incomplete": report.get("first_level_child_watch_truncated") is True,
        "negative_control_only": True,
        "real_swing_recorded": False,
        "power_verified": False,
        "next_action": ("If only continuous clock-like patterns were found, "
                        "S002 should source-identify golfer/club member "
                        "ownership or cover the truncated later child batch "
                        "under a fresh canonical human-approved run."),
        "offset_patterns": trajectories,
        "local_only_no_public_schema_approval": True,
        "warning": ("No game power, club angle, shot carry, or real impact "
                    "was observed; private absolute addresses and values "
                    "are intentionally discarded."),
    }


def analyze_files(raw: Path, sanitized: Path, output: Path):
    raw, sanitized, output = Path(raw), Path(sanitized), Path(output)
    if (not raw.name.endswith("-RAW-PRIVATE.jsonl") or
            not raw.is_file() or not sanitized.is_file() or
            raw.stat().st_size > MAX_BYTES or
            sanitized.stat().st_size > 128 * 1024 or
            output.exists() or output == raw or output == sanitized):
        raise ValueError("Invalid private/sanitized input, limits or existing output")
    report = json.loads(sanitized.read_text(encoding="utf-8"))
    if report.get("id") != raw.stem:
        raise ValueError("Sanitized report ID does not match private capture")
    rows = []
    with raw.open(encoding="utf-8") as fp:
        for line in fp:
            if len(rows) >= MAX_ROWS:
                raise ValueError("Too many snapshot rows")
            rows.append(json.loads(line))
    result = analyze_private_trajectory(rows, report)
    with output.open("x", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2, sort_keys=True, allow_nan=False)
        fp.write("\n")
    return result
