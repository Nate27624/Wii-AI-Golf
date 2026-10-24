"""Bounded, read-only, US Rev1 golf-state numeric-differential discovery.

NOT a verified ball position, swing event, wind or result decoder.
Raw memory remains local; game RAM is never modified.
"""
from __future__ import annotations

from collections import defaultdict
import math
import struct
from typing import Any

from .symbol_probe import probe_rev1
from .scenario_inference import infer_scene

# Source-identified structs or field-manager-owned effect pointers.
# Config ~7.3 KiB; effect windows 512 bytes each are exploratory.
WINDOWS = {
    "golf_config": (0, 0x1C74),
    "golf_field": (0, 0xA8),
    "sports_sequence": (0, 0xD0),
    "minimap_ball_effect": (0, 0x200),
    "minimap_player_effect": (0, 0x200),
    "minimap_shot_line_effect": (0, 0x200),
}
FIELDS = {
    "minimap_ball_effect": 0x9C,
    "minimap_player_effect": 0x94,
    "minimap_shot_line_effect": 0x98,
}
# Fast omits the large unknown golf-config tail, retaining its mode/header.
# Broad is for lower-frequency counter/score discovery.
FAST_WINDOWS = {**WINDOWS, "golf_config": (0, 0xC0)}
MAX_TOTAL_BYTES = 12 * 1024
CHUNK_BYTES = 1024


def _ram(ptr: int, n: int) -> bool:
    return type(ptr) is int and ptr % 4 == 0 and n > 0 and (
        (0x80000000 <= ptr and ptr + n <= 0x81800000) or
        (0x90000000 <= ptr and ptr + n <= 0x94000000))


def _read(rpc: Any, base: int, length: int) -> str:
    out = []
    for delta in range(0, length, CHUNK_BYTES):
        n = min(CHUNK_BYTES, length - delta)
        value = rpc.call("memory.read_bytes", [base + delta, n])
        if not isinstance(value, str) or len(value) != 2 * n:
            raise ValueError("unexpected memory.read_bytes hex length")
        try:
            bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("invalid memory.read_bytes hex") from exc
        out.append(value)
    return "".join(out)


