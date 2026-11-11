#!/usr/bin/env python3
"""P0 two-label club selector probe; operator D-pad only, read-only Felk RPC.

Built on #412's separately source-derived selector-global hypothesis.
Wedge/Iron -> Wedge -> aim-only -> Iron/Wedge -> two secret heldouts.
No input injection, swing, savestate, source promotion or training.
Only the operator's private directory receives index/aim candidate records.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import p0_live_club_selector_global_private as core

STAGES = (
    ("B0", "WEDGE", "select Wedge; leave A RELEASED"),
    ("IDLE", "WEDGE", "do nothing; keep Wedge"),
    ("IRON1", "IRON", "press D-pad UP once from Wedge; confirm Iron"),
    ("WEDGE1", "WEDGE", "press D-pad DOWN once to Wedge"),
    ("AIM", "WEDGE", "change aim LEFT/RIGHT only; keep Wedge"),
    ("IRON2", "IRON", "select Iron again; no A or swing"),
    ("WEDGE2", "WEDGE", "return to Wedge; no A or swing"),
    ("BLIND1", None, "secretly select Iron OR Wedge"),
    ("BLIND2", None, "secretly select the OTHER club"),
)
LABELS = ("WEDGE", "IRON")


def require(condition, reason):
    if not condition:
        raise core.Abstain(reason)


def prediction(events, index):
    """Use repeated fixed-label calibration only; no operator blind truth."""
    by = {e["phase"]: e for e in events}
    if not all(k in by for k in ("B0", "IDLE", "IRON1", "WEDGE1",
                               "AIM", "IRON2", "WEDGE2")):
        return "UNKNOWN"
    w = [by[k]["index"] for k in ("B0", "IDLE", "WEDGE1", "AIM", "WEDGE2")]
    i = [by[k]["index"] for k in ("IRON1", "IRON2")]
    if len(set(w)) != 1 or len(set(i)) != 1 or w[0] == i[0]:
        return "UNKNOWN"
    if by["AIM"]["aim_candidate_word"] == by["WEDGE1"]["aim_candidate_word"]:
        return "UNKNOWN"
    return "WEDGE" if index == w[0] else "IRON" if index == i[0] else "UNKNOWN"


def assess(events):
    require([e["phase"] for e in events] == [s[0] for s in STAGES],
            "INVALID_OR_INCOMPLETE_PHASE_SEQUENCE")
    require(all(type(e.get("index")) is int and 0 <= e["index"] <= 3
                and type(e.get("aim_candidate_word")) is int
                and 0 <= e["aim_candidate_word"] <= 0xFFFFFFFF
                for e in events), "INVALID_INDEX_OR_AIM_WORD")
    by = {e["phase"]: e for e in events}
    checks = {
        "operator_labeled_phases": all(
            by[p]["club"] == club for p, club, _ in STAGES if club is not None),
        "idle_index_stable": by["IDLE"]["index"] == by["B0"]["index"],
        "wedge_repeated_index": len({by[p]["index"] for p in
                                     ("B0", "IDLE", "WEDGE1", "AIM", "WEDGE2")}) == 1,
        "iron_repeated_index": by["IRON1"]["index"] == by["IRON2"]["index"],
        "two_distinct_indices": by["IRON1"]["index"] != by["B0"]["index"],
        "aim_candidate_changed": (by["AIM"]["aim_candidate_word"]
                                  != by["WEDGE1"]["aim_candidate_word"]),
        "aim_only_index_stable": by["AIM"]["index"] == by["WEDGE1"]["index"],
        "both_blind_truths_present": {by["BLIND1"]["club"],
                                      by["BLIND2"]["club"]} == set(LABELS),
        "blind_predictions_match": all(
            e["prediction"] != "UNKNOWN" and e["prediction"] == e["club"]
            and e["prediction"] == prediction(events[:7], e["index"])
            for e in events[7:]),
    }
    passed = all(checks.values())
    return {
        "status": ("P0_TWO_LABEL_CLUB_SELECTOR_CANDIDATE_SUPPORTED" if passed
                   else "P0_TWO_LABEL_CLUB_SELECTOR_CANDIDATE_NOT_SUPPORTED"),
        "checks": checks,
        "index_by_operator_label": (
            {"WEDGE": by["B0"]["index"], "IRON": by["IRON1"]["index"]}
            if checks["wedge_repeated_index"] and
               checks["iron_repeated_index"] and
               checks["two_distinct_indices"] else {}),
        "source_global_hypothesis_only": True,
        "native_r13_register_verified": False,
        "game_club_id_verified": False,
        "four_club_mapping_verified": False,
        "training_approved": False,
    }


def private_folder(path):
    require(path.exists() and path.is_dir() and not path.is_symlink(),
            "PRIVATE_ROOT_INVALID")
    resolved = path.resolve(strict=True)
    repo = ROOT.resolve()
    require(resolved != repo and repo not in resolved.parents,
            "PRIVATE_ROOT_INSIDE_GIT")
    require(not any(s in str(resolved).lower() for s in
                    ("onedrive", "dropbox", "google drive")),
            "PRIVATE_SYNC_ROOT_UNSAFE")
    return resolved / ("p0-club-pair-" +
                       datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") +
                       "-" + uuid.uuid4().hex[:8] + "-PRIVATE")


def run(port, private_root, rpc_class=None):
    if rpc_class is None:
        from wii_ai_golf.integration.rpc import FelkRPC
        rpc_class = FelkRPC
    folder = private_folder(private_root)
    folder.mkdir(mode=0o700)
    stream = folder / "events-PRIVATE.jsonl"
    events = []
    result = {"status": "ABSTAIN_NOT_STARTED", "training_approved": False}
    print("P0 WEDGE/IRON two-label source selector test; READ-ONLY, NO A/SWING.")
    print("ATTACH to existing Felk Dolphin; manual D-pad only, no automatic inputs.")
    try:
        with rpc_class(port=port, timeout_s=15.0) as rpc:
            ping = rpc.call("bridge.ping", [])
            require(isinstance(ping, dict) and
                    isinstance(ping.get("bridge_version"), str),
                    "BRIDGE_PING_FAILED")
            require(input("Rev1 Hitting the Green, A RELEASED, no ball motion? READY: ").strip().upper()
                    == "READY", "OPERATOR_CANCELLED")
            snapshot = core.source.take_snapshot(rpc)
            identity = snapshot["identity"]
            baseline_ball = rpc.call("memory.read_bytes", [identity[7] + 0x30, 12])
            require(isinstance(baseline_ball, str) and len(baseline_ball) == 24,
                    "BAD_BALL_BASELINE")
            original_owner = core.word(rpc, core.GLOBAL_SLOT)
            with stream.open("x", encoding="utf-8") as fh:
                for phase, expected, action in STAGES:
                    print("\n" + phase + ": " + action)
                    require(input("After performing action, type READY (or STOP): ").strip().upper()
                            == "READY", "OPERATOR_CANCELLED")
                    measured = core.bracketed_index(
                        rpc, identity, baseline_ball,
                        expected_owner=original_owner)
                    # +0x3C is an operator direction-correlated record candidate,
                    # not a proven game-owned aim value. Used ONLY as control.
                    aim_word = core.word(rpc, identity[6] + 0x3C)
                    event = {"phase": phase, "index": measured["index"],
                             "aim_candidate_word": aim_word}
                    if expected is not None:
                        visible = input("Type actually visible club (" + expected +
                                        ") or STOP: ").strip().upper()
                        require(visible == expected, "OPERATOR_VISIBLE_LABEL_MISMATCH")
                        event["club"] = visible
                    else:
                        predicted = prediction(events, event["index"])
                        event["prediction"] = predicted
                        print("BLIND PREDICTION BEFORE LABEL:", predicted)
                        visible = input("NOW reveal visible club (WEDGE/IRON/STOP): ").strip().upper()
                        require(visible in LABELS, "OPERATOR_BLIND_LABEL_INVALID")
                        event["club"] = visible
                    events.append(event)
                    fh.write(json.dumps(event, sort_keys=True) + "\n")
                    fh.flush()
                    print("Source candidate index:", event["index"])
                    if phase == "IDLE":
                        require(events[0]["index"] == event["index"],
                                "IDLE_INDEX_DRIFT")
                    if phase == "IRON1":
                        require(events[0]["index"] != event["index"],
                                "NO_TWO_CLUB_INDEX_CONTRAST_STOP_EARLY")
        result = assess(events)
    except (core.Abstain, KeyError, IndexError, OSError, RuntimeError,
            ValueError, TypeError, EOFError, TimeoutError) as exc:
        reason = str(exc) if isinstance(exc, core.Abstain) else type(exc).__name__
        result = {"status": "ABSTAIN_" + reason, "training_approved": False}
    finally:
        digest = sha256(stream.read_bytes()).hexdigest() if stream.exists() else None
        (folder / "manifest-PRIVATE.json").write_text(
            json.dumps({"protocol": "p0-club-pair-v1",
                        "event_sha256": digest, "event_count": len(events),
                        "result": result, "training_approved": False},
                       indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "P0_TWO_LABEL_CLUB_SELECTOR_CANDIDATE_SUPPORTED" else 3


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=55355)
    ap.add_argument("--private-root", type=Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        require(core.GLOBAL_SLOT == 0x804BF900 and core.FIELD_OFFSET == 0x1C,
                "WRONG_SOURCE_SELECTOR_HYPOTHESIS")
        print(json.dumps({"status": "SELFTEST_PASS", "rpc_used": False,
                          "training_approved": False}))
        return 0
    if args.private_root is None:
        ap.error("--private-root required")
    return run(args.port, args.private_root)


if __name__ == "__main__":
    raise SystemExit(main())
