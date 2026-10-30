#!/usr/bin/env python3
"""P0 high-information no-A directional aim series (read-only, operator-controlled).

Reuses repo-native source-gated B0/A0 reader. Stores exact candidate bits ONLY
in a local private outside-Git folder; stdout prints sanitized relative metrics.
Neither observed frame.get_count nor human phase labels prove game physics/input.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import p0_live_no_contact_compare as base

PHASES = (
    ("B0", "Idle baseline: no input"),
    ("B1", "Idle repeat: no input, several seconds later"),
    ("L1", "Aim visibly LEFT from baseline, NO A/swing"),
    ("C1", "Recenter to starting aim, NO A/swing"),
    ("R1", "Aim visibly RIGHT from baseline, NO A/swing"),
    ("C2", "Recenter to starting aim again, NO A/swing"),
    ("L2", "Repeat the same LEFT aim, NO A/swing"),
)
EXTRA = ("selected_record_plus_0x30", "selected_record_plus_0x90")
AIM = "aim_candidate_plus_0x3c"


def typed_float(word: int) -> float | None:
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        return None
    v = struct.unpack(">f", word.to_bytes(4, "big"))[0]
    return v if math.isfinite(v) and abs(v) <= 100000.0 else None


def signed_delta(value: float, reference: float) -> float:
    return round(value - reference, 6)


def sanitize(events: list[dict], samples_per_phase: int) -> dict:
    if [e["phase"] for e in events] != [
        p for p, _ in PHASES for _ in range(samples_per_phase)
    ]:
        raise ValueError("missing or nonsequential phase packets")
    if samples_per_phase < 2 or len(events) != len(PHASES) * samples_per_phase:
        raise ValueError("insufficient phase data")
    keys = set(events[0]["words"])
    if AIM not in keys or not set(EXTRA) <= keys:
        raise ValueError("required candidate channels missing")
    for event in events:
        if set(event["words"]) != keys or event["identity"] != events[0]["identity"]:
            raise ValueError("source identity or key mismatch")
        if event["start_ns"] > event["end_ns"]:
            raise ValueError("nonmonotone local time")
    phase_metrics = {}
    values = {}
    for phase, _ in PHASES:
        xs = [e for e in events if e["phase"] == phase]
        aim_words = [e["words"][AIM][0] for e in xs]
        float_values = [typed_float(w) for w in aim_words]
        median = statistics.median(float_values) if all(v is not None for v in float_values) else None
        values[phase] = {"words": aim_words, "median": median}
        phase_metrics[phase] = {
            "sample_count": len(xs),
            "elapsed_monotonic_ms": round((xs[-1]["end_ns"] - xs[0]["start_ns"]) / 1_000_000, 2),
            "aim_unique_word_patterns": len(set(aim_words)),
            "aim_word_transitions_within_phase": sum(a != b for a, b in zip(aim_words, aim_words[1:])),
            "candidate_words_different_from_B0_first": {
                key: sum(a != b for e in xs for a, b in zip(e["words"][key], events[0]["words"][key]))
                for key in sorted(keys)
            },
        }
    ref = values["B0"]["median"]
    for phase, _ in PHASES:
        val = values[phase]["median"]
        phase_metrics[phase]["aim_float32_hypothesis_delta_vs_B0"] = (
            signed_delta(val, ref) if val is not None and ref is not None else None
        )
    def exact_return(phase: str) -> bool:
        return (len(set(values[phase]["words"])) == 1
                and values[phase]["words"][0] == values["B0"]["words"][0])
    left = phase_metrics["L1"]["aim_float32_hypothesis_delta_vs_B0"]
    right = phase_metrics["R1"]["aim_float32_hypothesis_delta_vs_B0"]
    def sign(v):
        return None if v is None else (1 if v > 0 else (-1 if v < 0 else 0))
    return {
        "status": "P0_DIRECTIONAL_SERIES_CANDIDATE_ONLY",
        "protocol_version": 1,
        "phase_order": [p for p, _ in PHASES],
        "samples_per_phase": samples_per_phase,
        "total_sample_packets": len(events),
        "new_candidate_channels": list(EXTRA),
        "phase_metrics": phase_metrics,
        "directional_float32_hypothesis_opposite_signs": (
            sign(left) * sign(right) == -1 if sign(left) is not None and sign(right) is not None else None
        ),
        "left_repeat_exact_word_pattern": (
            len(set(values["L1"]["words"] + values["L2"]["words"])) == 1
        ),
        "recenter_C1_exact_B0_word": exact_return("C1"),
        "recenter_C2_exact_B0_word": exact_return("C2"),
        "no_A_and_visual_direction_human_attested_only": True,
        "source_pointer_identity_stable_within_and_between_packets": True,
        "selected_actor_generation_verified": False,
        "rendered_ball_xyz_verified": False,
        "guest_physics_step_verified": False,
        "accepted_A_or_contact_verified": False,
        "same_shot_outcome_verified": False,
        "training_approved": False,
        "warning": "IEEE754 deltas are candidate decoding hypotheses, NOT a verified angle or units. Host bridge frames NOT guest physics frames.",
    }


def end_epoch_matches(rpc, identity: tuple) -> bool:
    """Recheck source roots/selection after the bounded packet; no RAM write."""
    manager, scene, config, field, pm, selected, record, ball, nested, start, start_vec, pin, pin_vec, hole = identity
    address_expect = (
        (base.SCENE_STATIC, manager),
        (manager + 0xC, scene),
        (base.CONFIG_STATIC, config),
        (base.FIELD_STATIC, field),
        (base.PLAYER_MANAGER_STATIC, pm),
        (pm + 0x334, record),
        (record + 0x88, ball),
        (ball + 0x4C, nested),
        (field + 0x50, start),
        (start + 0x4C, start_vec),
        (field + 0x44, pin),
        (pin + 0x4C, pin_vec),
        (config + 0x98, hole),
        (config + 0x94, 4),
        (manager + 0x18, 5),
    )
    for address, expected in address_expect:
        result = rpc.call("memory.read_u32", [address])
        if type(result) is not int or result != expected:
            return False
    return True


def packet(rpc, phase: str, index: int) -> dict:
    start = time.monotonic_ns()
    snapshot = base.take_snapshot(rpc)
    identity = snapshot["identity"]
    record = identity[6]
    def triple(addr):
        return tuple(rpc.call("memory.read_u32", [addr + i * 4]) for i in range(3))
    new_words = {
        EXTRA[0]: triple(record + 0x30),
        EXTRA[1]: triple(record + 0x90),
    }
    if any(type(v) is not int or not 0 <= v <= 0xFFFFFFFF for v in
           (x for row in new_words.values() for x in row)):
        raise ValueError("invalid live candidate type")
    if not end_epoch_matches(rpc, identity):
        raise ValueError("intra-packet scene/owner/ball/tee/pin identity changed")
    end_frame = rpc.call("frame.get_count", [])
    if type(end_frame) is not int or end_frame < snapshot["frame_bracket"][1]:
        raise ValueError("invalid bridge ordering")
    end = time.monotonic_ns()
    return {
        "phase": phase, "index": index, "start_ns": start, "end_ns": end,
        "frame_bracket": (snapshot["frame_bracket"][0], end_frame),
        "identity": identity,
        "words": {**snapshot["values"], **new_words},
    }


def local_private_path(root: Path) -> Path:
    root = root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("private capture root invalid")
    repo = HERE.parent.resolve()
    if root == repo or repo in root.parents:
        raise ValueError("private captures cannot be inside Git checkout")
    if any(t in str(root).lower() for t in ("onedrive", "dropbox", "google drive")):
        raise ValueError("private captures cannot be in synced folders")
    session = root / ("p0-directional-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10] + "-PRIVATE")
    session.mkdir(mode=0o700)
    return session / "candidate-event-stream-PRIVATE.jsonl"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples-per-phase", type=int, choices=range(2, 13), default=8)
    ap.add_argument("--port", type=int, default=55355)
    ap.add_argument("--private-root", type=Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        print(json.dumps({"status": "SELFTEST_PASS", "phases": [p for p, _ in PHASES], "bridge_contacted": False}))
        return 0
    if args.private_root is None:
        ap.error("--private-root is required")
    try:
        # Create local-only raw output BEFORE any live work, never within the Git checkout.
        target = local_private_path(args.private_root)
        sys.path.insert(0, str(HERE.parent / "src"))
        from wii_ai_golf.integration.rpc import FelkRPC
        run = []
        with target.open("x", encoding="utf-8") as out:
            with FelkRPC(port=args.port, timeout_s=10.0) as rpc:
                expected_identity = None
                for phase, instruction in PHASES:
                    print("NEXT " + phase + ": " + instruction, file=sys.stderr, flush=True)
                    ans = input("Visually confirm phase and NO A/swing. Type YES to sample: ").strip()
                    if ans != "YES":
                        raise ValueError("operator declined phase")
                    for index in range(args.samples_per_phase):
                        e = packet(rpc, phase, index)
                        if expected_identity is None:
                            expected_identity = e["identity"]
                        if e["identity"] != expected_identity:
                            raise ValueError("cross-phase source/shot identity changed")
                        # Exact source-private words stay in this local file; stdout never prints them.
                        record = {
                            "phase": phase, "sample_index": index,
                            "start_monotonic_ns": e["start_ns"],
                            "end_monotonic_ns": e["end_ns"],
                            "bridge_frame_count_bracket_NOT_GUEST_PHYSICS": e["frame_bracket"],
                            "source_identity_digest_private": hashlib.sha256(str(e["identity"]).encode()).hexdigest(),
                            "candidate_words_private_be_u32_hex": {
                                key: [f"{word:08x}" for word in words]
                                for key, words in e["words"].items()
                            },
                            "source_layout_qualified": True,
                            "game_accepted_A_verified": False,
                            "guest_physics_step_verified": False,
                        }
                        out.write(json.dumps(record, sort_keys=True) + "\n")
                        out.flush()
                        run.append(e)
                    print("Captured " + phase + " packets (source checked).", file=sys.stderr, flush=True)
        print(json.dumps(sanitize(run, args.samples_per_phase), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError, EOFError, TypeError):
        print('{"status":"ABSTAIN_LIVE_DIRECTIONAL_SOURCE_OR_OPERATOR_GATE","training_approved":false}')
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
