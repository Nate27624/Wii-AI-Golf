"""Four forward-stroke SPEED-PARAMETER shots, ONE Dolphin, saved-state reloads.

The controlled parameter is Felk's requested speed_m_s for the 20 FORWARD
samples only. This is NOT a verified physical angular-velocity injection.
Runs under the canonical existing first-shot launcher; it NEVER starts Dolphin.
A, movement distance, return speed, club, aim and initial pose are fixed.

Offline:
 py -3 -I scripts/p0_forward_speed_sweep.py --scenario speedtrial01 \
   --bridge-source D:\path\atomic_a45.py --catalog D:\path\savestates.local.json
Live (separate approved canonical wrapper):
 py -3 -I scripts/run_golf_experiment.py --send-live \
   --config SAVED_LAUNCH_JSON --catalog SAVED_CATALOG --bridge PINNED_ATOMIC_BRIDGE \
   --script p0_forward_speed_sweep.py -- --send-live-sweep \
   --scenario speedtrial01 --catalog SAVED_CATALOG \
   --bridge-source PINNED_ATOMIC_BRIDGE
"""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
for entry in (str(ROOT / "scripts"), str(ROOT / "src")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

# Reuse existing controlled input/observation and canonical intro code without
# changing S001/S002/S003 shared modules or writing/modifying any savestate.
from probe_swing import build_probe
from collect_outcome_transition import _build_v1_trace_and_digest, run_session
from p0_pose_power_trial import (
    RefuseTrial, gated_pose_reader, parse_power_observation,
    postshot_notes, setup as pose_setup, eligible as human_power_eligible,
    outcome_eligible as human_landing_eligible, inspect_bridge,
)
from wii_ai_golf.integration.atomic_a45_client import AtomicA45SwingTraceClient
from wii_ai_golf.integration.button_prime import release_buttons
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.savestates import StateCatalog, StateManager
from wii_ai_golf.integration.swing_client import SwingTraceClient
from wii_ai_golf.menu_sequence import planned_menu_phases, execute_menu_phases
from launch_hitting_green import _healthy_connection

DATA = ROOT.parent / "Wii-AI-Golf-Data" / "captures"
# Ordered, bounded study: baseline, large lower requested speed, mid, baseline.
# Output must retain the exact FORWARD-ONLY 20-field change, not mislabel
# prior collect_outcome_transition.speed_scale (also changes backswing).
ARMS = (("F100", 1.0), ("F040", 0.4), ("F070", 0.7), ("F100R", 1.0))
EXPECTED_POSE = "partial-back"
EXPECTED_CLUB = "iron"
EXPECTED_AIM = "straight"
PRE_START_PROFILE = "green-pre-start"


def _digest(samples: list) -> str:
    values = [[s.hold_a, *s.direction, s.distance_m, s.speed_m_s,
               s.return_speed_m_s, s.angle_rad] for s in samples]
    return hashlib.sha256(json.dumps(
        values, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def make_traces() -> list[dict[str, Any]]:
    """Source canonical 89 samples; modify ONLY forward speed per arm."""
    base, source_sha = _build_v1_trace_and_digest(
        motion_scale=1.0, speed_scale=1.0, backswing_scale=1.0)
    if len(base) != 89 or _digest(base) != source_sha:
        raise RefuseTrial("canonical original trace changed")
    if [s.hold_a for s in base] != ([True] * 77 + [False] * 12):
        raise RefuseTrial("canonical A held/released mask changed")
    moving = [i for i, s in enumerate(base) if s.direction == (0.0, 1.0, 0.0)]
    backswing = [i for i, s in enumerate(base) if s.direction == (0.0, -1.0, 0.0)]
    if moving != list(range(27, 47)) or backswing != list(range(12, 27)):
        raise RefuseTrial("canonical swing stage indices changed")
    if any(abs(base[i].speed_m_s - 3.5) > 1e-12 for i in moving):
        raise RefuseTrial("canonical forward request speed changed")

    class FakeRPC:
        def __init__(self):
            self.calls = []
        def call(self, method, args):
            self.calls.append((method, args))
            return {"state": "scheduled", "kind": "swing"}

    rows = []
    for label, scale in ARMS:
        changed = [
            replace(s, speed_m_s=s.speed_m_s * scale) if i in moving else s
            for i, s in enumerate(base)
        ]
        if len(changed) != 89:
            raise RefuseTrial("swing length changed")
        differences = [
            (i, field) for i in range(89) for field, (a, b) in enumerate(
                zip((base[i].hold_a, *base[i].direction,
                     base[i].distance_m, base[i].speed_m_s,
                     base[i].return_speed_m_s, base[i].angle_rad),
                    (changed[i].hold_a, *changed[i].direction,
                     changed[i].distance_m, changed[i].speed_m_s,
                     changed[i].return_speed_m_s, changed[i].angle_rad)))
            if a != b
        ]
        expected_differences = ([] if scale == 1.0
                                else [(i, 5) for i in moving])
        if differences != expected_differences:
            raise RefuseTrial("sweep changes more than forward requested speed")
        fake = FakeRPC()
        SwingTraceClient(fake, port=0).submit(changed)
        if (len(fake.calls) != 1 or fake.calls[0][0] != "trace.submit_swing"
                or fake.calls[0][1][0] != 0
                or len(fake.calls[0][1][1]) != 89
                or any(len(sample) != 8 for sample in fake.calls[0][1][1])):
            raise RefuseTrial("actual repository client serializer mismatch")
        rows.append({
            "arm": label, "requested_forward_speed_scale": scale,
            "requested_forward_speed_m_s": 3.5 * scale,
            "changed_numeric_fields": len(differences),
            "trace_sha256": _digest(changed),
            "samples": changed,
        })
    if not (rows[0]["trace_sha256"] == rows[-1]["trace_sha256"]
            and len({row["trace_sha256"] for row in rows}) == 3):
        raise RefuseTrial("control replication/request hash invariants failed")
    return rows


def preflight_catalog(path: Path):
    if path.is_symlink() or not path.is_file():
        raise RefuseTrial("Savestate catalog unavailable or symlink")
    if path.stat().st_size > 128_000:
        raise RefuseTrial("Savestate catalog oversized")
    catalog = StateCatalog(path)
    profile = catalog.get(PRE_START_PROFILE)
    if profile.name != PRE_START_PROFILE or not 0 <= profile.slot <= 99:
        raise RefuseTrial("Wrong registered start state")
    # A label is not proof of a correct game screen; human checks remain vital.
    return profile


def preflight_source(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RefuseTrial("Atomic bridge source unavailable or symlink")
    # Previously proven atomic A45 V1 with exact source provenance.
    return inspect_bridge(path, atomic=True)


def load_and_replay_intro(*, port: int, profile, reader: Callable[[str], str] = input,
                          connect=FelkRPC, healthy=_healthy_connection,
                          state_manager=StateManager,
                          menu=execute_menu_phases) -> list[dict]:
    """Reload EXISTING pre-start slot inside same Dolphin, then menu intro.

    No state capture/save, no second Dolphin launch. The request acknowledgement
    alone is not proof that the game reached ready-to-swing.
    """
    if reader("Type RELOAD-STATE to reload the existing pre-start state "
              "and replay the menu intro, or q to stop: ").strip() != "RELOAD-STATE":
        raise RefuseTrial("User declined the next savestate reload")
    with connect(port=port, timeout_s=15) as rpc:
        result = state_manager(rpc).request_load(profile)
        if (type(result) is not dict
                or result.get("action") != "load_requested"
                or result.get("slot") != profile.slot):
            raise RefuseTrial("Savestate load acknowledgement mismatch")
    with closing(healthy(port, 60.0)) as rpc:
        AtomicA45SwingTraceClient.require_capability(rpc)
        reports = menu(rpc, planned_menu_phases(), remote=0)
        if (len(reports) != 7 or
                [p["phase"] for p in reports] !=
                [p.label for p in planned_menu_phases()]):
            raise RefuseTrial("Canonical menu intro report is incomplete")
    print("State reload + menu inputs dispatched. READY screen is NOT machine-verified.",
          flush=True)
    return reports


def observe_after_shot(report: dict, *, reader: Callable[[str], str] = input) -> dict:
    power = (None, "unknown")
    for _ in range(3):
        try:
            power = parse_power_observation(reader(
                "Observed gauge (e.g. 101, 65?, >100, blank=unknown): "))
            break
        except RefuseTrial:
            print("Enter a finite numerical human estimate, '?' or blank.", flush=True)
    notes = postshot_notes(reader, report)
    return {"human_power_pct": power[0], "human_power_confidence": power[1], **notes}


def make_row(arm: dict, report: dict, observed: dict, notes: dict,
             *, scenario: str, bridge_sha: str, catalog_slot: int,
             reset_index: int) -> dict:
    """Capture only human data and requested-trace identity, not private RAM."""
    human = report["human_observation"]
    if (human.get("initial_club_pose_human") != "back"
            or observed.get("pose_detail_human") != EXPECTED_POSE
            or observed.get("selected_club_human") != EXPECTED_CLUB
            or observed.get("club_change_human") != "wedge-to-iron"):
        raise RefuseTrial("Pre-shot club/pose mismatch; shot quarantined")
    result = {
        "schema_version": 1,
        "study": "S003-FORWARD-REQUEST-SPEED-SAVESTATE-BATCH-01",
        "utc": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario, "arm": arm["arm"], "shot_index": reset_index + 1,
        "same_dolphin_session_human_procedure": True,
        "savestate_profile": PRE_START_PROFILE, "savestate_slot": catalog_slot,
        "reset_before_shot": reset_index > 0,
        "savestate_load_game_verified": False,
        "ready_screen_game_verified": False,
        "expected_pose": "back", "expected_pose_detail": EXPECTED_POSE,
        "initial_pose_human": human["initial_club_pose_human"],
        "initial_pose_detail_human": observed["pose_detail_human"],
        "expected_club": EXPECTED_CLUB,
        "expected_club_change": "wedge-to-iron",
        "selected_club_human": observed["selected_club_human"],
        "club_change_human": observed["club_change_human"],
        "aim_marker": EXPECTED_AIM, "wind": 0,
        "bridge_sha256": bridge_sha,
        "trace_sha256": arm["trace_sha256"],
        "requested_forward_speed_scale": arm["requested_forward_speed_scale"],
        "requested_forward_speed_m_s": arm["requested_forward_speed_m_s"],
        "changed_numeric_fields": arm["changed_numeric_fields"],
        "forward_samples": 20, "trace_samples": 89, "atomic_a_lead_callback_ticks": 45,
        "contact_human": human.get("contact_human", "unknown"),
        "terminal_seen_human": human.get("terminal_screen_seen_before_transition_human"),
        "visible_result_class_human": human.get("visible_result_class_human"),
        "displayed_distance_human": human.get("displayed_distance_human"),
        "displayed_distance_source": human.get("displayed_distance_source"),
        **notes,
        "power_game_verified": False,
        "club_angular_velocity_game_verified": False,
        "source_launch_vector_verified": False,
        "score_carry_verified": False,
        "training_approved": False,
    }
    result["power_comparison_eligible_human_only"] = human_power_eligible(result)
    result["outcome_eligible_human_only"] = human_landing_eligible(result)
    return result


def append_private(path: Path, row: dict, *, first: bool) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise RefuseTrial("Unsafe private ledger destination")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if first else "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def run_sweep(*, scenario: str, catalog: Path, bridge_source: Path,
              port: int = 55355, reader: Callable[[str], str] = input,
              data_dir: Path = DATA) -> list[dict]:
    if not re.fullmatch(r"[a-z][a-z0-9_-]{3,31}", scenario):
        raise RefuseTrial("scenario must be a new local slug of 4..32 characters")
    if not 1 <= port <= 65535:
        raise RefuseTrial("Invalid bridge port")
    arms = make_traces()
    profile = preflight_catalog(catalog)
    bridge_hash = preflight_source(bridge_source)
    ledger = data_dir / ("forward-speed-" + scenario + ".jsonl")
    if ledger.is_symlink() or ledger.exists():
        raise RefuseTrial("Scenario ledger already exists: use a new scenario, do not overwrite")
    # The outer canonical launcher has already booted the first-ball game.
    # Explicit opt-in to the whole bounded plan does NOT remove per-shot checks.
    if reader("One Dolphin, FOUR shots, 3 reloads; type RUN-FOUR to approve "
              "the sequence, or q to cancel: ").strip() != "RUN-FOUR":
        raise RefuseTrial("Operator did not approve four-shot plan")

    completed: list[dict] = []
    for i, arm in enumerate(arms):
        if i > 0:
            load_and_replay_intro(port=port, profile=profile, reader=reader)
        # Human confirms scene after every state load, club change, and pose.
        plan = pose_setup("B1", "back", scenario, club=EXPECTED_CLUB,
                          aim_id=EXPECTED_AIM, pose_detail=EXPECTED_POSE,
                          club_change="wedge-to-iron")
        observed: dict[str, str] = {}
        print("Trial", i + 1, "of", len(arms), arm["arm"],
              ": requested forward speed", arm["requested_forward_speed_m_s"],
              "m/s. Manually select iron after wedge if necessary.",
              flush=True)
        with FelkRPC(port=port, timeout_s=15) as rpc:
            AtomicA45SwingTraceClient.require_capability(rpc)
            try:
                result = run_session(
                    rpc,
                    raw_path=data_dir / "UNUSED-FORWARD-SPEED-RAW-PRIVATE.jsonl",
                    pre_samples=2, post_samples=2, settled_samples=2,
                    interval=0.0,
                    input_fn=lambda prompt: gated_pose_reader(
                        plan, prompt, reader=reader, observed=observed),
                    # Avoid S002 default waveform: it would also alter the
                    # BACKSWING when speed_scale != 1.0.
                    swing_fn=lambda client: AtomicA45SwingTraceClient(
                        client, port=0).run(arm["samples"]),
                    observe_start_pose=True, visual_first=True, ask_power=False)
            finally:
                release_buttons(rpc, remote=0)

        if result.get("cancelled"):
            raise RefuseTrial("Shot canceled; stopping entire sweep")
        observation = observe_after_shot(result, reader=reader)
        if hashlib.sha256(bridge_source.read_bytes()).hexdigest() != bridge_hash:
            raise RefuseTrial("Source bridge changed during batch; quarantine")
        row = make_row(arm, result, observed, observation,
                       scenario=scenario, bridge_sha=bridge_hash,
                       catalog_slot=profile.slot, reset_index=i)
        append_private(ledger, row, first=(i == 0))
        completed.append(row)
        print(json.dumps({
            "shot": i + 1, "arm": row["arm"],
            "requested_forward_speed_m_s": row["requested_forward_speed_m_s"],
            "contact_human": row["contact_human"],
            "human_power_pct": row["human_power_pct"],
            "human_power_confidence": row["human_power_confidence"],
            "red_shot_human": row["red_shot_human"],
            "curve_human": row["visible_curve_or_rotation_human"],
            "outcome_eligible_human_only": row["outcome_eligible_human_only"],
            "training_approved": False}, indent=2), flush=True)
    return completed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--bridge-source", type=Path)
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--send-live-sweep", action="store_true",
                        help="requires an already-running canonical first-ball Dolphin")
    args = parser.parse_args(argv)
    try:
        plan = make_traces()
        summary = [{k: value for k, value in row.items() if k != "samples"}
                   for row in plan]
        if not args.send_live_sweep:
            print(json.dumps({"status": "DRY_RUN_NO_EMULATOR_INPUT",
                              "variant": "FORWARD_REQUEST_SPEED_ONLY_NOT_ANGULAR_VELOCITY",
                              "shots": summary,
                              "state_reset": PRE_START_PROFILE,
                              "no_savestate_save": True}, indent=2))
            return 0
        if args.catalog is None or args.bridge_source is None:
            raise RefuseTrial("Live requires original --catalog and --bridge-source")
        rows = run_sweep(scenario=args.scenario, catalog=args.catalog,
                         bridge_source=args.bridge_source,
                         port=args.port)
        print("BATCH COMPLETE:", len(rows), "human-observed shots. "
              "All native accepted-power/trajectory/training claims remain FALSE.")
        return 0
    except (RefuseTrial, ValueError, RuntimeError, OSError, KeyError,
            TimeoutError, TypeError) as exc:
        print("ABSTAIN: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
