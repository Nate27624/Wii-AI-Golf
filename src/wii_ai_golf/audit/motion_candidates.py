"""Audit ranked motion candidates; never infer confirmed ball coordinates.

The published S002 candidate list may be TRUNCATED and may repeat a vector
under multiple overlapping memory windows. This audit looks only at the
published subset. A float32 XYZ candidate occupies [address, address+12).
Neither exact address equality nor byte-span overlap certifies semantic identity.
"""
from __future__ import annotations

from collections import defaultdict
from math import isfinite, sqrt
import re
from typing import Any

_HEX = re.compile(r"^(?:0[xX])?[0-9a-fA-F]{1,16}$")
_MAX_CANDIDATES = 10000


def _address(raw: Any) -> int:
    if not isinstance(raw, str) or not _HEX.fullmatch(raw):
        raise ValueError(f"invalid hexadecimal address: {raw!r}")
    return int(raw, 16)


def _hex(value: int) -> str:
    return f"0x{value:08X}"


def _integer(raw: Any, label: str) -> int:
    if type(raw) is not int or raw < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return raw


def _unit_endpoint(vector: Any) -> bool:
    if not isinstance(vector, list) or len(vector) != 3:
        return False
    if any(type(v) not in (int, float) or not isfinite(v) for v in vector):
        return False
    length = sqrt(sum(float(v) ** 2 for v in vector))
    return all(abs(float(v)) <= 1.05 for v in vector) and 0.8 <= length <= 1.2


def _candidate_rank(candidate: dict[str, Any]) -> tuple[int, int, int, str]:
    return (candidate["within_same_scene_changed_steps"], candidate["changed_steps"],
            candidate["observed_samples"], candidate["window"])


def audit_motion_report(report: dict[str, Any],
                        baseline: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return JSON-safe structural diagnostics, never raw memory values."""
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("expected S002 report schema_version=1")
    group = report.get("position_candidates")
    if not isinstance(group, dict) or not isinstance(group.get("candidates"), list):
        raise ValueError("missing position_candidates.candidates list")
    listed = group["candidates"]
    if len(listed) > _MAX_CANDIDATES:
        raise ValueError("too many candidates to audit")
    reported = _integer(group.get("candidate_count"), "candidate_count")
    if reported < len(listed):
        raise ValueError("reported candidate_count less than published list length")
    if type(group.get("candidates_truncated", False)) is not bool:
        raise ValueError("candidates_truncated must be boolean")

    by_address: dict[int, list[dict[str, Any]]] = defaultdict(list)
    bad_offsets = []
    for i, candidate in enumerate(listed):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate {i} is not an object")
        address = _address(candidate.get("candidate_address"))
        window = candidate.get("window")
        if not isinstance(window, str) or not window:
            raise ValueError(f"candidate {i} missing window name")
        fields = ("within_same_scene_changed_steps", "changed_steps", "observed_samples")
        clean = {key: _integer(candidate.get(key), key) for key in fields}
        clean.update({"window": window,
                      "unit_vector_endpoints_hint": _unit_endpoint(candidate.get("first_xyz"))
                      and _unit_endpoint(candidate.get("last_xyz"))})
        if "window_address" in candidate and "offset_hex" in candidate:
            window_start = _address(candidate["window_address"])
            offset = candidate["offset_hex"]
            if not isinstance(offset, str) or not offset.startswith("+"):
                raise ValueError(f"candidate {i} has invalid offset_hex")
            if address != window_start + _address(offset[1:]):
                bad_offsets.append(_hex(address))
        by_address[address].append(clean)

    aliases = []
    for address, copies in sorted(by_address.items()):
        chosen = max(copies, key=_candidate_rank)
        aliases.append({
            "candidate_address": _hex(address),
            "published_rows": len(copies),
            "windows": sorted(set(item["window"] for item in copies)),
            "within_same_scene_changed_steps_max": chosen["within_same_scene_changed_steps"],
            "changed_steps_max": chosen["changed_steps"],
            "unit_vector_endpoints_hint": any(x["unit_vector_endpoints_hint"] for x in copies),
            "alias_statistics_disagree": len({
                (x["within_same_scene_changed_steps"], x["changed_steps"],
                 x["observed_samples"]) for x in copies}) > 1,
        })

    # Groups overlapping float32 XYZ spans, NOT semantic identities.
    clusters: list[dict[str, Any]] = []
    for address in sorted(by_address):
        end = address + 12
        if not clusters or address >= clusters[-1]["_end"]:
            clusters.append({"_start": address, "_end": end, "addresses": [address]})
        else:
            clusters[-1]["_end"] = max(clusters[-1]["_end"], end)
            clusters[-1]["addresses"].append(address)

    spans = [{"start_address": _hex(c["_start"]),
              "end_exclusive": _hex(c["_end"]),
              "distinct_vector_starts": len(c["addresses"]),
              "candidate_addresses": [_hex(x) for x in c["addresses"]]}
             for c in clusters]

    outcome: dict[str, Any] = {
        "schema_version": 1,
        "source_run_id": str(report.get("run_id", "unknown")),
        "reported_candidate_count": reported,
        "published_vector_rows": len(listed),
        "published_list_incomplete": bool(group.get("candidates_truncated", False)
                                          or reported > len(listed)),
        "unique_start_addresses_in_published_list": len(by_address),
        "duplicate_rows_in_published_list": len(listed) - len(by_address),
        "repeated_start_addresses": sum(len(x) > 1 for x in by_address.values()),
        "overlapping_span_groups_in_published_list": len(spans),
        "potential_unit_vector_start_addresses": sum(
            any(item["unit_vector_endpoints_hint"] for item in copies)
            for copies in by_address.values()),
        "offset_mismatch_addresses": sorted(set(bad_offsets)),
        "aliases": aliases,
        "overlap_groups": spans,
        "ball_position_verified": False,
        "score_verified": False,
        "warning": ("These counts describe only published ranked candidates, not all "
                    "possible game variables. Overlap and unit-norm hints do not "
                    "establish game semantics or physical XYZ coordinates."),
    }
    if baseline is not None:
        if baseline is report:
            raise ValueError("baseline must be a distinct report")
        previous = audit_motion_report(baseline)
        before = {row["candidate_address"] for row in previous["aliases"]}
        after = {row["candidate_address"] for row in aliases}
        outcome["published_subset_comparison"] = {
            "baseline_run_id": previous["source_run_id"],
            "baseline_published_rows": previous["published_vector_rows"],
            "shared_start_addresses": len(before & after),
            "only_in_current_published_subset": len(after - before),
            "only_in_baseline_published_subset": len(before - after),
            "warning": ("Membership comparison of truncated ranked lists only; "
                        "not a count of new physical game variables."),
        }
    return outcome
