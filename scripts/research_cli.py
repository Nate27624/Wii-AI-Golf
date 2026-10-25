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
               "displayed_unit_human", "shot_start_frame_before_controller_trace")
SAFE_TRACE = ("trace_sha256", "generated_trace_frames",
              "a_lead_requested_frames", "a_lead_observed_frame_delta")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="Fast-forward clean trusted main; never start Dolphin")
    t = commands.add_parser("test", help="Sync, run focused offline unittests, publish results")
    t.add_argument("--pattern", default="test_*.py")
    t.add_argument("--no-upload", action="store_true", help="Keep results local")
    v = commands.add_parser("v1", help="Sync, execute ONE isolated historic V1 shot, publish sanitized report")
    v.add_argument("--a-lead", type=int, default=0)
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
        if args.command == "v1" and (not args.live or type(args.a_lead) is not int
                                     or not 0 <= args.a_lead <= 90):
            parser.error("v1 requires --live and --a-lead between 0 and 90")
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
                              "--observe-start-pose"])
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
