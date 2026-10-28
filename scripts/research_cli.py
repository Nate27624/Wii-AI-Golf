"""Single command-line entrypoint for Wii Sports golf research.

Commands:
    py scripts/research_cli.py test
    py scripts/research_cli.py v1 --a-lead 0
    py scripts/research_cli.py sync

Safe sequence: clean main fast-forward -> local experiment -> sanitized
result commit/push to the dedicated research/observations branch. Never
uploads ROMs, savestates, generated bridge code, RAW JSONL or RAM captures.
No Dolphin for offline tests. Live always requires --live.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.lab.github_sync import sync_merged_main

DATA = ROOT.parent / "Wii-AI-Golf-Data"
OBS_BRANCH = "research/observations"
REPO_URL = "https://github.com/Nate27624/Wii-AI-Golf.git"
CAPTURES = DATA / "captures"
SAFE_LABELS = ("contact_human", "initial_club_pose_human",
               "finished_on_green_human", "displayed_distance_human",
               "displayed_unit_human", "shot_start_frame_before_controller_trace",
               "displayed_power_percent_human")
SAFE_TRACE = ("trace_sha256", "generated_trace_frames",
              "a_lead_requested_frames", "a_lead_observed_frame_delta",
              "motion_scale", "speed_scale", "backswing_scale")
_ALLOWED = {"test", "v1"}


def _run(argv: list[str], *, cwd: Path = ROOT) -> int:
    return subprocess.run(argv, cwd=cwd, check=False).returncode


def _head() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                           text=True, capture_output=True, check=True, timeout=6)
        return r.stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unavailable"


def _sha_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def v1_clean_boot_args(root: Path) -> list[str]:
    """Fail closed if the only vetted portable Dolphin launch is unavailable.

    This is an offline file-presence check. No Dolphin process, controller,
    savestate, network request or local configuration write is performed.
    The outer canonical runner retains sole control of fresh boot/intro.
    """
    clean = root.parent / "tools" / "FelkDolphin-Clean"
    executable = clean / "Dolphin.exe"
    user = clean / "User"
    config = root / "research" / "launch.local.json"
    catalog = root / "research" / "savestates.local.json"
    missing = []
    for label, present in (
        ("isolated clean Dolphin executable", executable.is_file()),
        ("portable.txt user-root selector", (clean / "portable.txt").is_file()),
        ("isolated clean Dolphin User directory", user.is_dir()),
        ("local launcher configuration", config.is_file()),
        ("local named-savestate catalog", catalog.is_file()),
    ):
        if not present:
            missing.append(label)
    if missing:
        raise RuntimeError(
            "P0 V1 safe launch blocked: missing " + ", ".join(missing) +
            ". Do not fall back to the old FelkDolphin installation; "
            "restore the clean portable setup and named checkpoint first."
        )
    return ["--dolphin", str(executable), "--dolphin-user", str(user),
            "--config", str(config), "--catalog", str(catalog)]



def _fresh_human_labels(start_time: datetime) -> dict:
    """Read ONLY selected public/sanitized fields from a NEW locally generated summary."""
    if not CAPTURES.is_dir():
        return {}
    options = [p for p in CAPTURES.glob("outcome-*-candidates.json")
               if p.is_file() and p.stat().st_mtime >= start_time.timestamp()]
    if len(options) != 1:
        return {"capture_status": "none_or_ambiguous"}
    path = options[0]
    try:
        if path.stat().st_size > 2_000_000:
            return {"capture_status": "summary_too_large"}
        content = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(content, dict) or not str(content.get("source", "")).startswith("live-emulator-"):
            return {"capture_status": "unexpected_summary_source"}
        human = content.get("human_observation") or {}
        swing = content.get("known_good_swing_request") or {}
        if not isinstance(human, dict) or not isinstance(swing, dict):
            return {"capture_status": "unexpected_summary_shape"}
        result = {"capture_status": "sanitized_human_annotation_only"}
        result["human"] = {k: human[k] for k in SAFE_LABELS if k in human
                           and (human[k] is None or type(human[k]) in (str, int, float, bool))}
        result["controller"] = {k: swing[k] for k in SAFE_TRACE if k in swing
                                and (swing[k] is None or type(swing[k]) in (str, int, float, bool))}
        observed = content.get("settled_screen_observation")
        # Never transmit arbitrary nested private collector content.
        result["settled_screen_observation"] = observed if type(observed) is str and observed in {
            "operator_confirmed_before_transition",
            "screen_had_already_transitioned_before_settled_samples",
            "already transitioned",
            "human_terminal_before_transition",
            "human_terminal_unseen_or_unknown",
        } else "unknown"
        return result
    except (OSError, ValueError, UnicodeError):
        return {"capture_status": "unreadable_summary"}



def _joined_visual_first(run_token: str, start: datetime, *,
                         a_lead: int, speed: float, backswing: float) -> dict:
    """Read ONE exactly named child artifact; never infer identity via file mtime.

    All values are unverified human annotations/command metadata. No RAM or
    private file path is returned. Invalid/incomplete records fail closed.
    """
    invalid = {"capture_status": "visual_first_join_refused",
               "shot_dispatch_verified_by_collector": False}
    path = CAPTURES / ("outcome-" + run_token + "-candidates.json")
    try:
        if (not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{10}", run_token)
                or path.is_symlink() or not path.is_file()
                or not 0 < path.stat().st_size <= 2_000_000
                or path.stat().st_mtime < start.timestamp()):
            return invalid
        item = json.loads(path.read_text(encoding="utf-8"))
        if type(item) is not dict or item.get("run_token") != run_token:
            return invalid
        if (item.get("source") != "human-terminal-result-no-ram-game-context-unverified"
                or item.get("outcome_collection_mode") != "human_terminal_first_no_ram"
                or item.get("raw_data_created") is not False
                or item.get("candidate_ranking") is not None):
            return invalid
        dispatch = item.get("swing_dispatch")
        swing = item.get("known_good_swing_request")
        human = item.get("human_observation")
        if not all(type(v) is dict for v in (dispatch, swing, human)):
            return invalid
        if (dispatch.get("state") != "complete"
                or type(swing.get("generated_trace_frames")) is not int
                or swing["generated_trace_frames"] != 89
                or type(dispatch.get("applied_frames")) is not int
                or dispatch["applied_frames"] != swing["generated_trace_frames"]
                or swing.get("preset") != "forward"
                or swing.get("motion_scale") != 1.0
                or swing.get("speed_scale") != speed
                or swing.get("backswing_scale") != backswing
                or swing.get("a_lead_requested_frames") != a_lead
                or type(swing.get("a_lead_observed_frame_delta")) is not int
                or swing["a_lead_observed_frame_delta"] < a_lead):
            return invalid
        digest = swing.get("trace_sha256")
        if type(digest) is not str or re.fullmatch(r"[a-f0-9]{64}", digest) is None:
            return invalid
        # An arbitrary 64-character digest does NOT bind an action to the
        # expected waveform. Rebuild the SAME pure requested trace used by
        # the child, then verify equality before accepting this result.
        from collect_outcome_transition import _build_v1_trace_and_digest
        expected_samples, expected_digest = _build_v1_trace_and_digest(
            motion_scale=1.0, speed_scale=speed, backswing_scale=backswing)
        if len(expected_samples) != 89 or digest != expected_digest:
            return invalid
        contact, green = human.get("contact_human"), human.get("finished_on_green_human")
        seen = human.get("terminal_screen_seen_before_transition_human")
        kind = human.get("visible_result_class_human")
        source = human.get("displayed_distance_source")
        value = human.get("displayed_distance_human")
        unit = human.get("displayed_unit_human")
        pose = human.get("initial_club_pose_human")
        power = human.get("displayed_power_percent_human")
        shot_start = human.get("shot_start_frame_before_controller_trace")
        if (type(pose) is not str or pose not in ("back", "center", "forward", "unknown")
                or type(shot_start) is not int or shot_start < 0
                or (power is not None and (type(power) not in (int, float)
                    or not math.isfinite(power) or not 0 <= power <= 100))
                or human.get("initial_club_pose_verified_by_memory") is not False
                or human.get("displayed_power_verified_by_memory") is not False
                or human.get("hitting_green_first_ball_context_human_confirmed") is not True
                or human.get("game_context_verified_by_memory") is not False):
            return invalid
        if (contact not in ("yes", "no", "unknown") or green not in ("yes", "no", "unknown")
                or not (type(seen) is bool or seen is None) or type(kind) is not str
                or kind not in ("green", "offgreen", "uncertain", "transitioned")
                or source not in ("offgreen_100ft_penalty", "offgreen_display_unverified",
                                  "ongreen_display_human", "unseen_or_not_recorded")
                or unit not in ("ft", "yd", "m", "unknown", "not-visible")
                or (value is not None and (type(value) not in (int, float)
                    or not math.isfinite(value) or not 0 <= value <= 100000))
                or human.get("game_distance_verified_by_memory") is not False):
            return invalid
        if ((kind == "green" and (green != "yes" or seen is not True))
                or (kind == "offgreen" and (green != "no" or seen is not True))
                or (kind in ("uncertain", "transitioned") and green != "unknown")
                or (kind == "transitioned" and seen is not False)
                or (kind == "uncertain" and seen is not None)
                or (source == "offgreen_100ft_penalty" and
                    not (kind == "offgreen" and value == 100.0 and unit == "ft"))
                or (source == "ongreen_display_human" and
                    not (kind == "green" and value is not None))
                or (source == "offgreen_display_unverified" and
                    not (kind == "offgreen" and value is not None))
                or (source == "unseen_or_not_recorded" and value is not None)
                or (kind in ("uncertain", "transitioned") and source != "unseen_or_not_recorded")
                or (kind == "green" and source not in
                    ("ongreen_display_human", "unseen_or_not_recorded"))
                or (kind == "offgreen" and source not in
                    ("offgreen_100ft_penalty", "offgreen_display_unverified",
                     "unseen_or_not_recorded"))
                or (value is None and unit != "not-visible")
                or (value is not None and unit == "not-visible")):
            return invalid
        screen = item.get("settled_screen_observation")
        if screen != ("human_terminal_before_transition" if seen is True
                      else "human_terminal_unseen_or_unknown"):
            return invalid
        informative = (contact == "yes" and seen is True
                       and kind in ("green", "offgreen"))
        return {
            "capture_status": "visual_first_joined",
            # The collector attests scheduled RPCs, not in-game ball contact.
            "informative_action_outcome_trial": informative,
            "hitting_green_first_ball_context_human_confirmed": True,
            "game_id_revision_mode_machine_verified": False,
            "shot_dispatch_verified_by_collector": True,
            "controller": {"trace_sha256": digest, "generated_trace_frames": 89,
                           "a_lead_requested_frames": a_lead,
                           "a_lead_observed_frame_delta": swing["a_lead_observed_frame_delta"],
                           "speed_scale": speed, "backswing_scale": backswing,
                           "motion_scale": 1.0},
            "human": {"contact_human": contact, "finished_on_green_human": green,
                      "terminal_screen_seen_before_transition_human": seen,
                      "visible_result_class_human": kind,
                      "displayed_distance_source": source,
                      "displayed_distance_human": value,
                      "displayed_unit_human": unit,
                      "initial_club_pose_human": pose,
                      "shot_start_bridge_tick_before_trace": shot_start,
                      "displayed_power_percent_human": power},
            "settled_screen_observation": screen,
            "outcome_is_censored_penalty": source == "offgreen_100ft_penalty",
            # A human HUD number is never a measured physical carry distance.
            "numeric_distance_target_eligible": False,
            "train_approved": False,
            "verified_game_score": False,
            "physical_distance_verified": False,
        }
    except (OSError, ValueError, UnicodeError, TypeError, OverflowError):
        return invalid


def _fallback_human_observation(*, answer=input) -> dict:
    """Allow a human to save contact/pose when the normal collector lacks a summary.

    Never infer a hit from process status. A blank answer means unknown.
    """
    allowed = {"back", "center", "forward", "unknown"}
    pose = answer("Starting club pose [back/center/forward/unknown; blank=unknown]: ").strip().lower()
    if pose not in allowed:
        pose = "unknown"
    contact = answer("Did ball visibly make contact? [yes/no/unknown; blank=unknown]: ").strip().lower()
    if contact not in {"yes", "no", "unknown"}:
        contact = "unknown"
    timing = answer("Swing motion looked [early/late/on-time/unknown; blank=unknown]: ").strip().lower()
    if timing not in {"early", "late", "on-time", "unknown"}:
        timing = "unknown"
    return {"capture_status": "human_fallback_after_missing_collector_summary",
            "human": {"initial_club_pose_human": pose,
                      "contact_human": contact,
                      "motion_timing_human": timing},
            "verified_game_score": False,
            "warning": "Human memory only; collector did not publish a complete capture"}


def _missing_capture_needs_fallback(record: dict) -> bool:
    return record.get("capture_status") in (None, "none_or_ambiguous",
                                            "unreadable_summary",
                                            "unexpected_summary_shape",
                                            "unexpected_summary_source")



def _git(args: list[str], *, cwd: Path) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                       text=True, check=False, timeout=60)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "Git command failed").strip()[:500])
    return p.stdout.strip()


def publish_summary(summary: dict) -> str:
    """Append a tiny allowlisted record to a separate branch, never main.

    Uses a temporary shallow clone to keep the operator's code working tree
    untouched. Refuses to create a new branch implicitly or force-push.
    """
    with tempfile.TemporaryDirectory(prefix="wii-golf-observation-") as tmp:
        work = Path(tmp)
        # Reuse configured origin URL only after sync_merged_main verified it.
        url = _git(["remote", "get-url", "origin"], cwd=ROOT)
        from wii_ai_golf.lab.github_sync import _trusted_url
        if not _trusted_url(url):
            raise RuntimeError("Refusing publication to unapproved GitHub origin")
        _git(["clone", "--quiet", "--single-branch", "--branch", OBS_BRANCH,
              "--depth", "1", url, str(work / "repo")], cwd=work)
        repo = work / "repo"
        target = repo / "research" / "observations"
        target.mkdir(parents=True, exist_ok=True)
        name = summary["id"] + ".json"
        file = target / name
        with file.open("x", encoding="utf-8") as out:
            json.dump(summary, out, indent=2, sort_keys=True, allow_nan=False)
            out.write("\n")
        _git(["add", "--", str(file.relative_to(repo))], cwd=repo)
        _git(["-c", "user.name=Wii Golf Research Worker",
              "-c", "user.email=research-worker@users.noreply.github.com",
              "commit", "-m", "research: record sanitized " + summary["kind"] + " result"], cwd=repo)
        # No force. Concurrent writers are never overwritten; operator can
        # retry publish from locally preserved summary if needed.
        _git(["push", "origin", "HEAD:" + OBS_BRANCH], cwd=repo)
    return "https://github.com/Nate27624/Wii-AI-Golf/tree/" + OBS_BRANCH + "/research/observations"



POWER_MAP_ID = "S003-POWER-MAP-10-V1"
# Five conditions twice, same first-ball scenario on independent fresh boots.
POWER_MAP_STUDY = ((1.0,1.0),(0.8,1.0),(1.0,1.2),(0.9,1.0),(1.0,0.8),
                   (1.0,1.0),(1.0,0.8),(0.9,1.0),(1.0,1.2),(0.8,1.0))


def power_map_commands() -> list[str]:
    return [("py scripts/research_cli.py v1 --live --a-lead 45 "
             f"--speed-scale {speed:.1f} --backswing-scale {back:.1f} "
             f"--study-id {POWER_MAP_ID} --trial-index {i}")
            for i, (speed, back) in enumerate(POWER_MAP_STUDY, 1)]


def show_power_map() -> None:
    print("S003 10-shot study: 10 fresh-boot FIRST-HOLE trials, NOT ten unique holes.")
    print("Close Dolphin between trials. Fixed V1 bridge, A lead 45, full forward travel.")
    print("For each: report contact, starting pose, visible power%, green and score.")
    print("Use 't' if the game transitions before the settled capture; 100ft off-green is a penalty.")
    for i, cmd in enumerate(power_map_commands(), 1):
        speed, back = POWER_MAP_STUDY[i - 1]
        print(f"\nTrial {i:02d}/10: speed {speed:.1f}x, backwards travel {back:.1f}x")
        print(cmd)
    print("Stop on unsafe state, failed button hold or unmatched bridge. No automatic multi-hole navigation.")



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="Fast-forward clean trusted main; never start Dolphin")
    commands.add_parser("study", help="Print preregistered 10-shot plan; no Dolphin")
    t = commands.add_parser("test", help="Sync, run focused offline unittests, publish results")
    t.add_argument("--pattern", default="test_*.py")
    t.add_argument("--no-upload", action="store_true", help="Keep results local")
    v = commands.add_parser("v1", help="Sync, execute ONE isolated historic V1 shot, publish sanitized report")
    v.add_argument("--a-lead", type=int, default=0)
    v.add_argument("--backswing-scale", type=float, choices=(0.8, 1.0, 1.2), default=1.0,
                   help="Scale only backswing travel; all other motion/A unchanged")
    v.add_argument("--speed-scale", type=float, choices=(0.8, 0.9, 1.0, 1.1), default=1.0,
                   help="Change swing speed only; preserve club travel and A timing")
    v.add_argument("--motion-scale", type=float, choices=(0.6, 0.8, 1.0, 1.2), default=1.0,
                   help="Controlled motion calibration; 1.0 exactly reproduces verified baseline")
    v.add_argument("--study-id", choices=(POWER_MAP_ID,), default=None)
    v.add_argument("--trial-index", type=int, choices=range(1,11), default=None)
    v.add_argument("--live", action="store_true", help="Explicit consent to launch Dolphin")
    v.add_argument("--no-upload", action="store_true", help="Keep report local")
    v.add_argument("--visual-first", action="store_true",
                   help="M1.5 one-shot terminal HUMAN result first; no RAM scoring")
    args = parser.parse_args(argv)
    try:
        report = sync_merged_main(ROOT)  # CLI workflow does not use retired GUI lockfiles
        print("GitHub main sync:", report.status, report.note, flush=True)
        if report.status not in ("updated", "up_to_date"):
            print("No experiment started; resolve sync blocker first.", file=sys.stderr)
            return 2
        if args.command == "sync":
            return 0
        if args.command == "study":
            show_power_map()
            return 0
        if args.command == "v1" and (not args.live or type(args.a_lead) is not int
                                     or not 0 <= args.a_lead <= 90):
            parser.error("v1 requires --live and --a-lead between 0 and 90")
        if args.command == "v1" and args.motion_scale != 1.0:
            parser.error("--motion-scale alters travel AND speeds; use --speed-scale for one-variable calibration")
        if args.command == "v1" and args.backswing_scale != 1.0 and args.speed_scale != 1.0:
            parser.error("change either --backswing-scale or --speed-scale, not both")
        if args.command == "v1":
            # M1.5 is a preregistered B1/B2/X1 pilot, not a free-form sweep.
            # Refuse mismatched settings BEFORE touching the emulator or bridge.
            if args.visual_first and (args.a_lead != 45 or args.speed_scale != 1.0
                                      or args.backswing_scale not in (1.0, 1.2)):
                parser.error("M1.5 --visual-first requires --a-lead 45, "
                             "--speed-scale 1.0, and --backswing-scale 1.0 or 1.2")
            if args.visual_first and args.study_id is not None:
                parser.error("The M1.5 visual-first pilot is not the 10-shot power-map study")
            if (args.study_id is None) != (args.trial_index is None):
                parser.error("--study-id and --trial-index must be used together")
            if args.study_id:
                expected_speed, expected_back = POWER_MAP_STUDY[args.trial_index - 1]
                if (args.a_lead != 45 or args.motion_scale != 1.0
                    or args.speed_scale != expected_speed
                    or args.backswing_scale != expected_back):
                    parser.error("Trial settings differ from preregistered plan")
        begin = datetime.now(timezone.utc)
        run_token = begin.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10]
        if args.command == "test":
            exit_code = _run([sys.executable, "-m", "unittest", "discover",
                              "-s", "tests", "-p", args.pattern, "-v"])
        else:
            bridge = ROOT.parent / "tools" / "mcp_bridge_swing_legacy_eval.py"
            from wii_ai_golf.shared.bridge_provenance import inspect_bridge_file
            identity = inspect_bridge_file(bridge)
            if identity["revision"] != "V1-neutral-swing-calls" or not identity["safe_for_isolated_legacy_copy"]:
                raise RuntimeError("Verified isolated V1 bridge missing; will not launch Dolphin")
            clean_boot = v1_clean_boot_args(ROOT)
            print("Close existing Dolphin before this ONE live trial.", flush=True)
            action = [sys.executable, str(ROOT / "scripts" / "run_golf_experiment.py"),
                      "--send-live", *clean_boot, "--bridge", str(bridge),
                      "--script", "collect_outcome_transition.py", "--",
                      "--send-live-swing", "--a-prime-requests", "0",
                      "--a-lead-frames", str(args.a_lead),
                      "--observe-start-pose", "--motion-scale", str(args.motion_scale),
                      "--speed-scale", str(args.speed_scale),
                      "--backswing-scale", str(args.backswing_scale),
                      "--ask-power"]
            if args.visual_first:
                action.extend(["--visual-first", "--run-token", run_token])
            exit_code = _run(action)
        summary = {"schema": 1,
                   "id": run_token,
                   "kind": args.command, "started_utc": begin.isoformat(),
                   "git_commit": _head(), "process_exit_code": exit_code,
                   "verified_game_score": False}
        if args.command == "test":
            summary["test_pattern"] = args.pattern
            summary["outcome"] = "pass" if exit_code == 0 else "fail"
        else:
            summary["requested_a_lead_frames"] = args.a_lead
            summary["requested_motion_scale"] = args.motion_scale
            summary["requested_speed_scale"] = args.speed_scale
            summary["requested_backswing_scale"] = args.backswing_scale
            if args.study_id:
                summary["study_id"] = args.study_id
                summary["trial_index"] = args.trial_index
                summary["trial_count"] = len(POWER_MAP_STUDY)
            summary["bridge_sha256"] = _sha_file(bridge)
            if args.visual_first:
                summary["visual_first"] = True
                if exit_code == 0:
                    summary.update(_joined_visual_first(
                        run_token, begin, a_lead=args.a_lead,
                        speed=args.speed_scale, backswing=args.backswing_scale))
                else:
                    summary.update({"capture_status": "failed_or_cancelled_action",
                                    "shot_dispatch_verified_by_collector": False})
            elif exit_code == 0:
                summary.update(_fresh_human_labels(begin))
                if _missing_capture_needs_fallback(summary):
                    print("No unambiguous completed collector summary. "
                          "Recording HUMAN-only observation to avoid losing this trial.", flush=True)
                    summary.update(_fallback_human_observation())
            else:
                summary["capture_status"] = "failed_or_cancelled_action"
        private = DATA / "research-cli"
        private.mkdir(parents=True, exist_ok=True)
        dest = private / (summary["id"] + ".json")
        with dest.open("x", encoding="utf-8") as out:
            json.dump(summary, out, indent=2, sort_keys=True, allow_nan=False)
            out.write("\n")
        print("Local sanitized result:", dest, flush=True)
        # Never publish a failed/cancelled action, nor a visual result whose
        # unique child shot/trace token cannot be joined to this exact command.
        if args.command == "v1" and (exit_code != 0 or
                (args.visual_first and (summary.get("capture_status") != "visual_first_joined"
                                        or summary.get("informative_action_outcome_trial") is not True))):
            print("M1.5 outcome NOT eligible; no GitHub publication.", flush=True)
            return exit_code if exit_code != 0 else 2
        if not args.no_upload:
            try:
                url = publish_summary(summary)
                print("GitHub observation published:", url, flush=True)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                print("Upload NOT completed; local sanitized result remains saved:",
                      exc, file=sys.stderr, flush=True)
                return 3 if exit_code == 0 else exit_code
        return exit_code
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print("Research command failed (no success claimed):", exc,
              file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
