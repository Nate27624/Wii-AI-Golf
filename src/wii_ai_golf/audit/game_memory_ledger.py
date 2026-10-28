"""Schema and claim-gates for the evidence-first Wii Golf memory dictionary.

This reads JSON metadata only: never game RAM, DOL, Dolphin, network, or
private captures. A ledger entry is a *claim* requiring corroboration,
not a data source for automatic model training.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

_KIND = "wii-sports-golf-memory-field-evidence-ledger"
_TOP = {
    "schema_version", "kind", "game_id", "target_revision", "status",
    "source_state", "evidence_levels_note", "training_gate", "fields",
}
_FIELD = {
    "field_id", "object_role", "relative_offset", "semantic_hypothesis",
    "identity_level", "behavior_level", "source_typed_member_verified",
    "writer_instruction_verified", "independent_boot_replication_verified",
    "same_shot_frame_join_verified", "gameplay_value_verified",
    "negative_control", "training_eligible", "evidence_refs", "notes",
}
_BOOLEAN = {
    "source_typed_member_verified", "writer_instruction_verified",
    "independent_boot_replication_verified", "same_shot_frame_join_verified",
    "gameplay_value_verified", "negative_control", "training_eligible",
}
_TRAINING = _BOOLEAN - {"negative_control", "training_eligible"}
_IDENTITY = {
    "unlocated", "source_lead", "runtime_candidate",
    "source_and_runtime_confirmed", "writer_traced",
}
_BEHAVIOR = {
    "unobserved", "control_dynamic", "control_stable",
    "action_correlated", "intervention_replicated",
}
_ID = re.compile(r"[a-z][a-z0-9_]*(?:[.][a-z0-9_]+)+\\Z")
_OFFSET = re.compile(r"\\+0x[0-9A-F]{3,4}\\Z")
_PUBLIC_REF = "https://github.com/Nate27624/Wii-AI-Golf/"
_HEX_POINTER = re.compile(r"0x[89][0-9A-Fa-f]{7}\\b")


def validate_memory_ledger(doc: Any) -> list[dict[str, Any]]:
    """Fail closed on overstated training claims and unsafe/ambiguous entries."""
    if type(doc) is not dict or set(doc) != _TOP:
        raise ValueError("Unsupported memory field ledger schema")
    if (type(doc["schema_version"]) is not int or doc["schema_version"] != 1
        or doc["kind"] != _KIND or doc["game_id"] != "RSPE01"
        or type(doc["target_revision"]) is not int or doc["target_revision"] != 1):
        raise ValueError("Unrecognized game/revision or ledger version")
    if any(type(doc[key]) is not str or not doc[key].strip()
           for key in ("status", "source_state", "evidence_levels_note", "training_gate")):
        raise ValueError("Missing evidence-ledger declaration")
    fields = doc["fields"]
    if type(fields) is not list or not 1 <= len(fields) <= 150:
        raise ValueError("Unbounded memory field ledger")
    seen = set()
    for f in fields:
        if type(f) is not dict or set(f) != _FIELD:
            raise ValueError("Unreviewed field-level evidence keys")
        fid = f["field_id"]
        if type(fid) is not str or _ID.fullmatch(fid) is None or fid in seen:
            raise ValueError("Invalid or repeated field identifier")
        seen.add(fid)
        if any(type(f[key]) is not str or not f[key].strip() or len(f[key]) > 700
               for key in ("object_role", "semantic_hypothesis", "notes")):
            raise ValueError("Missing or oversized field hypothesis")
        if _HEX_POINTER.search(f["notes"]) or _HEX_POINTER.search(f["semantic_hypothesis"]):
            raise ValueError("Runtime pointer/address leaked into memory ledger")
        if (type(f["identity_level"]) is not str or f["identity_level"] not in _IDENTITY
            or type(f["behavior_level"]) is not str or f["behavior_level"] not in _BEHAVIOR):
            raise ValueError("Unsupported evidence level")
        offset = f["relative_offset"]
        if offset is not None and (type(offset) is not str or _OFFSET.fullmatch(offset) is None):
            raise ValueError("Only aligned source-relative offsets may be recorded")
        if offset is not None and int(offset[3:], 16) % 4:
            raise ValueError("Memory offset must be 32-bit aligned")
        if any(type(f[key]) is not bool for key in _BOOLEAN):
            raise ValueError("Evidence/verification flags must be booleans")
        refs = f["evidence_refs"]
        if (type(refs) is not list or len(refs) > 12
            or any(type(ref) is not str or not ref.startswith(_PUBLIC_REF)
                   or len(ref) > 300 for ref in refs)):
            raise ValueError("Only known public evidence links are allowed")
        if f["identity_level"] == "unlocated":
            if offset is not None or f["object_role"] != "unknown" or refs:
                raise ValueError("Unlocated field cannot claim offset/ownership/evidence")
            if f["behavior_level"] != "unobserved" or any(f[key] for key in _BOOLEAN):
                raise ValueError("Unlocated field cannot claim observation or training")
        if f["behavior_level"] != "unobserved" and not refs:
            raise ValueError("Observed behavior must have a public evidence reference")
        if f["identity_level"] != "unlocated" and not refs:
            raise ValueError("Runtime or source leads must cite public evidence")
        if f["negative_control"] and (f["behavior_level"] != "control_dynamic"
                                      or f["training_eligible"]):
            raise ValueError("No-shot negative control cannot be a power-training feature")
        if f["training_eligible"]:
            if not all(f[key] for key in _TRAINING):
                raise ValueError("Training promotion lacks writer, boot, same-shot or semantics proof")
            if f["behavior_level"] not in {"action_correlated", "intervention_replicated"}:
                raise ValueError("Training candidate lacks action-response validation")
    return fields


def read_memory_ledger(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 160_000:
        raise ValueError("Missing, linked or oversized evidence-ledger file")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, OSError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed evidence-ledger JSON") from exc
    return validate_memory_ledger(doc)
