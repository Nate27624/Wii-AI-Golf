"""Cross-run audit of SANITIZED Hitting the Green outcome summaries.

No Dolphin, no RAM reads, no screenshot inference, no claimed score decoder.
Exact 32-bit word identities—not rounded floating-point strings—are compared.
"""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Any

from .outcome_recovery import exploratory_ranking_target

MAX_RUNS = 25
MAX_CANDIDATES_PER_RUN = 1000


def _u32(value: Any) -> int:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("candidate before/settled u32 must be a 32-bit integer")
    return value


def _hex(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.startswith("0x"):
        raise ValueError("expected candidate 0x memory address")
    try:
        address = int(raw, 16)
    except ValueError as exc:
        raise ValueError("invalid candidate memory address") from exc
    if not 0x80000000 <= address <= 0x93FFFFFF or address % 4:
        raise ValueError("candidate address not in bounded 4-byte aligned game RAM")
    return f"0x{address:08X}"


def _run(doc: dict[str, Any], index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise ValueError(f"run {index}: expected schema_version=1")
    ranking = doc.get("candidate_ranking")
    if not isinstance(ranking, dict) or not isinstance(ranking.get("candidates"), list):
        raise ValueError(f"run {index}: missing candidate_ranking.candidates")
    if len(ranking["candidates"]) > MAX_CANDIDATES_PER_RUN:
        raise ValueError("too many candidates in a single run")
    candidates = {}
    for row in ranking["candidates"]:
        if not isinstance(row, dict):
            raise ValueError("candidate must be an object")
        address = _hex(row.get("address"))
        if address in candidates:
            raise ValueError(f"duplicate address {address} in one run")
        before = row.get("before")
        settled = row.get("settled")
        if not isinstance(before, dict) or not isinstance(settled, dict):
            raise ValueError("candidate must include before and settled raw words")
        windows = row.get("windows")
        if not isinstance(windows, list) or any(not isinstance(x, str) for x in windows):
            raise ValueError("candidate windows must be a list of strings")
        matches = row.get("matches_displayed_numeric_label_as", [])
        if not isinstance(matches, list) or any(not isinstance(x, str) for x in matches):
            raise ValueError("candidate matches must be a list")
        candidates[address] = {
            "before_bits": _u32(before.get("u32")),
            "settled_bits": _u32(settled.get("u32")),
            "windows": windows,
            "literal_display_matches": matches,
        }
    label = doc.get("human_observation") or {}
    if not isinstance(label, dict):
        raise ValueError("human_observation must be an object")
    value = label.get("displayed_distance_human")
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
        raise ValueError("human displayed distance must be finite numeric or null")
    # Historical sanitized rows can predate the fixed-100ft penalty gate.
    # Never revive an invalid numeric match from their candidate annotations.
    censored_penalty = (
        value is not None
        and exploratory_ranking_target(
            value, displayed_unit=label.get("displayed_unit_human"),
            green=label.get("finished_on_green_human")) is None
    )
    if censored_penalty:
        for row in candidates.values():
            row["literal_display_matches"] = []
    dispatch = doc.get("swing_dispatch") or {}
    requested = doc.get("known_good_swing_request") or {}
    if not isinstance(dispatch, dict) or not isinstance(requested, dict):
        raise ValueError("swing metadata must be objects")
    applied = dispatch.get("applied_frames")
    generated = requested.get("generated_trace_frames")
    for name, count in (("applied", applied), ("generated", generated)):
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError(f"{name} frame count must be nonnegative")
    trace_hash = requested.get("trace_sha256")
    if trace_hash is not None and (not isinstance(trace_hash, str) or len(trace_hash) != 64
                                   or any(c not in "0123456789abcdef" for c in trace_hash)):
        raise ValueError("trace_sha256 must be lowercase 64-character hex")
    prime_requests = requested.get("a_button_only_prime_requests")
    prime_applied = requested.get("a_button_prime_applied")
    if prime_requests is not None and (type(prime_requests) is not int
                                       or not 0 <= prime_requests <= 180):
        raise ValueError("A-button prime count must be 0..180 or null")
    if prime_applied is not None and type(prime_applied) is not bool:
        raise ValueError("a_button_prime_applied must be boolean or null")
    lead_frames = requested.get("a_lead_requested_frames")
    observed_lead = requested.get("a_lead_observed_frame_delta")
    if lead_frames is not None and (type(lead_frames) is not int
                                    or not 0 <= lead_frames <= 90):
        raise ValueError("a_lead_requested_frames must be integer 0..90 or null")
    if observed_lead is not None and (type(observed_lead) is not int
                                      or observed_lead < 0):
        raise ValueError("a_lead_observed_frame_delta must be a nonnegative integer or null")
    overview = {
        "run_number": index,
        "displayed_distance_human": value,
        "displayed_unit_human": label.get("displayed_unit_human"),
        "displayed_distance_censored_penalty": censored_penalty,
        "numeric_distance_target_eligible": False,
        "finished_on_green_human": label.get("finished_on_green_human"),
        "contact_human": label.get("contact_human"),
        "applied_frames": applied,
        "generated_trace_frames": generated,
        "trace_sha256": trace_hash,
        "a_button_only_prime_requests": prime_requests,
        "a_button_prime_applied": prime_applied,
        "a_lead_requested_frames": lead_frames,
        "a_lead_observed_frame_delta": observed_lead,
        "candidate_count_in_summary": len(candidates),
        "candidate_list_truncated": bool(ranking.get("candidates_truncated", False)),
        "literal_memory_matches_to_displayed_number": sum(
            bool(row["literal_display_matches"]) for row in candidates.values()),
    }
    return overview, candidates


def compare_outcome_runs(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare two or more already sanitized JSON summaries without score claims."""
    if not isinstance(reports, list) or not 2 <= len(reports) <= MAX_RUNS:
        raise ValueError(f"requires 2..{MAX_RUNS} outcome summaries")
    parsed = [_run(doc, idx+1) for idx, doc in enumerate(reports)]
    sessions = [overview for overview, _rows in parsed]
    all_maps = [rows for _overview, rows in parsed]
    shared = set.intersection(*(set(x) for x in all_maps))
    union = set.union(*(set(x) for x in all_maps))
    exact_pre = 0
    exact_settled = 0
    identical_transition = 0
    variants = []
    signatures: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for addr in sorted(shared):
        before = [rows[addr]["before_bits"] for rows in all_maps]
        settled = [rows[addr]["settled_bits"] for rows in all_maps]
        if len(set(before)) == 1:
            exact_pre += 1
        if len(set(settled)) == 1:
            exact_settled += 1
        if len(set(before)) == 1 and len(set(settled)) == 1:
            identical_transition += 1
        signatures[tuple(x for pair in zip(before, settled) for x in pair)].append(addr)
        if len(set(settled)) > 1:
            variants.append({
                "address": addr,
                "before_u32_by_run": before,
                "settled_u32_by_run": settled,
                "windows": sorted(set(w for rows in all_maps for w in rows[addr]["windows"])),
                "hypothesis_status": "NOT_VERIFIED_OUTCOME_FIELD",
            })
    signature_groups = [sorted(addresses) for addresses in signatures.values()
                        if len(addresses) > 1]
    signature_groups.sort(key=lambda x: (-len(x), x))
    frame_set = {x["applied_frames"] for x in sessions}
    frame_mismatch = len(frame_set) > 1 or any(x["applied_frames"] is None for x in sessions)
    trace_hashes = [x["trace_sha256"] for x in sessions]
    if all(trace_hashes):
        trace_comparable = len(set(trace_hashes)) == 1
        trace_reason = "same waveform fingerprint" if trace_comparable else "different waveform fingerprints"
    elif frame_mismatch:
        trace_comparable = False
        trace_reason = "frame counts differ or are missing; waveform identity not established"
    else:
        trace_comparable = False
        trace_reason = "equal frame counts alone do not establish waveform identity"
    # Matching swing sample hashes do not prove matching controller inputs:
    # the standalone probe also primes A with BUTTON-ONLY requests before the
    # waveform. Require that separately captured priming program to match.
    complete_prime = all(s["a_button_prime_applied"] is not None
                         and s["a_button_only_prime_requests"] is not None
                         for s in sessions)
    # Legacy summaries can omit frame-measured A lead altogether. Do not
    # declare those full programs comparable with frame-observed protocols
    # just because their waveform SHA and button RPC counts match.
    complete_lead = all(s["a_lead_requested_frames"] is not None
                        and (s["a_lead_requested_frames"] == 0
                             or s["a_lead_observed_frame_delta"] is not None)
                        for s in sessions)
    priming_same = complete_prime and complete_lead and len({
        (s["a_button_prime_applied"], s["a_button_only_prime_requests"],
         s["a_lead_requested_frames"], s["a_lead_observed_frame_delta"])
        for s in sessions}) == 1
    different_labels = len({(str(s["displayed_distance_human"]),
                             s["displayed_unit_human"], s["finished_on_green_human"])
                            for s in sessions}) > 1
    return {
        "schema_version": 1, "study": "S002-HG-OFFLINE-CROSS-RUN-CANDIDATE-COMPARISON",
        "runs": sessions,
        "shared_candidate_addresses": len(shared),
        "candidate_union_addresses": len(union),
        "identical_before_u32_among_shared": exact_pre,
        "identical_settled_u32_among_shared": exact_settled,
        "different_settled_u32_among_shared": len(variants),
        "identical_before_and_settled_transitions_among_shared": identical_transition,
        "unique_before_settled_bit_signatures_among_shared": len(signatures),
        "repeated_value_pattern_groups": signature_groups,
        "different_settled_candidates": variants,
        "human_labels_differ": different_labels,
        "waveforms_proven_identical": trace_comparable,
        "waveform_comparison": trace_reason,
        "button_prime_program_comparable": priming_same,
        "full_controller_program_comparable": trace_comparable and priming_same,
        "ball_position_verified": False, "game_score_verified": False,
        "training_approved": False,
        "censored_penalty_runs": sum(
            row["displayed_distance_censored_penalty"] for row in sessions),
        "warning": ("This compares published, possibly truncated candidate lists only. "
                    "Two labelled shots cannot distinguish swing/setup/run effects from "
                    "landing effects or identify a true game score. Identical RAM values "
                    "across different human labels disfavor a direct raw score mapping; "
                    "different values may reflect transforms, UI animation or counters."),
    }
