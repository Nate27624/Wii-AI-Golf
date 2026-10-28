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
    # Source-backed Felk Preview4 portable selector. An adjacent User folder
    # alone does not prove the running Dolphin chooses that profile root.
    portable_marker = clean / "portable.txt"
    user = clean / "User"
    config = root / "research" / "launch.local.json"
    catalog = root / "research" / "savestates.local.json"
    missing = []
    for label, present in (
        ("isolated clean Dolphin executable", executable.is_file()),
        ("clean Dolphin portable.txt marker", portable_marker.is_file()),
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


def _fresh_human_labels(start_time: datetime, *, run_token: str | None = None,
                        expected_controller: dict | None = None) -> dict:
    """Accept only THIS completed child shot; local file mtime is not identity.

    The nonce is private and never copied into the public summary. Reject
    missing/foreign results, failed traces, altered settings and wrong source.
    """
    if type(run_token) is not str or len(run_token) != 32 or expected_controller is None:
        return {"capture_status": "unqualified_missing_run_identity"}
    if not CAPTURES.is_dir():
        return {"capture_status": "none_or_ambiguous"}
    options = [p for p in CAPTURES.glob("outcome-*-candidates.json")
               if p.is_file() and p.stat().st_mtime >= start_time.timestamp()]
    matches = []
    for path in options:
        try:
            if path.stat().st_size > 2_000_000:
                continue
            content = json.loads(path.read_text(encoding="utf-8"))
            if (type(content) is dict and content.get("run_token") == run_token
                    and content.get("source") == "live-emulator-read-only-US-Rev1+human-result-label"):
                matches.append(content)
        except (OSError, ValueError, UnicodeError):
            continue
    if len(matches) != 1:
        return {"capture_status": "none_or_ambiguous"}
    content = matches[0]
    human = content.get("human_observation")
    swing = content.get("known_good_swing_request")
    dispatch = content.get("swing_dispatch")
    if not (type(human) is dict and type(swing) is dict and type(dispatch) is dict
            and dispatch.get("state") == "complete"
            and type(swing.get("generated_trace_frames")) is int
            and swing["generated_trace_frames"] > 0
            and type(dispatch.get("applied_frames")) is int
            and dispatch["applied_frames"] == swing["generated_trace_frames"]
            and type(swing.get("trace_sha256")) is str
            and len(swing["trace_sha256"]) == 64
            and all(c in "0123456789abcdef" for c in swing["trace_sha256"])  # literal trace hash
            and all(type(swing.get(k)) is type(v) and swing[k] == v
                    for k, v in expected_controller.items())
            and human.get("contact_human") in ("yes", "no", "unknown")
            and human.get("finished_on_green_human") in ("yes", "no", "unknown")):
        return {"capture_status": "unqualified_child_trace_or_controls"}
    timing = content.get("settled_screen_observation")
    if timing not in ("operator_confirmed_before_transition",
                      "screen_had_already_transitioned_before_settled_samples"):
        return {"capture_status": "unqualified_terminal_timing"}
    category = content.get("terminal_human_category")
    if (content.get("terminal_capture_mode") != "result_first_human_prompt"
            or category not in ("on_green", "off_green", "visible_unknown", "transitioned")
            or (category == "on_green" and human["finished_on_green_human"] != "yes")
            or (category == "off_green" and human["finished_on_green_human"] != "no")
            or (category in ("visible_unknown", "transitioned")
                and human["finished_on_green_human"] != "unknown")):
        return {"capture_status": "unqualified_terminal_category_or_mode"}
    safe_human = {k: human[k] for k in SAFE_LABELS if k in human
                  and (human[k] is None or type(human[k]) in (str, int, float, bool))}
    safe_trace = {k: swing[k] for k in SAFE_TRACE if k in swing
                  and (swing[k] is None or type(swing[k]) in (str, int, float, bool))}
    penalty = (human.get("finished_on_green_human") == "no"
               and human.get("displayed_distance_human") == 100
               and human.get("displayed_unit_human") == "ft")
    return {
        "capture_status": "sanitized_human_annotation_only",
        "shot_dispatch_status": "bridge_trace_completed_not_game_contact_verified",
        "human": safe_human, "controller": safe_trace,
        "settled_screen_observation": timing,
        "terminal_capture_mode": "result_first_human_prompt",
        "terminal_human_category": category,
        "distance_interpretation": (
            "censored_offgreen_100ft_penalty" if penalty
            else "human_label_not_physical_distance_verified"),
        "physical_distance_verified": False,
    }


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
            if (args.study_id is None) != (args.trial_index is None):
                parser.error("--study-id and --trial-index must be used together")
            if args.study_id:
                expected_speed, expected_back = POWER_MAP_STUDY[args.trial_index - 1]
                if (args.a_lead != 45 or args.motion_scale != 1.0
                    or args.speed_scale != expected_speed
                    or args.backswing_scale != expected_back):
                    parser.error("Trial settings differ from preregistered plan")
        begin = datetime.now(timezone.utc)
        run_token = uuid.uuid4().hex if args.command == "v1" else None
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
            exit_code = _run([sys.executable, str(ROOT / "scripts" / "run_golf_experiment.py"),
                              "--send-live", *clean_boot, "--bridge", str(bridge),
                              "--script", "collect_outcome_transition.py", "--",
                              "--send-live-swing", "--a-prime-requests", "0",
                              "--a-lead-frames", str(args.a_lead),
                              "--observe-start-pose", "--motion-scale", str(args.motion_scale),
                              "--speed-scale", str(args.speed_scale),
                              "--backswing-scale", str(args.backswing_scale),
                              "--ask-power", "--result-first",
                              "--run-token", run_token])
        summary = {"schema": 1,
                   "id": begin.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10],
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
            # The wrapper can forward boot/child errors. A zero exit alone is
            # not a completed shot; a missing summary is NOT fallback contact.
            if exit_code == 0:
                labels = _fresh_human_labels(
                    begin, run_token=run_token,
                    expected_controller={
                        "a_lead_requested_frames": args.a_lead,
                        "motion_scale": args.motion_scale,
                        "speed_scale": args.speed_scale,
                        "backswing_scale": args.backswing_scale,
                    })
                summary.update(labels)
            if (exit_code != 0 or summary.get("capture_status") !=
                    "sanitized_human_annotation_only"):
                summary["kind"] = "v1_attempt"
                summary["attempt_status"] = (
                    "nonzero_launcher_or_collector_exit" if exit_code != 0
                    else "missing_or_unqualified_child_summary")
                summary["shot_dispatched"] = "unknown"
                summary["trial_valid_for_action_outcome"] = False
            elif (summary.get("settled_screen_observation") !=
                    "operator_confirmed_before_transition"
                  or summary.get("terminal_capture_mode") != "result_first_human_prompt"
                  or summary.get("terminal_human_category") not in ("on_green", "off_green")):
                # Only a human-labeled terminal category observed before any
                # post-shot RAM can be a categorical action/outcome example.
                summary["kind"] = "v1_attempt"
                summary["attempt_status"] = "terminal_result_missing_or_unqualified"
                summary["trial_valid_for_action_outcome"] = False
            elif (type(summary.get("human")) is not dict
                  or summary["human"].get("contact_human") != "yes"):
                # A completed controller trace is NOT evidence of impact.
                # Keep no/unknown-contact attempts local, not training examples.
                summary["kind"] = "v1_attempt"
                summary["attempt_status"] = "positive_ball_contact_not_observed"
                summary["trial_valid_for_action_outcome"] = False
            else:
                summary["trial_valid_for_action_outcome"] = True
        private = DATA / "research-cli"
        private.mkdir(parents=True, exist_ok=True)
        dest = private / (summary["id"] + ".json")
        with dest.open("x", encoding="utf-8") as out:
            json.dump(summary, out, indent=2, sort_keys=True, allow_nan=False)
            out.write("\n")
        print("Local sanitized result:", dest, flush=True)
        # Keep canceled, incomplete and unqualified runs LOCAL; never publish
        # as completed V1 observations, even when the launcher exited zero.
        eligible_to_publish = args.command != "v1" or summary["kind"] == "v1"
        if not args.no_upload and eligible_to_publish:
            try:
                url = publish_summary(summary)
                print("GitHub observation published:", url, flush=True)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                print("Upload NOT completed; local sanitized result remains saved:",
                      exc, file=sys.stderr, flush=True)
                return 3 if exit_code == 0 else exit_code
        if args.command == "v1" and not eligible_to_publish:
            print("No completed V1 result published: child trial identity or outcome unverified.", flush=True)
            return exit_code if exit_code != 0 else 2
        return exit_code
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print("Research command failed (no success claimed):", exc,
              file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
