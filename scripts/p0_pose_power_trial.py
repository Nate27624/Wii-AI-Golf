"""One Hitting-the-Green zero-wind, pose-gated swing-power pilot.

Offline: py -3 -I scripts/p0_pose_power_trial.py --arm B1 --pose back --scenario firstball01 --club iron --aim-id straight
Live:   py -3 -I scripts/run_golf_experiment.py --send-live --bridge PATH_TO_PINNED_V1_BRIDGE \
          --script p0_pose_power_trial.py -- --send-live-swing --arm B1 \
          --pose back --scenario firstball01 --club iron --aim-id straight --bridge-source PATH_TO_PINNED_V1_BRIDGE

One live invocation dispatches at most ONE swing via the canonical post-boot collector.
No autonomous trial progression, Dolphin startup, bridge installation, training, or upload.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
for folder in (str(ROOT / "scripts"), str(ROOT / "src")):
    if folder not in sys.path:
        sys.path.insert(0, folder)

ARMS = {"B1": 1.0, "B2": 1.0, "X1": 1.2}
POSES = ("back", "center", "forward")
DATA = ROOT.parent / "Wii-AI-Golf-Data" / "captures"


class RefuseTrial(ValueError):
    """Fail closed without a controller submission."""


def setup(arm: str, pose: str, scenario: str, *, club: str = "unknown", aim_id: str = "unknown") -> dict:
    if arm not in ARMS or pose not in POSES:
        raise RefuseTrial("unknown arm/pose")
    if club not in ("unknown", "driver", "iron", "wedge", "putter"):
        raise RefuseTrial("unknown club")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,31}", aim_id):
        raise RefuseTrial("aim_id must be a local 3..32 character label")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{3,31}", scenario):
        raise RefuseTrial("scenario must be a local 4..32 character slug")
    return {"arm": arm, "expected_pose": pose, "scenario": scenario,
            "backswing_scale": ARMS[arm], "wind": 0, "a_lead": 45,
            "expected_club": club, "aim_marker": aim_id}


def assert_payload_contrast() -> dict:
    """Exercise the REAL project builder and the REAL SwingTraceClient serializer."""
    from collect_outcome_transition import _build_v1_trace_and_digest
    from wii_ai_golf.integration.swing_client import SwingTraceClient

    class FakeRPC:
        def __init__(self):
            self.calls = []
        def call(self, method, args):
            self.calls.append((method, args))
            return {"state": "scheduled", "kind": "swing"}

    payloads = {}
    hashes = {}
    for key, factor in (("baseline", 1.0), ("increased", 1.2)):
        trace, digest = _build_v1_trace_and_digest(
            motion_scale=1.0, speed_scale=1.0, backswing_scale=factor)
        if len(trace) != 89 or [x.hold_a for x in trace] != [True] * 77 + [False] * 12:
            raise RefuseTrial("original A topology or trace length changed")
        rpc = FakeRPC()
        SwingTraceClient(rpc, port=0).submit(trace)
        if len(rpc.calls) != 1 or rpc.calls[0][0] != "trace.submit_swing":
            raise RefuseTrial("unexpected RPC serializer")
        port, payload = rpc.calls[0][1]
        if port != 0 or len(payload) != 89 or any(len(row) != 8 for row in payload):
            raise RefuseTrial("unexpected serialized trace")
        payloads[key], hashes[key] = payload, digest

    original = payloads["baseline"]
    changed = payloads["increased"]
    diffs = [(i, j) for i in range(89) for j in range(8)
             if original[i][j] != changed[i][j]]
    if diffs != [(i, 4) for i in range(12, 27)]:
        raise RefuseTrial("contrast is not limited to 15 backswing-distance fields")
    if any(original[i][4] != 0.25 or changed[i][4] != 0.30 for i in range(12, 27)):
        raise RefuseTrial("unexpected requested backswing distances")
    if hashes["baseline"] == hashes["increased"]:
        raise RefuseTrial("identical control and contrast hashes")
    return {"baseline_trace_sha256": hashes["baseline"],
            "contrast_trace_sha256": hashes["increased"],
            "changed_fields": 15, "samples": 89,
            "test": "actual_project_payload_serializer_pass"}


def pose_gate(expected: str, prompt: str, reader=input) -> str:
    entered = reader(prompt).strip().lower()
    if prompt.startswith("BEFORE pressing A, initial club position"):
        if entered != expected:
            raise RefuseTrial(
                "pre-shot pose mismatch/unknown; no A or swing requested. "
                "Reset and verify the requested initial club position.")
    return entered


def read_rows(path: Path) -> list[dict]:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise RefuseTrial("unsafe ledger target")
    if not path.exists():
        return []
    if not 0 < path.stat().st_size <= 100_000:
        raise RefuseTrial("missing or oversized ledger")
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (UnicodeError, ValueError) as e:
        raise RefuseTrial("invalid ledger JSON") from e
    if any(not isinstance(row, dict) for row in rows):
        raise RefuseTrial("invalid ledger row")
    return rows


def eligible(row: dict) -> bool:
    """Human-only comparability requirement, NOT source-proven accepted power."""
    power = row.get("human_power_pct")
    return (row.get("contact_human") == "yes"
            and row.get("terminal_seen_human") is True
            and type(power) in (float, int) and 0 <= power <= 100
            and row.get("wind") == 0
            and row.get("initial_pose_human") == row.get("expected_pose"))


def precheck(rows: list[dict], plan: dict, bridge_sha: str) -> None:
    arm = plan["arm"]
    order = ("B1", "B2", "X1")
    if len(rows) != order.index(arm):
        raise RefuseTrial("wrong trial order; one B1, then B2, then X1 only")
    for i, row in enumerate(rows):
        if (row.get("arm") != order[i]
                or row.get("scenario") != plan["scenario"]
                or row.get("expected_pose") != plan["expected_pose"]
                or row.get("expected_club") != plan["expected_club"]
                or row.get("aim_marker") != plan["aim_marker"]
                or row.get("bridge_sha256") != bridge_sha
                or not eligible(row)):
            raise RefuseTrial("baseline differs, lacks power/contact, or is unqualified")
    if arm == "X1" and abs(rows[0]["human_power_pct"] - rows[1]["human_power_pct"]) > 5:
        raise RefuseTrial("baselines differ by >5 visual percentage points")


def inspect_bridge(path: Path, *, atomic: bool) -> str:
    from wii_ai_golf.shared.bridge_provenance import inspect_bridge_file
    if path.is_symlink() or not path.is_file():
        raise RefuseTrial("bridge file not a regular file")
    description = inspect_bridge_file(path)
    expected = "V1-atomic-a45" if atomic else "V1-neutral-swing-calls"
    if description.get("revision") != expected:
        raise RefuseTrial("bridge revision mismatch")
    if not atomic and description.get("safe_for_isolated_legacy_copy") is not True:
        raise RefuseTrial("unqualified legacy V1 bridge")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(result: dict, plan: dict, *, bridge_sha: str, payload: dict) -> dict:
    human = result["human_observation"]
    requested = result["known_good_swing_request"]
    expected_hash = (payload["contrast_trace_sha256"] if plan["arm"] == "X1"
                     else payload["baseline_trace_sha256"])
    if (requested["trace_sha256"] != expected_hash or requested["generated_trace_frames"] != 89
            or requested["backswing_scale"] != plan["backswing_scale"]
            or requested["a_lead_requested_frames"] != 45
            or human["initial_club_pose_human"] != plan["expected_pose"]):
        raise RefuseTrial("collector trace identity, A lead or initial pose changed")
    return {"schema_version": 1, "source": "human-only-zero-wind-pose-pilot",
            "utc": datetime.now(timezone.utc).isoformat(), **plan,
            "initial_pose_human": human["initial_club_pose_human"],
            "initial_pose_game_verified": False,
            "bridge_sha256": bridge_sha,
            "trace_sha256": requested["trace_sha256"],
            "contact_human": human.get("contact_human"),
            "terminal_seen_human": human.get("terminal_screen_seen_before_transition_human"),
            "human_power_pct": human.get("displayed_power_percent_human"),
            "power_game_verified": False,
            "green_human": human.get("finished_on_green_human"),
            "displayed_distance_source": human.get("displayed_distance_source"),
            "score_carry_verified": False,
            "training_approved": False}


def run_live(plan: dict, *, port: int, bridge_source: Path, atomic: bool,
             data_dir: Path = DATA, reader=input) -> dict:
    if not atomic:
        raise RefuseTrial(
            "Host-polled A45 can skip emulated frames (observed Win trial). "
            "This pilot requires the isolated atomic A45 V1 bridge and --atomic-a45; "
            "restart from a fresh first-ball state. No controller input sent.")
    if not 1 <= port <= 65535:
        raise RefuseTrial("invalid bridge port")
    hashes = assert_payload_contrast()
    if bridge_source.is_symlink():
        raise RefuseTrial("bridge source is a symlink")
    bridge_source = bridge_source.resolve(strict=True)
    bridge_sha = inspect_bridge(bridge_source, atomic=atomic)
    ledger = data_dir / ("pose-power-" + plan["scenario"] + ".jsonl")
    rows = read_rows(ledger)
    precheck(rows, plan, bridge_sha)
    print("SOURCE-SAFE PRECHECK PASSED; ONE shot maximum; no automatic next trial.")
    print("Verify first-ball Hitting the Green, zero wind, pin, aim and initial pose.")
    print("Expected club:", plan["expected_club"], "| aim reference:", plan["aim_marker"])

    from collect_outcome_transition import run_session
    from wii_ai_golf.integration.rpc import FelkRPC
    from wii_ai_golf.integration.atomic_a45_client import AtomicA45SwingTraceClient
    with FelkRPC(port=port, timeout_s=15) as rpc:
        # Verify the actually LOADED bridge responds to atomic capability
        # BEFORE prompting the operator or requesting any controller input.
        AtomicA45SwingTraceClient.require_capability(rpc)
        result = run_session(
            rpc, raw_path=data_dir / "UNUSED-POSE-PILOT-RAW-PRIVATE.jsonl",
            pre_samples=2, post_samples=2, settled_samples=2,
            interval=0.0, input_fn=lambda prompt: pose_gate(plan["expected_pose"], prompt, reader),
            a_prime_requests=0, a_lead_frames=45, atomic_a45=atomic,
            observe_start_pose=True, motion_scale=1.0,
            speed_scale=1.0, backswing_scale=plan["backswing_scale"],
            ask_power=True, visual_first=True)
    if result.get("cancelled"):
        raise RefuseTrial("operator cancelled; no usable trial recorded")
    if hashlib.sha256(bridge_source.read_bytes()).hexdigest() != bridge_sha:
        raise RefuseTrial("bridge changed during shot; quarantined")
    record = summarize(result, plan, bridge_sha=bridge_sha, payload=hashes)
    record["calibration_eligible_human_only"] = eligible(record)
    data_dir.mkdir(parents=True, exist_ok=True)
    if ledger.is_symlink():
        raise RefuseTrial("unsafe ledger target")
    with ledger.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=tuple(ARMS), required=True)
    parser.add_argument("--pose", choices=POSES, required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--club", choices=("unknown", "driver", "iron", "wedge", "putter"), required=True)
    parser.add_argument("--aim-id", required=True, help="fixed human aim reference label; not source-verified")
    parser.add_argument("--send-live-swing", action="store_true", help="one real swing, only via canonical post-boot runner")
    parser.add_argument("--bridge-source", type=Path, help="must be the exact source supplied to outer --bridge")
    parser.add_argument("--atomic-a45", action="store_true", help="REQUIRED for live trial: isolated atomic V1 bridge; host-polled A45 is refused")
    parser.add_argument("--port", type=int, default=55355)
    args = parser.parse_args(argv)
    try:
        plan = setup(args.arm, args.pose, args.scenario, club=args.club, aim_id=args.aim_id)
        if not args.send_live_swing:
            print(json.dumps({"plan": plan, "payload_verification": assert_payload_contrast(),
                              "status": "DRY_RUN_NO_GAME_INPUT"}, indent=2))
            return 0
        if args.bridge_source is None:
            raise RefuseTrial("live requires --bridge-source matching the outer launcher")
        result = run_live(plan, port=args.port, bridge_source=args.bridge_source,
                          atomic=args.atomic_a45)
        print(json.dumps({"arm": result["arm"], "contact_human": result["contact_human"],
                          "human_power_pct": result["human_power_pct"],
                          "starting_pose": result["initial_pose_human"],
                          "source": result["source"],
                          "calibration_eligible_human_only": result["calibration_eligible_human_only"],
                          "training_approved": False}, indent=2))
        return 0 if result["calibration_eligible_human_only"] else 2
    except (RefuseTrial, RuntimeError, OSError, ValueError, KeyError) as err:
        print("ABSTAIN: " + str(err), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
