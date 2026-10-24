"""Single entry point for Wii Sports Golf research and experiments.

All real-game commands delegate to existing audited scripts; this module
does not reimplement Dolphin startup, menu timings, savestate selection,
swing physics, evaluation or training. Python stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from . import __version__
from .research_catalog import evidence_summary, study_summary

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
DATA_ROOT = ROOT.parent / "Wii-AI-Golf-Data"
DEFAULT_EVIDENCE = DATA_ROOT / "integration" / "swing-probes.jsonl"
DEFAULT_QUEUE = ROOT / "research" / "queue.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="golf",
        description="Wii AI Golf: one interface for real-game control and reproducible research",
        epilog="Standard golf actions ALWAYS use the canonical Dolphin + savestate + A/A+B/A startup.",
    )
    parser.add_argument("--version", action="version", version=f"wii-ai-golf {__version__}")
    sub = parser.add_subparsers(dest="group", required=True)

    sub.add_parser("doctor", help="Check local files/configuration without launching Dolphin")

    def live_options(cmd):
        chk = cmd.add_mutually_exclusive_group()
        chk.add_argument("--slot", type=int, help="Registered pre-start state slot, e.g. 2")
        chk.add_argument("--profile", help="Registered pre-start profile name")
        cmd.add_argument("--game", help="Game image path (remembered locally after first use)")
        cmd.add_argument("--dolphin", help="Override Felk Dolphin executable")
        cmd.add_argument("--bridge", help="Override existing swing-enabled bridge")
        cmd.add_argument("--dolphin-user", help="Override local Dolphin User folder")
        cmd.add_argument("--dry-run", action="store_true", help="Show exact delegated command without launching")
    play = sub.add_parser("play", help="Fresh Dolphin boot, registered state restore, A/A+B/A intro")
    live_options(play)
    shot = sub.add_parser("swing", help="Fresh intro then one guarded human-confirmed swing")
    live_options(shot)
    shot.add_argument("--preset", choices=("forward", "reverse", "sideways"), default="forward")
    shot.add_argument("--follow-through-frames", type=int, default=30)
    shot.add_argument("--report", help="Override local swing observation JSONL path")

    experiment = sub.add_parser("experiment", help="Fresh intro then an approved action script")
    experiment.add_argument("--script", required=True, help="Existing scripts/*.py action name")
    experiment.add_argument("--game", help="Game image path if not saved")
    experiment.add_argument("--send-live", action="store_true",
                            help="Actually launch Dolphin and run the requested action; otherwise dry-run")
    experiment.add_argument("action_args", nargs=argparse.REMAINDER,
                            help="Action flags after --, passed to the safe coordinator wrapper")

    state = sub.add_parser("state", help="Inspect or manage named LOCAL savestate profiles")
    state.add_argument("--catalog", help="Override local named-state catalog")
    states = state.add_subparsers(dest="state_action", required=True)
    states.add_parser("list", help="List registered state names and slots; offline")
    register = states.add_parser("register", help="Label an already-existing slot; does not create a save")
    register.add_argument("name")
    register.add_argument("--slot", required=True, type=int)
    register.add_argument("--description", default="")
    reset = states.add_parser("reset", help="Advanced: reset named state in an EXISTING running Dolphin")
    reset.add_argument("name")

    scenarios = sub.add_parser("scenarios", help="Observed scene registry / offline coverage planning")
    scenarios.add_argument("action", choices=("list", "add", "plan", "load-attempt"))
    scenarios.add_argument("arguments", nargs=argparse.REMAINDER,
                           help="Extra arguments passed to the existing scenario planner")

    bridge = sub.add_parser("bridge", help="Advanced bridge utilities")
    bridge.add_argument("action", choices=("patch", "ping"))
    bridge.add_argument("arguments", nargs=argparse.REMAINDER,
                        help="For patch: --source/--output/--enable-swing; ping: --read-only-live")

    research = sub.add_parser("research", help="Studies, observed swing evidence and RAM audits")
    r_sub = research.add_subparsers(dest="research_action", required=True)
    studies = r_sub.add_parser("studies", help="Show S001..S005 hypotheses, ownership and blockers")
    studies.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    studies.add_argument("--json", action="store_true")
    evidence = r_sub.add_parser("evidence", help="Summarize local human-observed swing JSONL safely")
    evidence.add_argument("--path", type=Path, default=DEFAULT_EVIDENCE)
    evidence.add_argument("--json", action="store_true")
    audit = r_sub.add_parser("audit-motion", help="Offline audit of sanitized S002 RAM report")
    audit.add_argument("--input", required=True)
    audit.add_argument("--baseline")
    audit.add_argument("--out")

    tests = sub.add_parser("test", help="Run project unittest suite against THIS checkout")
    tests.add_argument("--pattern", default="test_*.py")

    sub.add_parser("demo", help="Run the existing SYNTHETIC toy environment (not Wii Sports)")
    return parser


def _environment() -> dict[str, str]:
    env = os.environ.copy()
    # Child scripts have their own source bootstrap, but this also keeps
    # Python -m, unittest and a stale editable installation deterministic.
    before = env.get("PYTHONPATH")
    paths = [str(ROOT / "src"), str(ROOT)]
    if before:
        paths.append(before)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def _script_command(script: str, *args: str) -> list[str]:
    path = SCRIPTS / script
    if not path.is_file():
        raise ValueError(f"Required project entrypoint missing: {path}")
    return [sys.executable, str(path), *args]


def _run(command: Sequence[str], *, dry_run: bool = False) -> int:
    if dry_run:
        print("DRY RUN (no process started):")
        print(json.dumps(list(command), indent=2))
        return 0
    try:
        return subprocess.run(list(command), cwd=ROOT, env=_environment(), check=False).returncode
    except OSError as exc:
        print(f"golf: could not run command: {exc}", file=sys.stderr)
        return 1


def doctor() -> int:
    checks = {
        "source checkout": (ROOT / "src" / "wii_ai_golf" / "cli.py").is_file(),
        "canonical game launcher": (SCRIPTS / "launch_golf.py").is_file(),
        "canonical intro": (SCRIPTS / "launch_hitting_green.py").is_file(),
        "swing probe": (SCRIPTS / "probe_swing.py").is_file(),
        "named savestate catalog (local)": (ROOT / "research" / "savestates.local.json").is_file(),
        "saved game/launch config (local)": (ROOT / "research" / "launch.local.json").is_file(),
        "Felk Dolphin executable (local)": (ROOT.parent / "tools" / "FelkDolphin" / "Dolphin.exe").is_file(),
        "swing bridge (local)": (ROOT.parent / "tools" / "mcp_bridge_swing.py").is_file(),
        "research study queue": DEFAULT_QUEUE.is_file(),
    }
    for name, present in checks.items():
        print(f"{'OK' if present else 'MISSING'}  {name}")
    print("Doctor is READ-ONLY: it does not start Dolphin, modify controller mode, or prove swing/score.")
    print("Local Dolphin files may be missing on GitHub/cloud or a different computer.")
    return 0 if all(checks[x] for x in (
        "source checkout", "canonical game launcher", "canonical intro", "swing probe",
        "research study queue")) else 1


def _game_options(args) -> list[str]:
    result = []
    if args.slot is not None:
        result += ["--slot", str(args.slot)]
    elif args.profile:
        result += ["--profile", args.profile]
    for flag in ("game", "dolphin", "bridge", "dolphin_user"):
        value = getattr(args, flag, None)
        if value is not None:
            result += ["--" + flag.replace("_", "-"), str(value)]
    return result


def execute(args: argparse.Namespace) -> int:
    if args.group == "doctor":
        return doctor()
    if args.group in ("play", "swing"):
        argv = _game_options(args)
        if args.group == "swing":
            if not 0 <= args.follow_through_frames <= 180:
                raise ValueError("--follow-through-frames must be 0..180")
            argv += ["--swing", "--preset", args.preset,
                     "--follow-through-frames", str(args.follow_through_frames)]
            if args.report is not None:
                argv += ["--report", str(args.report)]
        return _run(_script_command("launch_golf.py", *argv), dry_run=args.dry_run)
    if args.group == "experiment":
        action_args = list(args.action_args)
        if action_args and action_args[0] == "--":
            action_args.pop(0)
        argv = ["--script", args.script]
        if args.game:
            argv += ["--game", args.game]
        if args.send_live:
            argv += ["--send-live"]
        return _run(_script_command("run_golf_experiment.py", *argv, "--", *action_args))
    if args.group == "state":
        argv = []
        if args.catalog:
            argv += ["--catalog", args.catalog]
        if args.state_action == "list":
            argv += ["list"]
        elif args.state_action == "register":
            argv += ["register", args.name, "--slot", str(args.slot),
                     "--description", args.description]
        elif args.state_action == "reset":
            argv += ["reset", args.name]
        return _run(_script_command("savestate_session.py", *argv))
    if args.group == "scenarios":
        return _run(_script_command("plan_scenarios.py", args.action, *args.arguments))
    if args.group == "bridge":
        if args.action == "ping":
            return _run(_script_command("probe_dolphin_bridge.py", "--read-only-live", *args.arguments))
        return _run(_script_command("patch_felk_bridge.py", *args.arguments))
    if args.group == "research":
        if args.research_action == "studies":
            data = study_summary(args.queue)
        elif args.research_action == "evidence":
            data = evidence_summary(args.path)
        else:
            argv = ["--input", args.input]
            for key in ("baseline", "out"):
                if getattr(args, key):
                    argv += ["--" + key, getattr(args, key)]
            return _run(_script_command("audit_motion_candidates.py", *argv))
        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        elif args.research_action == "studies":
            print("Research direction (planning statuses; NOT proof of execution)")
            for item in data["studies"]:
                print(f"{item['study_id']}  {item['role']:<11} {item['title']}")
                print(f"      status={item['status']} | blocked_by={item['blocked_by']}")
            print("Gates: controlled live shot -> validated measured outcome -> calibration -> learning -> held-out evaluation.")
        else:
            print(f"Human-observed golf trials: {data['trials']} | "
                  f"complete bridge traces: {data['dispatch_complete']} | "
                  f"ball moved=yes: {data['ball_moved_yes']} | "
                  f"on green=yes: {data['on_green_yes']}")
            print(f"Unknown/invalid lines: {data['invalid_lines']} | "
                  f"score automatically verified: {data['verified_scores']}")
            print("Power readings are HUMAN VISUAL estimates, not game-internal power measurements.")
        return 0
    if args.group == "test":
        return _run([sys.executable, "-m", "unittest", "discover",
                     "-s", "tests", "-p", args.pattern, "-v"])
    if args.group == "demo":
        print("SYNTHETIC DEMO ONLY. Not a Wii Sports AI or real scored result.", flush=True)
        return _run([sys.executable, "-m", "wii_ai_golf.demo"])
    raise ValueError("Unsupported command")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return execute(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"golf: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
