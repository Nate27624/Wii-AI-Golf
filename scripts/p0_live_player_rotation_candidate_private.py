#!/usr/bin/env python3
"""Read-only selected-player rotation-state probe; world yaw NOT yet verified.

Uses existing RSPE01 Rev1 Golf scene5/mode4/selected-player source gates.
Measures the game-owned record+0x3C scalar and its nearby +0x40..+0x4C
rotation-like matrix directly, with no input integration or aim baseline.
Reports tee->pin bearing as a separately sourced *coordinate hypothesis*.
No game input, A, swing, savestate, guest writes, training, or publication.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import p0_live_no_contact_compare as source
import p0_live_directional_aim_series as epoch

PHASES = (
    ("B0", "Start at a visibly known aim, preferably directly at the flag. A RELEASED."),
    ("IDLE", "Do not change aim or club; wait several seconds."),
    ("LEFT", "Aim visibly LEFT of the original B0 direction, then RELEASE input."),
    ("RIGHT", "Aim visibly RIGHT of the original B0 direction, then RELEASE input."),
    ("RETURN", "Manually return near the original aim; do NOT assume exact recenter."),
)
ANGLE_OFFSET = 0x3C
MATRIX_OFFSET = 0x40
MATRIX_RESIDUAL_MAX = 0.003
DET_RESIDUAL_MAX = 0.006
ANGLE_DISAGREEMENT_DEG_MAX = 0.3


class Abstain(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise Abstain(reason)


def f32(word):
    require(type(word) is int and 0 <= word <= 0xFFFFFFFF, "BAD_U32")
    value = struct.unpack(">f", word.to_bytes(4, "big"))[0]
    require(math.isfinite(value), "NONFINITE_FLOAT")
    return value


def circular_deg(value):
    require(math.isfinite(value), "NONFINITE_ANGLE")
    return (value + 180.0) % 360.0 - 180.0


def difference_deg(a, b):
    return circular_deg(a - b)


def decode_rotation(words):
    """Raw Rev1 numeric relation, not a verified world-coordinate basis.

    Observed source-selected 2x2 = [sin(a),cos(a);-cos(a),sin(a)].
    As an ordinary 2D matrix its rotation angle is a - 90 degrees.
    Matrix world-axis semantics, player model and physical shot heading unknown.
    """
    require(isinstance(words, (tuple, list)) and len(words) == 5,
            "BAD_ROTATION_WORD_COUNT")
    a, m00, m01, m10, m11 = tuple(f32(w) for w in words)
    expected = (math.sin(a), math.cos(a), -math.cos(a), math.sin(a))
    matrix = (m00, m01, m10, m11)
    residual = max(abs(u-v) for u, v in zip(matrix, expected))
    determinant = m00*m11 - m01*m10
    measured_matrix_angle = math.degrees(math.atan2(m10, m00))
    scalar_matrix_angle = circular_deg(math.degrees(a) - 90.0)
    matrix_angle_error = abs(difference_deg(measured_matrix_angle,
                                            scalar_matrix_angle))
    valid = (residual <= MATRIX_RESIDUAL_MAX and
             abs(determinant-1.0) <= DET_RESIDUAL_MAX and
             matrix_angle_error <= ANGLE_DISAGREEMENT_DEG_MAX)
    return {
        "candidate_record_angle_degrees": round(circular_deg(math.degrees(a)), 5),
        "candidate_rotation_matrix_angle_degrees": round(circular_deg(measured_matrix_angle), 5),
        "scalar_minus_90_degrees": round(scalar_matrix_angle, 5),
        "matrix_max_sincos_residual": round(residual, 8),
        "matrix_det_error": round(abs(determinant-1.0), 8),
        "matrix_scalar_angle_error_degrees": round(matrix_angle_error, 6),
        "sincos_matrix_consistent": bool(valid),
        "world_frame_verified": False,
    }


def hypothetical_bearing(tee_words, pin_words):
    """Source-selected tee/pin XZ candidate; NOT independently world-typed."""
    require(len(tee_words) == len(pin_words) == 3, "BAD_LANDMARK_WORD_COUNT")
    tee = tuple(f32(x) for x in tee_words)
    pin = tuple(f32(x) for x in pin_words)
    dx, dz = pin[0]-tee[0], pin[2]-tee[2]
    if not (math.isfinite(dx) and math.isfinite(dz)) or math.hypot(dx,dz) < 0.0001:
        return None
    return round(circular_deg(math.degrees(math.atan2(dz, dx))), 5)


def read_hex_bytes(rpc, addr, size):
    require(source.in_bank(addr, size, "MEM2"), "UNQUALIFIED_PLAYER_RECORD_READ")
    raw = rpc.call("memory.read_bytes", [addr, size])
    require(type(raw) is str and len(raw) == size*2, "BAD_HEX_READ_LENGTH")
    try:
        data = bytes.fromhex(raw)
    except ValueError:
        raise Abstain("BAD_HEX_READ_DATA") from None
    require(len(data) == size, "BAD_HEX_READ_BYTES")
    return struct.unpack(">" + "I"*(size//4), data)


def sample(rpc, expected_identity=None, expected_ball=None):
    """Non-atomic but source-bracketed reading; operator stops moving first."""
    snap = source.take_snapshot(rpc)
    ident = snap["identity"]
    require(expected_identity is None or ident == expected_identity,
            "SCENE_OR_PLAYER_IDENTITY_CHANGED")
    record, ball = ident[6], ident[7]
    require(source.in_bank(record, 0xC0, "MEM2"), "BAD_SELECTED_RECORD")
    before_angle = snap["values"]["aim_candidate_plus_0x3c"][0]
    raw_ball = rpc.call("memory.read_bytes", [ball+0x30, 12])
    require(type(raw_ball) is str and len(raw_ball) == 24,
            "BAD_BALL_READ")
    require(expected_ball is None or raw_ball == expected_ball,
            "BALL_CHANGED_STOP")
    # Contiguous scalar+matrix block; compare against before/after scalar.
    words = read_hex_bytes(rpc, record+ANGLE_OFFSET, 20)
    # Additional previously observed quaternion-like fields are not used to
    # prove yaw; only report their norms for a possible future source trace.
    qwords = read_hex_bytes(rpc, record+0xA0, 32)
    after_angle = rpc.call("memory.read_u32", [record+ANGLE_OFFSET])
    require(type(after_angle) is int and
            before_angle == words[0] == after_angle,
            "ANGLE_CHANGED_INSIDE_NONATOMIC_SAMPLE")
    require(epoch.end_epoch_matches(rpc, ident),
            "SOURCE_EPOCH_CHANGED")
    end_frame = rpc.call("frame.get_count", [])
    require(type(end_frame) is int and end_frame >= snap["frame_bracket"][1],
            "INVALID_FRAME_BRACKET")
    angle = decode_rotation(words)
    quaternions = (
        [f32(w) for w in qwords[0:4]],
        [f32(w) for w in qwords[4:8]],
    )
    norms = [round(math.sqrt(sum(v*v for v in q)), 6) for q in quaternions]
    bearing = hypothetical_bearing(snap["values"]["tee_start_candidate"],
                                    snap["values"]["pin_candidate"])
    return {
        "identity": ident, "ball": raw_ball,
        "source_frame_bracket_NOT_PHYSICS": [snap["frame_bracket"][0], end_frame],
        "record": angle,
        "tee_pin_xz_bearing_candidate_degrees": bearing,
        "quat_like_norms_not_typed": norms,
    }


def assess(rows):
    require([r["phase"] for r in rows] == [k for k, _ in PHASES],
            "MISSING_OR_OUT_OF_ORDER_PHASE")
    angles = [r["record"]["candidate_record_angle_degrees"] for r in rows]
    consistency = all(r["record"]["sincos_matrix_consistent"] for r in rows)
    idle = abs(difference_deg(angles[1], angles[0]))
    left_delta = difference_deg(angles[2], angles[0])
    right_delta = difference_deg(angles[3], angles[0])
    returned = difference_deg(angles[4], angles[0])
    checks = {
        "source_numeric_matrix_consistent_each_phase": consistency,
        "idle_angle_stable_within_0_2deg": idle <= 0.2,
        "left_angle_increased_vs_baseline": left_delta > 0.2,
        "right_angle_decreased_vs_baseline": right_delta < -0.2,
    }
    return {
        "status": ("SOURCE_SELECTED_PLAYER_ROTATION_CANDIDATE_SUPPORTED"
                   if all(checks.values()) else
                   "SOURCE_SELECTED_PLAYER_ROTATION_CANDIDATE_INCONCLUSIVE"),
        "checks": checks,
        "phase_angles_degrees": dict(zip((p for p, _ in PHASES), angles)),
        "left_minus_baseline_degrees": round(left_delta, 5),
        "right_minus_baseline_degrees": round(right_delta, 5),
        "return_minus_baseline_degrees_not_required_exact": round(returned, 5),
        "tee_pin_bearings_candidate_degrees": {
            r["phase"]: r["tee_pin_xz_bearing_candidate_degrees"] for r in rows
        },
        "candidate_read_is_absolute_per_sample_not_integrated": True,
        "game_world_axis_sign_and_heading_verified": False,
        "actual_player_world_yaw_verified": False,
        "quaternion_semantics_verified": False,
        "training_approved": False,
    }


def private_folder(root):
    require(root.is_dir() and not root.is_symlink(), "PRIVATE_ROOT_MISSING_OR_SYMLINK")
    resolved = root.resolve(strict=True)
    repo = ROOT.resolve()
    require(resolved != repo and repo not in resolved.parents,
            "PRIVATE_ROOT_INSIDE_GIT_CHECKOUT")
    require(not any(k in str(resolved).lower() for k in
                    ("onedrive", "dropbox", "google drive")),
            "SYNCED_PRIVATE_ROOT_UNSAFE")
    return resolved / ("p0-player-rotation-" +
                       datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") +
                       "-" + uuid.uuid4().hex[:8] + "-PRIVATE")


def run(port, private_root, rpc_class=None):
    if rpc_class is None:
        from wii_ai_golf.integration.rpc import FelkRPC
        rpc_class = FelkRPC
    folder = private_folder(private_root)
    folder.mkdir(mode=0o700)
    stream = folder / "rotation-observations-PRIVATE.jsonl"
    rows = []
    result = {"status": "ABSTAIN_NOT_STARTED", "training_approved": False}
    print("P0 PLAYER ROTATION: READ-ONLY, NO A/SWING, NO AUTOMATED INPUT.")
    print("All printed angles are source-field/math CANDIDATES, NOT proven world yaw.")
    try:
        with rpc_class(port=port, timeout_s=15.0) as rpc:
            ping = rpc.call("bridge.ping", [])
            require(isinstance(ping, dict) and
                    isinstance(ping.get("bridge_version"), str),
                    "BRIDGE_PING_FAILED")
            require(input("Rev1 Hitting the Green, A RELEASED, ready to hit? Type READY: ").strip().upper()
                    == "READY", "OPERATOR_CANCELLED")
            identity, ball = None, None
            with stream.open("x", encoding="utf-8") as fh:
                for phase, instruction in PHASES:
                    print("\n" + phase + ": " + instruction)
                    require(input("After motion STOPS, type READY (or STOP): ").strip().upper()
                            == "READY", "OPERATOR_CANCELLED")
                    s = sample(rpc, identity, ball)
                    if identity is None:
                        identity, ball = s["identity"], s["ball"]
                    angle = s["record"]
                    event = {
                        "phase": phase,
                        "record": angle,
                        "tee_pin_xz_bearing_candidate_degrees":
                            s["tee_pin_xz_bearing_candidate_degrees"],
                        "quat_like_norms_not_typed": s["quat_like_norms_not_typed"],
                        "source_frame_bracket_NOT_PHYSICS":
                            s["source_frame_bracket_NOT_PHYSICS"],
                    }
                    rows.append(event)
                    fh.write(json.dumps(event, sort_keys=True) + "\n")
                    fh.flush()
                    print("Source-selected record angle:",
                          angle["candidate_record_angle_degrees"], "degrees")
                    print("2D matrix rotation candidate:",
                          angle["candidate_rotation_matrix_angle_degrees"],
                          "degrees; scalar/matrix consistent:",
                          angle["sincos_matrix_consistent"])
                    print("Tee→pin XZ bearing candidate:",
                          event["tee_pin_xz_bearing_candidate_degrees"])
        result = assess(rows)
    except (Abstain, OSError, RuntimeError, ValueError, TypeError,
            KeyError, IndexError, EOFError, TimeoutError) as exc:
        reason = str(exc) if isinstance(exc, Abstain) else type(exc).__name__
        result = {"status": "ABSTAIN_" + reason, "training_approved": False}
    finally:
        digest = sha256(stream.read_bytes()).hexdigest() if stream.exists() else None
        (folder / "manifest-PRIVATE.json").write_text(
            json.dumps({"protocol": "p0-selected-player-rotation-v1",
                        "event_sha256": digest, "event_count": len(rows),
                        "result": result, "training_approved": False},
                       indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == (
        "SOURCE_SELECTED_PLAYER_ROTATION_CANDIDATE_SUPPORTED") else 3


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--private-root", type=Path)
    ap.add_argument("--port", type=int, default=55355)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        a = 0.47
        word = lambda x: int.from_bytes(struct.pack(">f", x), "big")
        r = decode_rotation([word(v) for v in
                             (a, math.sin(a), math.cos(a),
                              -math.cos(a), math.sin(a))])
        require(r["sincos_matrix_consistent"], "OFFLINE_SELFTEST_FAILED")
        print(json.dumps({"status": "SELFTEST_PASS", "rpc_used": False,
                          "training_approved": False}))
        return 0
    if args.private_root is None:
        ap.error("--private-root required for live read")
    return run(args.port, args.private_root)


if __name__ == "__main__":
    raise SystemExit(main())