def snapshot_windows(rpc: Any, *, profile: str = "broad",
                     capture_geometry: bool = False,
                     record_frames: bool = False) -> dict[str, Any]:
    """Capture a small, fixed set of regions to rank hypothetical dynamic XYZ.

    Requires RSPE01 revision 1, game mode 4. Rejects invalid/out-of-range
    pointers before any dereference. No arbitrary user-provided RAM ranges.
    """
    if profile not in ("fast", "broad"):
        raise ValueError("profile must be fast or broad")
    frame_start = rpc.call("frame.get_count", []) if record_frames else None
    if record_frames and (type(frame_start) is not int or frame_start < 0):
        raise ValueError("invalid starting frame count")
    base = probe_rev1(rpc)
    out: dict[str, Any] = {
        "game_id": base["game_id"], "disc_revision": base["disc_revision"],
        "mode": base.get("fields", {}).get("golf_config", {}).get(
            "raw_fields", {}).get("game_mode_raw", {}).get("value_hex"),
        "windows": {}, "read_bytes": 0, "window_errors": {},
        "profile": profile, "scene": None, "frame_start": frame_start,
        "frame_end": None, "frame_span": None,
        "interpretation": "candidate-search-UNVERIFIED-no-ball-or-score-claim",
    }
    if not base["supported"] or out["mode"] != "0x00000004":
        out["warning"] = "unsupported region/revision/mode; no candidate windows read"
        return out
    src = base["fields"]
    if capture_geometry:
        # Read already-probed golf-field object pointers; no duplicate
        # symbol probing. RPC snapshots span multiple emulation frames.
        raw = src["golf_field"].get("raw_fields", {})
        objects = {}
        for field in ("current_pin_obj_ptr", "current_start_obj_ptr", "cup_obj_ptr"):
            ptr_text = raw.get(field, {}).get("value_hex")
            xyz = None
            if isinstance(ptr_text, str):
                try:
                    ptr = int(ptr_text, 16)
                except ValueError:
                    ptr = 0
                if _ram(ptr, 0x48) and _ram(ptr + 0x30, 12):
                    try:
                        vec = struct.unpack(">fff", bytes.fromhex(_read(rpc, ptr + 0x30, 12)))
                        if all(math.isfinite(v) and abs(v) < 1e6 for v in vec):
                            xyz = list(vec)
                    except (ValueError, RuntimeError, OSError, struct.error):
                        pass
            objects[field] = {"translation_xyz_unverified": xyz}
        data = {"game_id": base["game_id"], "disc_revision": base["disc_revision"],
                "mode": "GAMEMODE_TR_NEARPIN", "objects": objects}
        out["scene"] = infer_scene(data)
        out["scene"]["raw_start_xyz"] = objects["current_start_obj_ptr"]["translation_xyz_unverified"]
        out["scene"]["raw_pin_xyz"] = objects["current_pin_obj_ptr"]["translation_xyz_unverified"]
        out["scene"]["raw_cup_xyz"] = objects["cup_obj_ptr"]["translation_xyz_unverified"]
    lookup = {
        "golf_config": src["golf_config"]["instance_pointer"],
        "golf_field": src["golf_field"]["instance_pointer"],
        "sports_sequence": src["sports_sequence"]["instance_pointer"],
    }
    fieldptr = int(src["golf_field"]["instance_pointer"], 16)
    if _ram(fieldptr, 0xA8):
        for name, offset in FIELDS.items():
            ptr = rpc.call("memory.read_u32", [fieldptr + offset])
            lookup[name] = (f"0x{ptr:08X}" if type(ptr) is int
                            and 0 <= ptr <= 0xFFFFFFFF else "0x00000000")
    selected = WINDOWS if profile == "broad" else FAST_WINDOWS
    for name, (start, size) in selected.items():
        ptr = int(lookup.get(name, "0x0"), 16) + start
        if out["read_bytes"] + size > MAX_TOTAL_BYTES:
            out["window_errors"][name] = "bounded memory budget exhausted"
            continue
        if not _ram(ptr, size):
            out["window_errors"][name] = "null_or_invalid_ram_pointer"
            continue
        try:
            value = _read(rpc, ptr, size)
        except (ValueError, RuntimeError, OSError) as exc:
            out["window_errors"][name] = type(exc).__name__
            continue
        out["windows"][name] = {"address": f"0x{ptr:08X}", "bytes_hex": value}
        out["read_bytes"] += size
    if record_frames:
        end = rpc.call("frame.get_count", [])
        if type(end) is not int or end < frame_start:
            raise ValueError("invalid ending frame count")
        out["frame_end"] = end
        out["frame_span"] = end - frame_start
    return out


