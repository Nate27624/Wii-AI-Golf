"""Bounded, read-only Dolphin snapshots and unverified RAM candidate matching.

No RAM symbols or Wii Sports fields are assumed. Changed addresses and numeric
matches must be checked against repeated on-screen observations.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from typing import Any, Protocol

MAX_CAPTURE_BYTES = 65536
CHUNK_BYTES = 2048  # small enough for the RPC client's 64 KiB response cap
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


class Reader(Protocol):
    def call(self, method: str, params: list[Any] | None = None) -> Any: ...


def parse_range(spec: str) -> tuple[int, int]:
    """Accept e.g. 0x80000000:4096 (hex or decimal)."""
    try:
        address_text, length_text = spec.split(":")
        address, length = int(address_text, 0), int(length_text, 0)
    except (ValueError, TypeError) as exc:
        raise ValueError("range must look like 0x80000000:4096") from exc
    if not (0 <= address <= 0xFFFFFFFF and 1 <= length <= MAX_CAPTURE_BYTES
            and address + length - 1 <= 0xFFFFFFFF):
        raise ValueError("range outside 32-bit address space or capture budget")
    return address, length


def _read_memory(reader: Reader, address: int, length: int) -> bytes:
    data = bytearray()
    for offset in range(0, length, CHUNK_BYTES):
        count = min(CHUNK_BYTES, length - offset)
        reply = reader.call("memory.read_bytes", [address + offset, count])
        if not isinstance(reply, str) or len(reply) != count * 2:
            raise ValueError("bridge returned unexpected memory hex length")
        try:
            data.extend(bytes.fromhex(reply))
        except ValueError as exc:
            raise ValueError("bridge returned invalid memory hex") from exc
    return bytes(data)


def capture(reader: Reader, label: str, ranges: list[tuple[int, int]] | None = None,
            *, wiimote_port: int = 0, annotations: dict[str, Any] | None = None,
            screenshot_path: str | Path | None = None) -> dict[str, Any]:
    """Capture one snapshot: never reset, send inputs or write memory."""
    if not LABEL.fullmatch(label):
        raise ValueError("label must be 1..80 ASCII letters/digits/_/-")
    if type(wiimote_port) is not int or wiimote_port not in range(4):
        raise ValueError("wiimote port must be 0..3")
    ranges = ranges or []
    if sum(n for _, n in ranges) > MAX_CAPTURE_BYTES:
        raise ValueError("total capture exceeds 64 KiB budget")
    for address, length in ranges:
        if not (0 <= address <= 0xFFFFFFFF and 1 <= length <= MAX_CAPTURE_BYTES
                and address + length - 1 <= 0xFFFFFFFF):
            raise ValueError("invalid memory range")
    ping = reader.call("bridge.ping", [])
    if not isinstance(ping, dict):
        raise ValueError("bridge ping did not return a mapping")
    start_frame = reader.call("frame.get_count", [])
    if type(start_frame) is not int or start_frame < 0:
        raise ValueError("invalid bridge frame counter")
    controller: dict[str, Any] = {}
    for field, method in (
        ("buttons", "controller.get_wiimote_buttons"),
        ("pointer", "controller.get_wiimote_pointer"),
        ("acceleration_m_s2", "controller.get_wiimote_acceleration"),
        ("angular_velocity_rad_s", "controller.get_wiimote_angular_velocity"),
    ):
        try:
            controller[field] = reader.call(method, [wiimote_port])
        except RuntimeError as exc:
            controller[field] = {"unavailable": str(exc)}
    memory = []
    for address, length in ranges:
        data = _read_memory(reader, address, length)
        memory.append({
            "address": f"0x{address:08X}", "length": length,
            "sha256": hashlib.sha256(data).hexdigest(), "hex": data.hex(),
        })
    end_frame = reader.call("frame.get_count", [])
    if type(end_frame) is not int or end_frame < start_frame:
        raise ValueError("frame counter reversed during capture")
    screenshot = None
    if screenshot_path is not None:
        path = Path(screenshot_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        screenshot = {"path": str(path.resolve()),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return {
        "schema_version": 1,
        "source": "live-bridge-read-only; memory-fields-unidentified",
        "label": label,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "bridge": ping, "frame_start": start_frame, "frame_end": end_frame,
        "multi_frame_non_atomic": end_frame != start_frame,
        "wiimote_port": wiimote_port, "controller": controller, "memory": memory,
        "screenshot": screenshot, "annotations_unverified_human": annotations or {},
    }


def write_snapshot(snapshot: dict[str, Any], path: str | Path) -> Path:
    """Use exclusive creation: experimental evidence must not be overwritten."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def compare(before: dict[str, Any], after: dict[str, Any], *,
            target: float | None = None, tolerance: float = 0.1,
            max_results: int = 40) -> dict[str, Any]:
    """Suggest changed PPC big-endian f32/u32/s32 fields, not decoded scores."""
    if not math.isfinite(tolerance) or tolerance < 0 or max_results < 1:
        raise ValueError("invalid tolerance or result limit")
    if target is not None and not math.isfinite(target):
        raise ValueError("target must be finite")
    a_ranges = {x["address"]: x for x in before.get("memory", [])}
    b_ranges = {x["address"]: x for x in after.get("memory", [])}
    if not a_ranges or a_ranges.keys() != b_ranges.keys():
        raise ValueError("snapshots must have the same nonempty memory ranges")
    changed_runs, matches = [], []
    changed_count = 0
    for start, a in a_ranges.items():
        b = b_ranges[start]
        aa, bb = bytes.fromhex(a["hex"]), bytes.fromhex(b["hex"])
        if len(aa) != len(bb) or len(aa) != a["length"] or len(bb) != b["length"]:
            raise ValueError("snapshot length mismatch")
        address = int(start, 16)
        different = [i for i, (x, y) in enumerate(zip(aa, bb)) if x != y]
        changed_count += len(different)
        for i in different:
            if changed_runs and changed_runs[-1]["address_end"] == address + i - 1:
                changed_runs[-1]["address_end"] = address + i
            else:
                changed_runs.append({"address_start": address + i, "address_end": address + i})
        if target is None:
            continue
        for i in range(0, len(bb) - 3):
            if (address + i) % 4 or aa[i:i+4] == bb[i:i+4]:
                continue
            for kind, fmt in (("f32_be", ">f"), ("u32_be", ">I"), ("s32_be", ">i")):
                old_value = struct.unpack(fmt, aa[i:i+4])[0]
                value = struct.unpack(fmt, bb[i:i+4])[0]
                if math.isfinite(value) and abs(value - target) <= tolerance:
                    matches.append({"address": f"0x{address + i:08X}",
                                    "type": kind, "before": old_value, "after": value,
                                    "error": abs(value - target)})
    matches.sort(key=lambda x: (x["error"], x["address"], x["type"]))
    return {
        "source": "unverified RAM difference; candidate addresses, not decoded game state",
        "before_label": before.get("label"), "after_label": after.get("label"),
        "changed_bytes": changed_count, "changed_runs": [
            {"start": f"0x{x['address_start']:08X}",
             "end": f"0x{x['address_end']:08X}"} for x in changed_runs[:max_results]],
        "runs_truncated": len(changed_runs) > max_results,
        "target_value_unverified": target, "candidate_matches": matches[:max_results],
        "matches_truncated": len(matches) > max_results,
    }
