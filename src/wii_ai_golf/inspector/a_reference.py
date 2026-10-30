"""Passive, private SHA-verified A-state *candidate* reference from a prior trial.

A genuine game-owned A latch is NOT known. No live/guest writes or label guesses:
only reuse a prior source-identical operator-blinded, heldout-validated run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re

from .a_button import SEQUENCE, LABELS, RECORD_WORDS, WINDOW_SIZE, stable_values, classify

_SHA = re.compile(r"[a-fA-F0-9]{64}\Z")
_WORD = re.compile(r"[a-fA-F0-9]{8}\Z")
_PHASES = SEQUENCE + ("B0", "B1", "B2")
_MAX_CAPTURE = 2_000_000


@dataclass(frozen=True)
class AReference:
    source_digest: str
    model: tuple[tuple[int, int, int], ...]
    trial_sha256: str


def load_reference(folder: Path) -> AReference:
    """Reject malformed/mixed/ambiguous private trial; no file writes/print."""
    folder = Path(folder)
    stream = folder / "candidate-events-PRIVATE.jsonl"
    manifest = folder / "manifest-PRIVATE.json"
    if not folder.is_dir() or folder.is_symlink() or any(p.is_symlink() or not p.is_file() for p in (stream, manifest)):
        raise ValueError("unavailable or symlinked private A-state trial")
    if not 0 < stream.stat().st_size <= _MAX_CAPTURE or not 0 < manifest.stat().st_size <= 65_536:
        raise ValueError("invalid private A-trial size")
    data = stream.read_bytes()
    details = json.loads(manifest.read_text(encoding="utf-8"))
    digest = hashlib.sha256(data).hexdigest()
    if not isinstance(details, dict) or details.get("protocol") != "p0-a-state-blind-v1":
        raise ValueError("wrong A-state protocol")
    if details.get("training_approved") is not False or details.get("status") not in ("ABORTED", "COMPLETE"):
        raise ValueError("unqualified private A-state manifest")
    expected = details.get("stream_sha256")
    if not isinstance(expected, str) or not _SHA.fullmatch(expected) or expected.lower() != digest:
        raise ValueError("SHA-256 verification failed")
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    if (not 30 <= len(rows) <= 60 or type(details.get("candidate_samples")) is not int
            or details["candidate_samples"] != len(rows)):
        raise ValueError("incomplete/private A study sample count")
    grouped: dict[str, list[tuple[int, ...]]] = {}
    owner = None
    prev_end = None
    for event in rows:
        if not isinstance(event, dict) or event.get("kind") != "candidate_sample":
            raise ValueError("unexpected A-study event")
        phase = event.get("phase")
        if phase not in SEQUENCE and not (isinstance(phase, str) and re.fullmatch(r"B[0-7]", phase)):
            raise ValueError("invalid A-trial phase")
        seq = grouped.setdefault(phase, [])
        if type(event.get("sample_index")) is not int or event["sample_index"] != len(seq):
            raise ValueError("A-trial sample indices disagree")
        source = event.get("source_identity_digest_private")
        if not isinstance(source, str) or not _SHA.fullmatch(source):
            raise ValueError("missing source actor identity")
        if owner is None:
            owner = source.lower()
        elif source.lower() != owner:
            raise ValueError("source actor changed within A-trial")
        start, end = event.get("start_monotonic_ns"), event.get("end_monotonic_ns")
        if (type(start) is not int or type(end) is not int or start < 0 or end < start
                or (prev_end is not None and start < prev_end)):
            raise ValueError("nonmonotone A-study host clock")
        prev_end = end
        words = event.get("candidate_words_private_be_u32_hex")
        vector = words.get("selected_player_record_all_51") if isinstance(words, dict) else None
        if (not isinstance(vector, list) or len(vector) != RECORD_WORDS
                or any(not isinstance(w, str) or not _WORD.fullmatch(w) for w in vector)):
            raise ValueError("invalid A-study selected record")
        seq.append(tuple(int(w, 16) for w in vector))
    if tuple(grouped)[:len(SEQUENCE)] != SEQUENCE or not all(len(grouped[p]) == WINDOW_SIZE for p in SEQUENCE):
        raise ValueError("A-trial missing repeated calibration / heldout phases")
    if not all(len(records) == WINDOW_SIZE for records in grouped.values()):
        raise ValueError("unsealed partial blind A windows")
    stable = {p: stable_values(grouped[p]) for p in SEQUENCE}
    model = tuple((i, stable["R0"][i], stable["H0"][i]) for i in range(RECORD_WORDS)
                  if (stable["R0"][i] is not None and stable["H0"][i] is not None
                      and stable["R0"][i] == stable["R1"][i]
                      and stable["H0"][i] == stable["H1"][i]
                      and stable["R0"][i] != stable["H0"][i]))
    if not model:
        raise ValueError("no stable A discriminator")
    for phase in ("R2", "H2", "R3"):
        if any(stable[phase][i] is None for i, _, _ in model):
            raise ValueError("unstable withheld A state")
        vector = tuple(-1 if word is None else word for word in stable[phase])
        if classify(vector, model) != LABELS[phase]:
            raise ValueError("failed withheld A test")
    truths, predictions = details.get("operator_intent_truth"), details.get("predictions")
    if not isinstance(truths, dict) or not isinstance(predictions, dict):
        raise ValueError("missing operator-blind truth receipts")
    blind = [p for p in grouped if p.startswith("B")]
    if (len(blind) < 3 or blind != ["B"+str(i) for i in range(len(blind))]
            or {truths.get(p) for p in blind} != {"PRESSED", "RELEASED"}):
        raise ValueError("insufficient balanced blind A confirmations")
    for phase in blind:
        blind_words = stable_values(grouped[phase])
        pred = classify(tuple(-1 if value is None else value for value in blind_words), model) \
            if all(blind_words[i] is not None for i, _, _ in model) else "UNKNOWN"
        if pred not in ("PRESSED", "RELEASED") or truths.get(phase) != pred or predictions.get(phase) != pred:
            raise ValueError("blind A result not independently confirmed")
    return AReference(owner, model, digest)


def discover_reference(repo_root: Path, *, max_folders: int = 48) -> AReference | None:
    """Only local sibling private Data/captures; never crawl arbitrary directories."""
    root = Path(repo_root).resolve().parent / "Wii-AI-Golf-Data" / "captures"
    if not root.is_dir() or root.is_symlink():
        return None
    folders = sorted(root.glob("p0-a-state-blind-*-PRIVATE"), reverse=True)
    for folder in folders[:max_folders]:
        try:
            return load_reference(folder)
        except (ValueError, OSError, UnicodeError, KeyError, TypeError):
            continue
    return None


@dataclass
class PassiveAIndicator:
    """No A controls, no auto-calibration, no cross-epoch extrapolation."""
    reference: AReference | None
    active_context: tuple[str, tuple[int, ...], tuple[int, ...]] | None = None
    recent: list[str] = field(default_factory=list)
    blocked: bool = False

    def clear(self) -> None:
        self.active_context = None
        self.recent.clear()
        self.blocked = False

    def observe(self, record: tuple[int, ...] | None, source: str | None,
                ball: tuple[int, ...] | None, aim: tuple[int, ...] | None) -> str:
        if self.blocked:
            return "UNKNOWN"
        if (self.reference is None or source != self.reference.source_digest or record is None
                or ball is None or aim is None or not isinstance(ball, tuple) or not isinstance(aim, tuple)):
            self.recent.clear()
            self.blocked = self.active_context is not None
            return "UNKNOWN"
        context = (source, ball, aim)
        if self.active_context is None:
            self.active_context = context
        if self.active_context != context:
            self.recent.clear()
            self.blocked = True
            return "UNKNOWN"
        state = classify(record, self.reference.model)
        if state == "UNKNOWN":
            self.recent.clear()
            return state
        self.recent.append(state)
        self.recent[:] = self.recent[-2:]
        return state if len(self.recent) == 2 and len(set(self.recent)) == 1 else "UNKNOWN"
