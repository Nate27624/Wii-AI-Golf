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
        result["settled_screen_observation"] = content.get("settled_screen_observation")
        return result
    except (OSError, ValueError, UnicodeError):
        return {"capture_status": "unreadable_summary"}



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
    from wii_ai_golf.shared.public_observation import public_observation
    clean = public_observation(summary)  # fail closed BEFORE any Git/network access
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
        name = clean["id"] + ".json"
        file = target / name
        with file.open("x", encoding="utf-8") as out:
            json.dump(clean, out, indent=2, sort_keys=True, allow_nan=False)
            out.write("\n")
        _git(["add", "--", str(file.relative_to(repo))], cwd=repo)
        _git(["-c", "user.name=Wii Golf Research Worker",
              "-c", "user.email=research-worker@users.noreply.github.com",
              "commit", "-m", "research: record sanitized " + clean["kind"] + " result"], cwd=repo)
        # No force. Concurrent writers are never overwritten; operator can
        # retry publish from locally preserved summary if needed.
        _git(["push", "origin", "HEAD:" + OBS_BRANCH], cwd=repo)
    return "https://github.com/Nate27624/Wii-AI-Golf/tree/" + OBS_BRANCH + "/research/observations"



def publish_saved_scene_root(record_id: str, *, local_only: bool = False) -> str:
    """Reuse an EXISTING sanitized probe report; no new Dolphin/RPC run.

    Deliberately restrict input to one source-approved report type in the
    private sibling captures directory. No arbitrary --file arguments.
    """
    from wii_ai_golf.shared.public_observation import TRIAL_ID, public_observation
    if (type(record_id) is not str or not TRIAL_ID.fullmatch(record_id)
        or record_id.startswith(("cohort-", "offline-"))):
        raise ValueError("Invalid source-gated scene-root record ID")
    captures = DATA / "captures"
    path = captures / ("golf-scene-root-" + record_id + "-summary.json")
    if (captures.is_symlink() or path.is_symlink() or not path.is_file()
        or not 0 < path.stat().st_size <= 16_384):
        raise ValueError("Saved scene-root report missing, linked or oversized")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("Saved scene-root report is not readable JSON") from exc
    if type(record) is not dict or record.get("id") != record_id:
        raise ValueError("Saved scene-root report ID mismatch")
    clean = public_observation(record)  # no raw/private fields or pointers
    if clean.get("kind") != "golf_scene_root_candidate_triage":
        raise ValueError("Not an approved scene-root report")
    if local_only:
        return "VALID LOCAL-ONLY scene-root report; no upload attempted"
    return publish_summary(clean)  # same existing reviewed Git authentication


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
    saved = commands.add_parser("publish-saved-scene-root",
                                help="Validate or publish an existing sanitized scene-root report; no Dolphin")
    saved.add_argument("--id", required=True, help="Record ID printed by source-gated probe")
    saved.add_argument("--local-only", action="store_true",
                       help="Validate saved report but do not upload")

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
        if args.command == "publish-saved-scene-root":
            result = publish_saved_scene_root(args.id, local_only=args.local_only)
            print("Scene-root saved report:", result, flush=True)
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
        if args.command == "test":
            exit_code = _run([sys.executable, "-m", "unittest", "discover",
                              "-s", "tests", "-p", args.pattern, "-v"])
        else:
            bridge = ROOT.parent / "tools" / "mcp_bridge_swing_legacy_eval.py"
            from wii_ai_golf.shared.bridge_provenance import inspect_bridge_file
            identity = inspect_bridge_file(bridge)
            if identity["revision"] != "V1-neutral-swing-calls" or not identity["safe_for_isolated_legacy_copy"]:
                raise RuntimeError("Verified isolated V1 bridge missing; will not launch Dolphin")
            print("Close existing Dolphin before this ONE live trial.", flush=True)
            exit_code = _run([sys.executable, str(ROOT / "scripts" / "run_golf_experiment.py"),
                              "--send-live", "--bridge", str(bridge),
                              "--script", "collect_outcome_transition.py", "--",
                              "--send-live-swing", "--a-lead-frames", str(args.a_lead),
                              "--observe-start-pose", "--motion-scale", str(args.motion_scale),
                              "--speed-scale", str(args.speed_scale),
                              "--backswing-scale", str(args.backswing_scale),
                              "--ask-power"])
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
            summary.update(_fresh_human_labels(begin))
            if _missing_capture_needs_fallback(summary):
                print("No unambiguous completed collector summary. "
                      "Recording HUMAN-only observation to avoid losing this trial.", flush=True)
                summary.update(_fallback_human_observation())
        private = DATA / "research-cli"
        private.mkdir(parents=True, exist_ok=True)
        dest = private / (summary["id"] + ".json")
        with dest.open("x", encoding="utf-8") as out:
            json.dump(summary, out, indent=2, sort_keys=True, allow_nan=False)
            out.write("\n")
        print("Local sanitized result:", dest, flush=True)
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