def analyze_samples(samples: list[dict[str, Any]], *, min_changed: int = 3,
                    top_n: int = 30) -> dict[str, Any]:
    """Rank big-endian f32 VEC3 candidates that change at the same address.

    Deduplicate overlapping windows at absolute addresses. A changing vector may be a UI effect, model transform or unrelated state.
    Static score integers / full ball identity are NOT decoded here.
    """
    if min_changed < 1 or top_n < 1:
        raise ValueError("min_changed and top_n must be positive")
    observations: dict[
        int, list[tuple[int, tuple[float, float, float], tuple[int, int] | None]]
    ] = defaultdict(list)
    scalar_samples: dict[int, list[tuple[int, int, tuple[int, int] | None]]] = defaultdict(list)
    vector_provenance: dict[int, set[str]] = defaultdict(set)
    scalar_provenance: dict[int, set[str]] = defaultdict(set)
    for idx, sample in enumerate(samples):
        seen_vectors: set[int] = set()
        seen_scalars: set[int] = set()
        if sample.get("game_id") != "RSPE01" or sample.get("disc_revision") != 1:
            continue
        scene = sample.get("scene") or {}
        scene_key = None
        if scene.get("scene_status") == "aligned_candidate":
            i, j = scene.get("tee_index_observed"), scene.get("pin_variant_observed")
            if type(i) is int and type(j) is int:
                scene_key = (i, j)
        for name, window in sample.get("windows", {}).items():
            if name not in WINDOWS or not isinstance(window, dict):
                continue
            address, raw = window.get("address"), window.get("bytes_hex")
            if not isinstance(address, str) or not isinstance(raw, str):
                continue
            try:
                blob = bytes.fromhex(raw)
            except ValueError:
                continue
            try:
                base_address = int(address, 16)
            except ValueError:
                continue
            for offset in range(0, len(blob) - 3, 4):
                absolute = base_address + offset
                scalar_provenance[absolute].add(name)
                if absolute in seen_scalars:
                    continue
                seen_scalars.add(absolute)
                u32 = struct.unpack_from(">I", blob, offset)[0]
                if 0 <= u32 <= 100000:
                    scalar_samples[absolute].append((idx, u32, scene_key))
            for offset in range(0, len(blob) - 11, 4):
                absolute = base_address + offset
                vector_provenance[absolute].add(name)
                if absolute in seen_vectors:
                    continue
                seen_vectors.add(absolute)
                xyz = struct.unpack_from(">fff", blob, offset)
                if all(math.isfinite(v) and abs(v) < 100000 for v in xyz):
                    observations[absolute].append((idx, xyz, scene_key))
    ranked = []
    for absolute, entries in observations.items():
        if len(entries) < 3:
            continue
        changes = 0
        displacement = 0.0
        within_scene_steps = 0
        across_scene_steps = 0
        for (i, p, scene_a), (j, q, scene_b) in zip(entries, entries[1:]):
            # Only adjacent successful samples. Don't infer movement across
            # missing data, changing instance addresses, or shot transitions.
            if j != i + 1:
                continue
            moved = math.dist(p, q)
            if moved >= 0.1:
                changes += 1
                displacement += moved
                if scene_a is not None and scene_a == scene_b:
                    within_scene_steps += 1
                elif scene_a != scene_b:
                    across_scene_steps += 1
        if changes < min_changed:
            continue
        ranked.append({
            "source_windows": sorted(vector_provenance[absolute]),
            "candidate_address": f"0x{absolute:08X}",
            "observed_samples": len(entries), "changed_steps": changes,
            "within_same_scene_changed_steps": within_scene_steps,
            "cross_scene_changed_steps": across_scene_steps,
            "total_displacement_game_units_unverified": round(displacement, 4),
            "first_xyz": [round(v, 4) for v in entries[0][1]],
            "last_xyz": [round(v, 4) for v in entries[-1][1]],
            "status": "unverified_numeric_vec3_candidate",
        })
    # Three adjacent unit-sized axes in a 3x3 float matrix are not a
    # moving world position: tag the likely transform region for triage.
    for candidate in ranked:
        address = int(candidate["candidate_address"], 16)
        first = candidate["first_xyz"]
        last = candidate["last_xyz"]
        unitish = all(abs(v) <= 1.05 for v in first + last)
        neighbors = sum((address + d) in observations for d in (-8, -4, 4, 8))
        candidate["likely_orientation_or_normal"] = bool(unitish and neighbors >= 2)
        candidate["status"] = ("likely_orientation_not_ball_xyz" if candidate["likely_orientation_or_normal"]
                               else "unverified_numeric_vec3_candidate")
    ranked.sort(key=lambda x: (x["likely_orientation_or_normal"], (-x["within_same_scene_changed_steps"],
                               -x["changed_steps"],
                               -x["total_displacement_game_units_unverified"],
                               x["candidate_address"]))
    scalar_ranked = []
    for absolute, entries in scalar_samples.items():
        if len(entries) < 3:
            continue
        steps = sum(p != q for (i, p, _sa), (j, q, _sb) in zip(entries, entries[1:])
                    if j == i + 1)
        within = sum(p != q for (i, p, sa), (j, q, sb) in zip(entries, entries[1:])
                     if j == i + 1 and sa is not None and sa == sb)
        if steps < min_changed:
            continue
        scalar_ranked.append({
            "source_windows": sorted(scalar_provenance[absolute]),
            "candidate_address": f"0x{absolute:08X}", "changed_steps": steps,
            "within_same_scene_changed_steps": within,
            "first_u32": entries[0][1], "last_u32": entries[-1][1],
            "status": "unverified_integer_state_candidate_NOT_score",
        })
    scalar_ranked.sort(key=lambda x: (-x["within_same_scene_changed_steps"],
                                       -x["changed_steps"], x["candidate_address"]))
    return {
        "samples": len(samples), "candidate_count": len(ranked),
        "unique_absolute_addresses": True,
        "candidates": ranked[:top_n],
        "candidates_truncated": len(ranked) > top_n,
        "scalar_candidate_count": len(scalar_ranked),
        "scalar_candidates": scalar_ranked[:top_n],
        "scalar_candidates_truncated": len(scalar_ranked) > top_n,
        "warning": "Do not treat candidate as moving golf ball without visual/temporal validation. Within-scene changes improve attribution but no score field identified.",
    }
