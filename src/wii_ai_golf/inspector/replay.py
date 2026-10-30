"""Strict, SHA-gated local JSONL replay for unverified P0 memory candidates.

No Dolphin, guest writes, controller commands, external publication or private
capture fixtures. Raw big-endian u32 bits are retained alongside optional f32.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from typing import Any

HEX = re.compile(r"^(?:0[xX])?([0-9a-fA-F]{8})$")
BALL = "selected_ball_plus_0x30"
CACHE = "selected_ball_cache_plus_0xcc"
AIM = "aim_candidate_plus_0x3c"
NESTED = "selected_nested_plus_0x4c"


class CaptureError(ValueError):
    """A file or field fails an integrity or evidence gate."""


def word_bits(raw: object) -> int:
    """Decode an exactly 32-bit BE word, never a host-endian interpretation."""
    if isinstance(raw, str):
        match = HEX.fullmatch(raw)
        if match is None:
            raise CaptureError("expected exactly eight hexadecimal digits per u32")
        return int(match.group(1), 16)
    if type(raw) is int and 0 <= raw <= 0xFFFFFFFF:
        return raw
    raise CaptureError("invalid u32 word")


def float_hypothesis(word: int) -> float | None:
    value = struct.unpack(">f", word.to_bytes(4, "big"))[0]
    return value if math.isfinite(value) else None


@dataclass(frozen=True)
class Sample:
    ordinal: int
    phase: str
    phase_index: int | None
    start_ns: int | None
    end_ns: int | None
    words: dict[str, tuple[int, ...]]
    source_digest: str | None
    source_qualified: bool
    annotation: str
    state: str
    frame_bracket: tuple[int, int] | None

    def vec(self, field: str) -> tuple[float, float, float] | None:
        bits = self.words.get(field)
        if bits is None or len(bits) != 3:
            return None
        values = tuple(float_hypothesis(bit) for bit in bits)
        return values if all(value is not None for value in values) else None


@dataclass(frozen=True)
class Replay:
    path: Path
    sha256: str
    samples: tuple[Sample, ...]
    warnings: tuple[str, ...]
    terminated: str
    training_approved: bool = False

    def messages(self, sample: Sample) -> tuple[str, ...]:
        notes = ["Unverified source coordinates; units, rendered actor and guest physics time unknown.",
                 "Non-atomic sequential reads: do not calculate physical velocity."]
        if not sample.source_qualified:
            notes.append("Source layout not qualified; values cannot be trusted as selected actor.")
        if sample.start_ns is None or sample.end_ns is None:
            notes.append("Missing host sampling bracket.")
        else:
            notes.append(f"Sample read duration: {(sample.end_ns - sample.start_ns) / 1e6:.1f} ms (host).")
        if sample.source_digest and self.samples[0].source_digest and sample.source_digest != self.samples[0].source_digest:
            notes.append("SOURCE IDENTITY CHANGED: do not join trajectories across epochs.")
        if sample.words.get(BALL) and sample.words.get(NESTED) and sample.words[BALL] != sample.words[NESTED]:
            notes.append("Nested +0x4C aliases ball +0x30 but differs on sequential reads; temporal skew possible.")
        if sample.state != "complete":
            notes.append(f"Segment status: {sample.state.upper()} (not validated contact).")
        return tuple(notes)


def _sha_from_manifest(data: Any, capture_name: str) -> str:
    """Only unambiguous explicit digests; never silently trust any nearby file."""
    found: list[str] = []
    if not isinstance(data, dict):
        raise CaptureError("manifest must be an object")
    for key in ("sha256", "capture_sha256", "jsonl_sha256", "event_stream_sha256", "private_sha256"):
        if key in data:
            found.append(data[key])
    for key in ("files", "artifacts"):
        group = data.get(key)
        entries = group.values() if isinstance(group, dict) else group if isinstance(group, list) else []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", entry.get("filename", entry.get("name")))
            if isinstance(path, str) and Path(path).name == capture_name and "sha256" in entry:
                found.append(entry["sha256"])
    if not found or any(not isinstance(s, str) or re.fullmatch(r"[a-fA-F0-9]{64}", s) is None for s in found):
        raise CaptureError("manifest has no valid explicit SHA-256 for selected capture")
    if len(set(s.lower() for s in found)) != 1:
        raise CaptureError("conflicting manifest SHA-256 values")
    for key in ("capture_file", "filename", "jsonl_file"):
        name = data.get(key)
        if name is not None and (not isinstance(name, str) or Path(name).name != capture_name):
            raise CaptureError("manifest identifies a different capture")
    return found[0].lower()


def _ns(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise CaptureError(f"{label} must be a nonnegative integer")
    return value


def _sample(raw: Any, ordinal: int) -> Sample:
    if not isinstance(raw, dict):
        raise CaptureError("event must be an object")
    phase = raw.get("phase")
    if not isinstance(phase, str) or not phase.strip() or len(phase) > 80:
        raise CaptureError("missing or invalid phase")
    fields = raw.get("candidate_words_private_be_u32_hex", raw.get("words"))
    if not isinstance(fields, dict) or not fields:
        raise CaptureError("missing candidate word fields")
    words: dict[str, tuple[int, ...]] = {}
    for name, values in fields.items():
        if not isinstance(name, str) or not name or len(name) > 120:
            raise CaptureError("invalid field label")
        if not isinstance(values, (tuple, list)) or not 1 <= len(values) <= 64:
            raise CaptureError(f"invalid word vector for {name}")
        words[name] = tuple(word_bits(w) for w in values)
    start = _ns(raw.get("start_monotonic_ns", raw.get("monotonic_start_ns")), "start")
    end = _ns(raw.get("end_monotonic_ns", raw.get("monotonic_end_ns")), "end")
    if start is not None and end is not None and end < start:
        raise CaptureError("nonmonotonic sampling bracket")
    phase_index = raw.get("sample_index")
    if phase_index is not None and (type(phase_index) is not int or phase_index < 0):
        raise CaptureError("invalid sample index")
    digest = raw.get("source_identity_digest_private", raw.get("source_owner_pointer_digest_private"))
    if digest is not None and (not isinstance(digest, str) or not 1 <= len(digest) <= 256):
        raise CaptureError("malformed source identity digest")
    bracket = raw.get("bridge_frame_count_bracket_NOT_GUEST_PHYSICS")
    if bracket is not None:
        if not isinstance(bracket, list) or len(bracket) != 2 or any(type(x) is not int or x < 0 for x in bracket) or bracket[1] < bracket[0]:
            raise CaptureError("invalid non-physics frame bracket")
        bracket = tuple(bracket)
    annotation = raw.get("operator_annotation", raw.get("annotation", ""))
    if not isinstance(annotation, str):
        raise CaptureError("invalid annotation")
    state = raw.get("capture_status", raw.get("segment_status", "complete"))
    if not isinstance(state, str) or state.lower() not in {"complete", "incomplete", "aborted", "quarantined"}:
        raise CaptureError("unknown segment status")
    return Sample(ordinal, phase, phase_index, start, end, words, digest.lower() if digest else None,
                  raw.get("source_layout_qualified") is True, annotation, state.lower(), bracket)


def load_replay(capture: Path | str, manifest: Path | str, *, max_bytes: int = 32_000_000, max_samples: int = 30000) -> Replay:
    """Verify original bytes before interpreting anything. No network or writes."""
    capture, manifest = Path(capture), Path(manifest)
    if capture.resolve() == manifest.resolve():
        raise CaptureError("capture and manifest must be different files")
    try:
        if capture.stat().st_size > max_bytes or manifest.stat().st_size > 1_000_000:
            raise CaptureError("capture exceeds bounded offline viewer size")
        data = capture.read_bytes()
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CaptureError(f"unable to read capture and manifest: {exc}") from exc
    actual = hashlib.sha256(data).hexdigest()
    if actual != _sha_from_manifest(metadata, capture.name):
        raise CaptureError("SHA-256 mismatch: capture modified, wrong manifest or corrupt")
    try:
        stream = data.decode("utf-8")
    except UnicodeError as exc:
        raise CaptureError("JSONL must be UTF-8") from exc
    samples: list[Sample] = []
    warnings: list[str] = []
    annotations: list[str] = []
    protocol = metadata.get("protocol", "")
    terminated = str(metadata.get("status", metadata.get("capture_status", "complete"))).lower()
    if terminated not in {"complete", "incomplete", "aborted", "quarantined"}:
        terminated = "incomplete"
        warnings.append("Unrecognized manifest run status.")
    lines = stream.splitlines()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if len(samples) >= max_samples:
            raise CaptureError("capture exceeds sample limit")
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise CaptureError("event must be an object")
            kind = raw.get("event", "candidate_sample")
            if kind in ("operator_phase_marker", "human_visual_observation"):
                # Annotations are human-supplied and not machine-aligned evidence.
                fragments = [str(raw[k]) for k in ("phase", "label", "description", "observation", "message", "note", "text")
                             if isinstance(raw.get(k), (str, int, float))]
                annotations.append((kind + ": " + " / ".join(fragments))[:300])
                continue
            if kind != "candidate_sample":
                raise CaptureError("unknown event type")
            sample = _sample(raw, len(samples))
            if annotations:
                sample = Sample(sample.ordinal, sample.phase, sample.phase_index,
                                sample.start_ns, sample.end_ns, sample.words, sample.source_digest,
                                sample.source_qualified, " | ".join(annotations) +
                                (" | " + sample.annotation if sample.annotation else ""),
                                sample.state, sample.frame_bracket)
                annotations.clear()
            if protocol == "manual-a-miss-v1" and sample.phase == "M1" and terminated == "aborted":
                sample = Sample(sample.ordinal, sample.phase, sample.phase_index,
                                sample.start_ns, sample.end_ns, sample.words, sample.source_digest,
                                sample.source_qualified, sample.annotation, "quarantined", sample.frame_bracket)
            samples.append(sample)
        except (json.JSONDecodeError, CaptureError) as exc:
            # Only a truncated final JSONL line can be retained as an incomplete run.
            if number == len(lines) and isinstance(exc, json.JSONDecodeError):
                terminated = "incomplete"
                warnings.append(f"Last JSONL line {number} truncated; valid earlier samples retained.")
                break
            raise CaptureError(f"event line {number}: {exc}") from exc
    if not samples:
        raise CaptureError("no complete valid event packets")
    if annotations:
        warnings.append("One or more trailing operator markers have no sampled frame alignment.")
    if protocol == "manual-a-miss-v1":
        expected_phases = [p for p in ("I0", "AH", "AR", "M0", "I1") for _ in range(8)] + ["M1"] * 6
        if (terminated != "aborted" or metadata.get("run_samples") != 46
                or metadata.get("training_approved") is not False
                or [s.phase for s in samples] != expected_phases
                or any(s.phase_index != (i % 8 if i < 40 else i - 40)
                       for i, s in enumerate(samples))):
            raise CaptureError("manual-a-miss-v1 archive manifest/phase gate failed")
        if (any(s.source_digest is None or s.source_digest != samples[0].source_digest for s in samples)
                or any(s.start_ns is None or s.end_ns is None for s in samples)):
            raise CaptureError("manual-a-miss-v1 source-owner/time gate failed")
        warnings.append("Original archive: five 8-packet no-contact controls plus six M1 packets QUARANTINED after human HIT report.")
    if terminated == "complete" and any(s.state != "complete" for s in samples):
        terminated = "incomplete"
    if any(s.source_digest != samples[0].source_digest for s in samples):
        warnings.append("Source identity differs across packets; do not join as one physical trajectory.")
    if any(s.phase == "M1" for s in samples) and terminated != "complete":
        warnings.append("M1 may include operator-observed contact; exact contact frame unverified.")
    if any(s.start_ns is None or s.end_ns is None for s in samples):
        warnings.append("Some packets have no valid host read bracket.")
    return Replay(capture, actual, tuple(samples), tuple(warnings), terminated)
