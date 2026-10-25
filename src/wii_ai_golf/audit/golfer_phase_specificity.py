"""Offline, source-scoped negative-control audit of S002 golfer candidate RAW-PRIVATE captures.

Input is LOCAL private RAM; output contains ONLY validated relative offsets,
per-phase change counts and bounded sampling metadata. No ROM, Dolphin or RPC.
No claim that a dynamic candidate is club pose, power or ball state.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re
import struct

MAX_ROWS = 60
MAX_CHILDREN = 16
MAX_FRAME_SPAN = 240
MAIN_BYTES = 0x100
CHILD_BYTES = 0x80
ADDR = re.compile(r"0x[89][0-9A-Fa-f]{7}\Z")
CHILD = re.compile(r"\+0x([0-9A-Fa-f]{3})\Z")
WARNING = ("Controls only: dynamic offsets are NOT game swing-power, pose or ball "
           "decoders; private memory and absolute pointers remain local.")


def _addr(value):
    return type(value) is str and ADDR.fullmatch(value) is not None


def _bytes(value, size):
    if type(value) is not str or len(value) != size * 2:
        raise ValueError("Invalid fixed-size local memory window")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("Malformed local memory bytes") from exc


def _wordmap(row):
    if type(row) is not dict:
        raise ValueError("Invalid snapshot")
    values = {"main": _bytes(row.get("bytes_hex"), MAIN_BYTES)}
    children = row.get("child_windows", {})
    addresses = row.get("watched_child_addresses", {})
    if type(children) is not dict or type(addresses) is not dict:
        raise ValueError("Invalid child object map")
    if len(children) > MAX_CHILDREN or set(children) != set(addresses):
        raise ValueError("Child window provenance incomplete")
    for key, contents in children.items():
        if type(key) is not str:
            raise ValueError("Invalid child offset type")
        match = CHILD.fullmatch(key)
        if match is None or int(match.group(1), 16) > 0xFC or int(match.group(1), 16) % 4:
            raise ValueError("Child pointer not referenced by bounded main object")
        if not _addr(addresses[key]):
            raise ValueError("Malformed child pointer provenance")
        values["child_at_main" + key.upper().replace("X", "x")] = _bytes(contents, CHILD_BYTES)
    return values


def _words(data):
    return struct.unpack(">" + str(len(data) // 4) + "I", data)


def _classify(idle, aim, ni, na):
    idle_rate, aim_rate = idle / ni, aim / na
    if idle_rate >= .5 and aim_rate >= .5:
        return "background_dynamic"
    if aim >= 2 and aim_rate - idle_rate >= .25:
        return "aim_enriched_control_candidate"
    if idle and not aim:
        return "idle_dynamic"
    if aim and not idle:
        return "aim_only_weak"
    return "mixed_control_change"


def analyze(rows, *, run_id):
    """Determine stage-specific controls; never conflate phase boundaries with input."""
    if (type(rows) is not list or not 4 <= len(rows) <= MAX_ROWS
        or type(run_id) is not str
        or not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8,12}", run_id)):
        raise ValueError("Invalid bounded capture or public identifier")
    prior = None
    first_provenance = None
    seen_stage = {}
    stage_counts = Counter()
    opportunities = Counter()
    changes = defaultdict(Counter)
    frame_spans = []
    region_set = None
    for row in rows:
        stage, phase = row.get("stage"), row.get("phase")
        if type(stage) is not int or stage not in (0, 1, 2):
            raise ValueError("Unexpected stage index")
        expected_phase = "aim_only" if stage == 1 else "idle"
        if phase != expected_phase or (prior is not None and stage < prior[0]):
            raise ValueError("Not the preregistered idle/aim/idle stage order")
        if prior is not None and stage > prior[0] + 1:
            raise ValueError("Missing phase stage")
        if stage in seen_stage and seen_stage[stage] != phase:
            raise ValueError("Stage label changed")
        seen_stage[stage] = phase
        start, end = row.get("frame_start"), row.get("frame_end")
        if (type(start) is not int or type(end) is not int or start < 0
            or end < start or end - start > MAX_FRAME_SPAN
            or (prior is not None and start < prior[1])):
            raise ValueError("Invalid or overlapping emulated frame brackets")
        frame_spans.append(end - start)
        provenance = (row.get("runtime_scene_address"),
                      row.get("runtime_golf_main_address"),
                      tuple(sorted(row.get("watched_child_addresses", {}).items())))
        if not all(_addr(p) for p in provenance[:2]):
            raise ValueError("Missing private same-instance provenance")
        if first_provenance is None:
            first_provenance = provenance
        elif provenance != first_provenance:
            raise ValueError("Runtime candidate pointers relocated")
        windows = _wordmap(row)
        if region_set is None:
            region_set = set(windows)
        elif set(windows) != region_set:
            raise ValueError("Window set changed during capture")
        stage_counts[stage] += 1
        if prior is not None and prior[0] == stage:
            opportunities[phase] += 1
            previous_windows = prior[2]
            for region in windows:
                for offset, (a, b) in enumerate(zip(
                    _words(previous_windows[region]), _words(windows[region]))):
                    if a != b:
                        changes[(region, offset * 4)][phase] += 1
        prior = (stage, end, windows)
    if stage_counts[0] < 2 or stage_counts[1] < 2 or (
        2 in stage_counts and stage_counts[2] < 2):
        raise ValueError("Need at least two samples per idle/aim stage")
    if len(stage_counts) not in (2, 3) or not opportunities["idle"] or not opportunities["aim_only"]:
        raise ValueError("Missing idle and aim control comparisons")
    idle_n, aim_n = opportunities["idle"], opportunities["aim_only"]
    candidates = []
    for (region, offset), counts in changes.items():
        idle, aim = counts["idle"], counts["aim_only"]
        label = _classify(idle, aim, idle_n, aim_n)
        candidates.append({
            "region": region, "relative_offset": f"+0x{offset:03X}",
            "idle_changes": idle, "idle_opportunities": idle_n,
            "aim_changes": aim, "aim_opportunities": aim_n,
            "control_class": label,
        })
    # Aim-specific controls first, then useful background counter negatives.
    rank = {"aim_enriched_control_candidate": 0, "aim_only_weak": 1,
            "background_dynamic": 2, "idle_dynamic": 3, "mixed_control_change": 4}
    candidates.sort(key=lambda x: (
        rank[x["control_class"]],
        -(x["aim_changes"] / aim_n - x["idle_changes"] / idle_n),
        x["region"], x["relative_offset"]))
    return {
        "schema_version": 1, "kind": "golf-golfer-control-specificity",
        "id": run_id, "study_id": "S002-GOLFER-CONTROL-SPECIFICITY",
        "sample_count": len(rows), "idle_samples": stage_counts[0] + stage_counts[2],
        "aim_samples": stage_counts[1], "idle_opportunities": idle_n,
        "aim_opportunities": aim_n, "max_non_atomic_frame_span": max(frame_spans),
        "timing_limited": max(frame_spans) > 12,
        "candidate_child_regions": len(region_set) - 1,
        "changed_word_count": len(candidates),
        "top_relative_words": candidates[:100],
        "truncated_changed_words": len(candidates) > 100,
        "power_verified": False, "club_pose_verified": False,
        "warning": WARNING,
    }
