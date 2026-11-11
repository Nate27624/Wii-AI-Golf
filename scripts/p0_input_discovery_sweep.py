"""Broad-input smoke test: EIGHT consented shots, seven same-Dolphin state reloads.

Not a calibrated power sweep. Isolate presence/duration/direction/magnitude of
motion, preserve the A45 + 89-sample button topology. No game input without
--send-live-sweep AND the canonical wrapper and human approvals.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
for item in (str(ROOT / "scripts"), str(ROOT / "src")):
    if item not in sys.path:
        sys.path.insert(0, item)

from collect_outcome_transition import _build_v1_trace_and_digest, run_session
from p0_pose_power_trial import (
    RefuseTrial, gated_pose_reader, setup as setup_pose,
    eligible as power_eligible, outcome_eligible,
)
from p0_forward_speed_sweep import (
    DATA, EXPECTED_POSE, EXPECTED_CLUB, EXPECTED_AIM, PRE_START_PROFILE,
    _digest, preflight_catalog, preflight_source,
    load_and_replay_intro, observe_after_shot, append_private,
)
from wii_ai_golf.integration.atomic_a45_client import AtomicA45SwingTraceClient
from wii_ai_golf.integration.button_prime import release_buttons
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.swing_client import SwingTraceClient
from wii_ai_golf.integration.a45_neutral_probe_patch import ATOMIC_NEUTRAL_MARKER

# Broad *mechanistic* differences, not arbitrary percentages:
# CTRL/CTRL_R identical; ZERO no request motion; BACK0 removes the backwards
# movement; FWD0 removes the forward movement; PULSE2 keeps two forward
# motion frames; TINY uses very small positive distance/speed in both phases;
# REVFWD reverses forward direction. Every arm keeps 45 A-only callbacks
# and the same 77-held/12-released 89-sample trace. No bridge modification.
VARIANTS = (
    ("CTRL", "original reference"),
    ("ZERO", "all 35 moving samples zero-valued (V1 still sends swing RPC)"),
    ("BACK0", "no 15-sample backswing"),
    ("FWD0", "no 20-sample forward stroke"),
    ("PULSE2", "only first 2 of 20 forward movement samples"),
    ("TINY", "both phases distance 0.02m, speed/return 0.10m/s"),
    ("REVFWD", "20 forward movement directions reversed"),
    ("CTRL_R", "unchanged reference repeated"),
)

def _fields(sample) -> tuple:
    return (sample.hold_a, *sample.direction, sample.distance_m,
            sample.speed_m_s, sample.return_speed_m_s, sample.angle_rad)

def make_variants() -> list[dict[str, Any]]:
    base, canonical_sha = _build_v1_trace_and_digest(
        motion_scale=1.0, speed_scale=1.0, backswing_scale=1.0)
    if len(base) != 89 or _digest(base) != canonical_sha:
        raise RefuseTrial("Original canonical 89-sample trace identity changed")
    if [s.hold_a for s in base] != [True] * 77 + [False] * 12:
        raise RefuseTrial("Original A topology changed")
    if ([(i, s.direction) for i, s in enumerate(base) if any(s.direction)]
            != [(i, (0.0, -1.0, 0.0)) for i in range(12, 27)]
            + [(i, (0.0, 1.0, 0.0)) for i in range(27, 47)]):
        raise RefuseTrial("Canonical active-phase indices changed")

    class FakeRPC:
        def __init__(self):
            self.calls = []
        def call(self, method, args):
            self.calls.append((method, args))
            return {"state": "scheduled", "kind": "swing"}

    out = []
    for name, description in VARIANTS:
        trace = []
        for i, sample in enumerate(base):
            new = sample
            if name == "ZERO" and 12 <= i < 47:
                new = replace(sample, direction=(0., 0., 0.),
                              distance_m=0., speed_m_s=0., return_speed_m_s=0.)
            elif name == "BACK0" and 12 <= i < 27:
                new = replace(sample, direction=(0., 0., 0.),
                              distance_m=0., speed_m_s=0., return_speed_m_s=0.)
            elif name == "FWD0" and 27 <= i < 47:
                new = replace(sample, direction=(0., 0., 0.),
                              distance_m=0., speed_m_s=0., return_speed_m_s=0.)
            elif name == "PULSE2" and 29 <= i < 47:
                new = replace(sample, direction=(0., 0., 0.),
                              distance_m=0., speed_m_s=0., return_speed_m_s=0.)
            elif name == "TINY" and 12 <= i < 47:
                new = replace(sample, distance_m=.02, speed_m_s=.10,
                              return_speed_m_s=.10)
            elif name == "REVFWD" and 27 <= i < 47:
                new = replace(sample, direction=(0., -1., 0.))
            trace.append(new)

        diffs = {(i, j) for i in range(89) for j, (a, b) in enumerate(
            zip(_fields(base[i]), _fields(trace[i]))) if a != b}
        allowed = {
            "CTRL": set(), "CTRL_R": set(),
            "ZERO": {(i, j) for i in range(12, 47) for j in (2, 4, 5, 6)},
            "BACK0": {(i, j) for i in range(12, 27) for j in (2, 4, 5, 6)},
            "FWD0": {(i, j) for i in range(27, 47) for j in (2, 4, 5, 6)},
            "PULSE2": {(i, j) for i in range(29, 47) for j in (2, 4, 5, 6)},
            "TINY": {(i, j) for i in range(12, 47) for j in (4, 5, 6)},
            "REVFWD": {(i, j) for i in range(27, 47) for j in (2,)},
        }[name]
        if diffs != allowed:
            raise RefuseTrial("Requested " + name + " input fields changed unexpectedly")
        if len(trace) != 89 or [t.hold_a for t in trace] != [True]*77 + [False]*12:
            raise RefuseTrial("Trial would change A timing or trace length")
        fake = FakeRPC()
        SwingTraceClient(fake, port=0).submit(trace)
        if (len(fake.calls) != 1 or fake.calls[0][0] != "trace.submit_swing"
                or fake.calls[0][1][0] != 0
                or fake.calls[0][1][1] != [list(_fields(t)) for t in trace]):
            raise RefuseTrial("Real project serialized swing payload mismatch")
        out.append({"arm": name, "requested_intervention": description,
                    "trace_sha256": _digest(trace),
                    "changed_numeric_fields": len(diffs), "samples": trace})
    if (out[0]["trace_sha256"] != canonical_sha
            or out[-1]["trace_sha256"] != canonical_sha
            or len({r["trace_sha256"] for r in out}) != 7):
        raise RefuseTrial("Control repeat / unique variant hash gate failed")
    return out


def require_genuine_neutral_capability(rpc) -> None:
    """Runtime check BEFORE A on the actually loaded neutral-suppressed bridge."""
    try:
        report = rpc.call("trace.a45_neutral_capabilities", [])
    except Exception as exc:
        raise RefuseTrial("Loaded bridge lacks true button-only neutral support") from exc
    if (type(report) is not dict
            or report.get("neutral_protocol") != 1
            or report.get("atomic_a45_protocol") != 1
            or report.get("no_swing_calls_for_zero_samples") is not True
            or report.get("nonzero_swing_calls_preserved") is not True):
        raise RefuseTrial("Loaded bridge neutral A45 capability mismatch")


def ask_motion(reader: Callable[[str], str]) -> str:
    for _ in range(3):
        answer = reader(
            "Could you clearly distinguish a CLUB SWING across the ball "
            "from idle/settling animation? [yes/no/unknown; unknown if unsure]: "
        ).strip().lower()
        if answer in ("yes", "no", "unknown"):
            return answer
        print("Please answer yes, no, or unknown.", flush=True)
    return "unknown"


def record_row(arm: dict, result: dict, observed: dict, annotations: dict,
               *, scenario: str, bridge_sha: str, savestate_slot: int,
               index: int) -> dict:
    human = result["human_observation"]
    if (human.get("initial_club_pose_human") != "back"
            or observed.get("pose_detail_human") != EXPECTED_POSE
            or observed.get("selected_club_human") != EXPECTED_CLUB
            or observed.get("club_change_human") != "wedge-to-iron"):
        raise RefuseTrial("Actual observed pose or club did not match experiment")
    row = {
        "schema_version": 1,
        "study": "S003-BROAD-MOTION-NECESSITY-SWEEP-01",
        "utc": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario, "arm": arm["arm"], "shot_index": index + 1,
        "savestate_profile": PRE_START_PROFILE, "savestate_slot": savestate_slot,
        "reset_before_shot": index > 0,
        "savestate_load_game_verified": False,
        "ready_screen_game_verified": False,
        "requested_intervention": arm["requested_intervention"],
        "changed_numeric_fields": arm["changed_numeric_fields"],
        "trace_sha256": arm["trace_sha256"],
        "bridge_sha256": bridge_sha,
        "atomic_a_lead_callback_ticks": 45, "trace_samples": 89,
        "expected_pose": "back", "expected_pose_detail": EXPECTED_POSE,
        "initial_pose_human": human["initial_club_pose_human"],
        "initial_pose_detail_human": observed["pose_detail_human"],
        "expected_club": EXPECTED_CLUB,
        "selected_club_human": observed["selected_club_human"],
        "expected_club_change": "wedge-to-iron",
        "club_change_human": observed["club_change_human"],
        "aim_marker": EXPECTED_AIM, "wind": 0,
        "contact_human": human.get("contact_human", "unknown"),
        "terminal_seen_human": human.get("terminal_screen_seen_before_transition_human"),
        "visible_result_class_human": human.get("visible_result_class_human"),
        "displayed_distance_human": human.get("displayed_distance_human"),
        "displayed_distance_source": human.get("displayed_distance_source"),
        **annotations,
        "game_consumed_motion_verified": False,
        "native_accepted_power_verified": False,
        "native_angular_velocity_verified": False,
        "native_trajectory_verified": False,
        "training_approved": False,
    }
    row["power_comparison_eligible_human_only"] = power_eligible(row)
    row["outcome_eligible_human_only"] = outcome_eligible(row)
    return row


def run_discovery(*, scenario: str, catalog: Path, bridge_source: Path,
                  port: int = 55355,
                  reader: Callable[[str], str] = input,
                  data_dir: Path = DATA,
                  genuine_neutral: bool = False) -> list[dict]:
    if not re.fullmatch(r"[a-z][a-z0-9_-]{3,31}", scenario):
        raise RefuseTrial("Scenario must be a fresh local slug")
    if not 1 <= port <= 65535:
        raise RefuseTrial("Invalid bridge port")
    variants = make_variants()[:2] if genuine_neutral else make_variants()
    profile = preflight_catalog(catalog)
    bridge_sha = preflight_source(bridge_source)
    if genuine_neutral and ATOMIC_NEUTRAL_MARKER not in bridge_source.read_text(
            encoding="utf-8"):
        raise RefuseTrial("True-neutral study requires separate neutral source")
    ledger = data_dir / (
        ("neutral-button-only-" if genuine_neutral else "input-discovery-")
        + scenario + ".jsonl")
    if ledger.is_symlink() or ledger.exists():
        raise RefuseTrial("Discovery ledger already exists; choose a NEW scenario")
    token = "RUN-TWO" if genuine_neutral else "RUN-EIGHT"
    desc = ("ONE Dolphin, TWO shots, one reload, TRUE button-only ZERO. "
            if genuine_neutral else
            "ONE Dolphin, EIGHT requested swings, seven reloads. ")
    if reader(desc + "Type " + token + " or q: ").strip() != token:
        raise RefuseTrial("Operator declined the study")

    rows = []
    for index, arm in enumerate(variants):
        if index:
            load_and_replay_intro(port=port, profile=profile, reader=reader)
        plan = setup_pose("B1", "back", scenario,
                          club=EXPECTED_CLUB, aim_id=EXPECTED_AIM,
                          pose_detail=EXPECTED_POSE,
                          club_change="wedge-to-iron")
        observed: dict[str, str] = {}
        print(f"Trial {index+1}/{len(variants)}: {arm['arm']} – {arm['requested_intervention']}.",
              flush=True)
        print("Visually verify first ball and manually select iron from wedge "
              "before answering the existing pre-A prompts.", flush=True)
        with FelkRPC(port=port, timeout_s=15) as rpc:
            AtomicA45SwingTraceClient.require_capability(rpc)
            if genuine_neutral:
                require_genuine_neutral_capability(rpc)
            try:
                result = run_session(
                    rpc,
                    raw_path=data_dir / "UNUSED-DISCOVERY-RAM.jsonl",
                    pre_samples=2, post_samples=2, settled_samples=2,
                    interval=0.0,
                    input_fn=lambda prompt: gated_pose_reader(
                        plan, prompt, reader=reader, observed=observed),
                    swing_fn=lambda client: AtomicA45SwingTraceClient(
                        client, port=0).run(arm["samples"]),
                    observe_start_pose=True, visual_first=True,
                    ask_power=False)
            finally:
                release_buttons(rpc, remote=0)
        if result.get("cancelled"):
            raise RefuseTrial("Operator canceled the shot; sweep stopped")
        from p0_forward_speed_sweep import observe_after_shot
        annotations = observe_after_shot(result, reader=reader)
        # Prior user correction: ambiguous movement prompt had been answered
        # yes then explicitly corrected to unknown. For this two-arm causal
        # test do not use an ambiguous animation label at all.
        annotations["club_motion_human"] = (
            "unknown" if genuine_neutral else ask_motion(reader))
        if hashlib.sha256(bridge_source.read_bytes()).hexdigest() != bridge_sha:
            raise RefuseTrial("Bridge source changed during sweep")
        row = record_row(arm, result, observed, annotations,
                         scenario=scenario, bridge_sha=bridge_sha,
                         savestate_slot=profile.slot, index=index)
        append_private(ledger, row, first=(index == 0))
        rows.append(row)
        print(json.dumps({
            "shot": index+1, "arm": row["arm"],
            "contact_human": row["contact_human"],
            "club_motion_human": row["club_motion_human"],
            "power_pct_human": row["human_power_pct"],
            "power_confidence": row["human_power_confidence"],
            "red_human": row["red_shot_human"],
            "training_approved": False,
        }, indent=2), flush=True)
        # A NEGATIVE no-contact result is expected and is retained.
        # But apparent contact with ZERO commanded motion means requested
        # movement is not yet a reliable proxy for the in-game swing event.
        # Stop rather than interpret any later interventions as causal.
        if (not genuine_neutral
                and arm["arm"] == "ZERO"
                and row["contact_human"] == "yes"):
            raise RefuseTrial(
                "ZERO negative control appeared to strike the ball. "
                "Its observation is saved; abort further tests until A/club "
                "game-side input acceptance is diagnosed.")
        # Otherwise continue ONLY with separate human reset approval.
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--bridge-source", type=Path)
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--send-live-sweep", action="store_true",
                        help="ONLY inside canonical launcher on an already running Dolphin")
    parser.add_argument("--true-neutral-control", action="store_true",
                        help="live: ONLY two-shot CTRL/ZERO with runtime-verified "
                             "distinct neutral bridge; original eight-arm mode is disabled")
    args = parser.parse_args(argv)
    try:
        plan = make_variants()
        if not args.send_live_sweep:
            print(json.dumps({
                "status": "DRY_RUN_NO_EMULATOR_INPUT",
                "purpose": "identify input change that first creates reduced/non-red power",
                "not_game_angular_velocity": True,
                "savestate": PRE_START_PROFILE,
                "no_savestate_save": True,
                "shots": [{k: v for k, v in x.items() if k != "samples"} for x in plan]
            }, indent=2))
            return 0
        if args.catalog is None or args.bridge_source is None:
            raise RefuseTrial("Live requires saved catalog and exact isolated atomic bridge")
        if not args.true_neutral_control:
            raise RefuseTrial(
                "Legacy V1 ZERO calls set_wiimote_swing(0...) and is NOT "
                "a no-motion-call control. Do not run the old eight-arm "
                "sweep live; use --true-neutral-control with a NEW isolated "
                "neutral A45 bridge, plus a new scenario.")
        rows = run_discovery(scenario=args.scenario,
                             catalog=args.catalog, bridge_source=args.bridge_source,
                             port=args.port, genuine_neutral=True)
        print("DISCOVERY COMPLETE:", len(rows), "human-observed trials. "
              "Native motion, accepted power, and training remain unverified.")
        return 0
    except (RefuseTrial, ValueError, RuntimeError, OSError, TypeError,
            KeyError, TimeoutError) as exc:
        print("ABSTAIN: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
