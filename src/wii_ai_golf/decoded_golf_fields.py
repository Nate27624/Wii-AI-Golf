"""Source-grounded, read-only US Rev1 Wii Sports golf structure fields.

Offsets are documented in kiwi515/ogws_info; these are raw values, NOT
the Hitting the Green 10-shot index, displayed training score or wind.
"""
from __future__ import annotations

import struct
from typing import Any

SOURCE = "https://github.com/kiwi515/ogws_info"

FIELDS = {
    "golf_config": {
        "golf_mode_raw": 0x94,
        "current_course_hole_raw": 0x98,
    },
    "sports_sequence": {
        "sport_raw": 0x04,
        "sequence_raw": 0x08,
        "training_game_raw": 0x0C,
        "golf_mode_raw": 0xAC,
    },
    "golf_field": {
        "target_object_count_raw": 0x30,
        "pin_object_count_raw": 0x3C,
        "start_object_count_raw": 0x48,
    },
}

ARRAYS = {
    "golf_config": ("standard_player_hole_scores_raw", 0x04, 4, 9),
    "sports_sequence": ("standard_golf_hole_scores_raw", 0x14, 9, 4),
}


def decode_documented_fields(sample: dict[str, Any]) -> dict[str, Any]:
    """Decode only source-documented offsets; never assign training semantics."""
    out: dict[str, Any] = {
        "source": SOURCE, "supported": False, "fields": {},
        "warning": "raw struct fields; NOT decoded training score, ball XYZ or wind",
    }
    if (sample.get("game_id") != "RSPE01" or
        sample.get("disc_revision") != 1 or
        sample.get("mode") != "0x00000004"):
        return out
    out["supported"] = True
    for window_name, offsets in FIELDS.items():
        source = sample.get("windows", {}).get(window_name, {}).get("bytes_hex")
        if not isinstance(source, str):
            continue
        try:
            blob = bytes.fromhex(source)
        except ValueError:
            continue
        for name, offset in offsets.items():
            if offset + 4 <= len(blob):
                out["fields"][window_name + "." + name] = struct.unpack_from(">I", blob, offset)[0]
        array = ARRAYS.get(window_name)
        if array:
            name, offset, rows, cols = array
            n = rows * cols
            if offset + n * 4 <= len(blob):
                values = struct.unpack_from(">" + "I" * n, blob, offset)
                out["fields"][window_name + "." + name] = [
                    list(values[i * cols:(i + 1) * cols]) for i in range(rows)
                ]
    return out


def summarize_documented_transitions(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize consecutive raw field changes for the public candidate report."""
    history: dict[str, list[tuple[int, Any]]] = {}
    for i, sample in enumerate(samples):
        for key, value in sample.get("decoded_fields", {}).get("fields", {}).items():
            history.setdefault(key, []).append((i, value))
    output: dict[str, Any] = {}
    for key, entries in sorted(history.items()):
        changes = sum(a != b for (ia, a), (ib, b) in zip(entries, entries[1:])
                      if ib == ia + 1)
        if isinstance(entries[0][1], list):
            output[key] = {
                "observed_samples": len(entries), "changed_steps": changes,
                "is_raw_standard_golf_score_array": True,
            }
        else:
            unique = list(dict.fromkeys(v for _, v in entries))
            output[key] = {
                "observed_samples": len(entries), "changed_steps": changes,
                "first_raw": entries[0][1], "last_raw": entries[-1][1],
                "distinct_raw_values_first_15": unique[:15],
                "distinct_value_count": len(unique),
            }
    return {
        "fields": output,
        "interpretation": "published US Rev1 field offsets only; training metric semantics unverified",
    }
