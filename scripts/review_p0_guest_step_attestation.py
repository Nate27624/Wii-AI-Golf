"""Offline source/clock/receiver provenance gate for a future M2 oracle.

Owned by S002-guest-step-witness-20261121-a, issue #472.
This checks sanitized evidence *claims*; it cannot authenticate actual Wii
guest execution or establish native parity. No emulator, files or network.
"""
from __future__ import annotations

import json
import re
import sys

SCHEMA = "wii-golf-guest-step-attestation-v1"
MAX_EVENTS = 4096
MAX_INPUT_BYTES = 262144
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,63}\Z")
_SOURCE_KEYS = frozenset((
    "source_archive_sha_qualified",
    "source_guest_pc_mapping_qualified",
    "source_selected_receiver_qualified",
    "source_post_step_boundary_qualified",
))
_GUEST_KEYS = frozenset((
    "kind", "host_frame", "guest_step_index", "executed_guest_pc",
    "receiver", "phase", "atomic", "boot", "shot", "ball_epoch",
))
_OTHER_KEYS = frozenset(("kind", "host_frame"))
_TOP_KEYS = frozenset((
    "schema", "trace_kind", "source_revision", "qualifiers",
    "clock_domain", "identity", "events",
))


def _fields(value, allowed, label, required=()):
    if type(value) is not dict or not set(value).issubset(allowed):
        raise ValueError(label + ": non-object or unexpected fields")
    if not set(required).issubset(value):
        raise ValueError(label + ": missing required fields")
    return value


def _id(value, label):
    if (type(value) is not str or not _ID.fullmatch(value)
            or re.search(r"0x[0-9a-f]{6,}", value, flags=re.I)):
        raise ValueError(label + ": expected a short sanitized symbolic ID")
    return value


def _counter(value, label):
    if type(value) is not int or not 0 <= value <= 1000000000:
        raise ValueError(label + ": expected bounded unsigned integer")
    return value


def _answer(status, *, synthetic_count=0, candidate_count=0, first=None, last=None):
    return {
        "schema": SCHEMA,
        "status": status,
        "synthetic_qualified_guest_steps": synthetic_count,
        "sanitized_candidate_guest_steps": candidate_count,
        "first_candidate_guest_index": first,
        "last_candidate_guest_index": last,
        "verified_native_guest_step_count": None,
        "guest_physics_clock_independently_verified": False,
        "native_game_parity_verified": False,
        "training_approved": False,
    }


def evaluate(document):
    """Evaluate bounded, sanitized claims without promoting them to native facts.

    Synthetic PASS means only the fixture satisfied the *asserted* contract.
    A sanitized source-qualified record yields CANDIDATE_REQUIRES_EXTERNAL_PROOF,
    never an attested native count: JSON flags are not independent witnesses.
    Malformed, extra-field or private-looking inputs raise ValueError.
    """
    doc = _fields(document, _TOP_KEYS, "document", _TOP_KEYS)
    if doc["schema"] != SCHEMA:
        raise ValueError("unknown contract schema")
    if doc["trace_kind"] not in ("synthetic", "sanitized"):
        raise ValueError("trace_kind must be synthetic or sanitized")
    qualifiers = _fields(doc["qualifiers"], _SOURCE_KEYS, "qualifiers")
    for value in qualifiers.values():
        if type(value) is not bool:
            raise ValueError("source qualifiers must be strict booleans")
    ident = _fields(doc["identity"], {"boot", "shot", "ball_epoch"},
                    "identity", ("boot", "shot", "ball_epoch"))
    for key, value in ident.items():
        _id(value, key)
    events = doc["events"]
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise ValueError("events must be a bounded list")

    # Validate all event shapes and IDs even if source qualification abstains.
    for event in events:
        if type(event) is not dict or event.get("kind") not in (
                "guest_step", "host_callback", "vi_frame"):
            raise ValueError("unexpected event kind")
        if event["kind"] == "guest_step":
            _fields(event, _GUEST_KEYS, "guest_step", ("kind",))
            for key in ("boot", "shot", "ball_epoch"):
                if key in event:
                    _id(event[key], key)
            for key in ("host_frame", "guest_step_index"):
                if key in event:
                    _counter(event[key], key)
            for key in ("executed_guest_pc", "atomic"):
                if key in event and type(event[key]) is not bool:
                    raise ValueError(key + " must be strict boolean")
            for key in ("receiver", "phase"):
                if key in event:
                    _id(event[key], key)
        else:
            _fields(event, _OTHER_KEYS, "host/VI event",
                    ("kind", "host_frame"))
            _counter(event["host_frame"], "host_frame")

    if doc["source_revision"] != "RSPE01_01":
        return _answer("ABSTAIN_SOURCE_REVISION")
    if doc["clock_domain"] != "qualified_guest_physics_step_counter":
        return _answer("ABSTAIN_HOST_OR_UNKNOWN_CLOCK")
    if not all(qualifiers.get(key) is True for key in _SOURCE_KEYS):
        return _answer("ABSTAIN_SOURCE_PROVENANCE")

    last_guest = None
    last_host = None
    first = None
    count = 0
    for event in events:
        if event["kind"] != "guest_step":
            continue  # Host/VI ticks never become guest physics invocations.
        if event.get("executed_guest_pc") is not True:
            return _answer("ABSTAIN_MISSING_EXECUTED_PC")
        if event.get("receiver") != "selected_ball":
            return _answer("ABSTAIN_WRONG_BALL_RECEIVER")
        if any(event.get(key) != ident[key] for key in ident):
            return _answer("ABSTAIN_SHOT_OR_RECEIVER_EPOCH_MISMATCH")
        if event.get("phase") != "post_golf_step":
            return _answer("ABSTAIN_DISCONTINUOUS_PHASE")
        if event.get("atomic") is not True:
            return _answer("ABSTAIN_NONATOMIC_SAMPLE")
        if "guest_step_index" not in event:
            return _answer("ABSTAIN_MISSING_GUEST_COUNTER")
        if "host_frame" not in event:
            return _answer("ABSTAIN_MISSING_HOST_FRAME")
        step = event["guest_step_index"]
        host = event["host_frame"]
        if last_guest is not None and step != last_guest + 1:
            return _answer("ABSTAIN_DISCONTINUOUS_GUEST_COUNTER")
        # Without independent multi-step-per-host attestation, repeated host
        # frames are ambiguous, not proof of two physics invocations.
        if last_host is not None and host <= last_host:
            return _answer("ABSTAIN_DUPLICATE_OR_NONMONOTONIC_HOST_FRAME")
        first = step if first is None else first
        last_guest, last_host = step, host
        count += 1

    if not count:
        return _answer("ABSTAIN_NO_EXECUTED_GUEST_STEPS")
    if doc["trace_kind"] == "synthetic":
        return _answer("SYNTHETIC_CONTRACT_PASS", synthetic_count=count,
                       first=first, last=last_guest)
    return _answer("CANDIDATE_REQUIRES_EXTERNAL_PROOF", candidate_count=count,
                   first=first, last=last_guest)


def main():
    """Read only a small stdin JSON fixture; never open private source files."""
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        result = _answer("ABSTAIN_INVALID_INPUT")
    else:
        try:
            data = json.loads(
                raw.decode("utf-8"),
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            result = evaluate(data)
        except (UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            result = _answer("ABSTAIN_INVALID_INPUT")
    print(json.dumps(result, sort_keys=True))
    # Exit status is fail-closed for callers that neglect JSON status:
    # 0=synthetic-only validation; 1=no qualified proof; 2=invalid JSON.
    # Even exit 0 is NEVER a verified native Wii physics step.
    if result["status"] == "SYNTHETIC_CONTRACT_PASS":
        return 0
    return 2 if result["status"] == "ABSTAIN_INVALID_INPUT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
