"""Single entry point for Wii Sports Golf research and experiments.

All real-game commands delegate to existing audited scripts; this module
does not reimplement Dolphin startup, menu timings, savestate selection,
swing physics, evaluation or training. Python stdlib only.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
import socket
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
SWING_BRIDGE_PORT = 55355


@contextmanager
def reserve_bridge_port(port: int = SWING_BRIDGE_PORT):
    """Refuse an occupied port, without making a fragile outgoing TCP connection.

    On Windows a connection to an unused loopback port may time out instead
    of raising ConnectionRefusedError, despite there being NO listener.
    Binding an exclusive wildcard IPv4 socket detects an actual conflicting
    listener and keeps the port reserved until the bridge file is replaced.
    """
    try:
        guard = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError(f"Cannot inspect bridge port {port}: {exc}") from exc
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            guard.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        guard.bind(("0.0.0.0", port))
    except OSError as exc:
        guard.close()
        raise ValueError(
            f"Bridge port {port} is unavailable or occupied ({exc}). "
            "Close Dolphin; inspect the port's owning process before upgrading."
        ) from exc
    try:
        yield
    finally:
        guard.close()



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
    shot.add_argument("--a-setup-frames", type=int, default=12,
                      help="Neutral A-held samples INSIDE swing trace (known-good default 12)")
    shot.add_argument("--a-prime-frames", type=int, default=60,
                      help="Separate A-button-only RPC presses before ANY swing API call (default 60)")
    shot.add_argument("--report", help="Override local swing observation JSONL path")

    outcome = sub.add_parser(
        "outcome",
        help="S002 human-observed shot outcome collection via canonical full startup"
    )
    outcome_actions = outcome.add_subparsers(dest="outcome_action", required=True)
    record = outcome_actions.add_parser(
        "record",
        help="One full-start guarded shot, read-only RAM snapshots, and human landing label"
    )
    record.add_argument("--send-live", action="store_true",
                        help="Opt in to ONE real shot; default is coordinator dry-run")
    record.add_argument("--game", help="Optional game path, else local remembered game")
    record.add_argument("--pre-samples", type=int, default=3,
                        help="Read-only game snapshots BEFORE swing (2..10; default 3)")
    record.add_argument("--post-samples", type=int, default=2,
                        help="Read-only game snapshots after swing (2..40; S002 default 2)")
    record.add_argument("--settled-samples", type=int, default=3,
                        help="Read-only snapshots after human confirms result (2..10)")
    record.add_argument("--interval", type=float, default=0.0,
                        help="Delay between RAM captures in seconds (0..5; S002 default 0)")
    record.add_argument("--a-prime-requests", type=int, default=0,
                        help="Separate A-button priming requests BEFORE trace (0..180; default 0 is S002's last observed striking method)")
    record.add_argument("--data-dir", help="Override local PRIVATE output folder, never Git")
    
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
    bridge.add_argument("action", choices=("patch", "ping", "upgrade-swing", "inspect"))
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

    lab = sub.add_parser("lab", help="One shared S000-S005 experiment registry with desktop and CLI runners")
    actions = lab.add_subparsers(dest="lab_action", required=True)
    ls = actions.add_parser("list", help="All agent experiments and runnable/planned state")
    ls.add_argument("--json", action="store_true")
    desc = actions.add_parser("show", help="Describe one experiment and its owner")
    desc.add_argument("experiment_id")
    for name in ("plan", "run"):
        subcommand = actions.add_parser(
            name, help="Print exact safe command" if name == "plan" else
            "Execute one recorded test (live requires --live)"
        )
        subcommand.add_argument("experiment_id")
        subcommand.add_argument("--input", dest="input_path")
        subcommand.add_argument("--second-input")
        subcommand.add_argument("--out", dest="output_path")
        subcommand.add_argument("--contact", choices=("yes", "no", "unknown"))
        subcommand.add_argument("--green", choices=("yes", "no", "unknown"))
        subcommand.add_argument("--distance")
        subcommand.add_argument("--a-prime", type=int, default=0)
        subcommand.add_argument("--a-lead", type=int, default=0,
                                help="Experimental V1 A lead: 0..90 observed frames; 12 previously failed")
        subcommand.add_argument("--follow-through", type=int, default=30)
        if name == "run":
            subcommand.add_argument("--live", action="store_true",
                                    help="Explicitly approve ONE canonical Dolphin launch")
    recent = actions.add_parser("history", help="Inspect local per-run execution records, never score claims")
    recent.add_argument("--limit", type=int, default=20)
    recent.add_argument("--json", action="store_true")
    outcomes = actions.add_parser("reports", help="List ONLY sanitized local S002 human-observed outcome files")
    outcomes.add_argument("--limit", type=int, default=20)
    outcomes.add_argument("--json", action="store_true")
    sync = actions.add_parser("sync", help="Safely fast-forward approved GitHub main and discover new agent tests")
    sync.add_argument("--json", action="store_true")
    actions.add_parser("gui", help="Open the optional Windows Research Lab desktop application")

    sub.add_parser("demo", help="Run the existing SYNTHETIC toy environment (not Wii Sports)")
    return parser


def inspect_local_bridge(path: Path | None = None) -> dict[str, str | bool | None]:
    """Inspect local generated bridge text ONLY, never connect to Dolphin.

    A bridge on disk is not proof that a currently running emulator loaded
    these exact bytes, so avoid claims about loaded/runtime bridge versions.
    """
    target = path if path is not None else ROOT.parent / "tools" / "mcp_bridge_swing.py"
    if not target.is_file():
        return {
            "present": False, "bridge_sha256": None, "protocol_on_disk": "missing",
            "read_only": True,
            "caveat": "This does not inspect a running Dolphin process."
        }
    content = target.read_bytes()
    from .integration.swing_patch import SWING_MARKER, SWING_NEUTRAL_V2_MARKER
    v2 = SWING_NEUTRAL_V2_MARKER.encode("ascii") in content
    v1 = SWING_MARKER.encode("ascii") in content
    version = "V2-neutral-button-only" if v2 else (
        "V1-neutral-swing-events" if v1 else "unrecognized")
    return {
        "present": True,
        "bridge_sha256": hashlib.sha256(content).hexdigest(),
        "protocol_on_disk": version,
        "read_only": True,
        "caveat": ("This describes the generated file on disk only; "
                   "the exact loaded bridge must be verified separately.")
    }


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
    if args.group == "lab":
        from .lab import core
        if args.lab_action == "list":
            entries = core.available_experiments(ROOT)
            if args.json:
                print(json.dumps(entries, indent=2))
            else:
                for e in entries:
                    print(f"{e['id']:<27} {e['owner']}  {e['mode']:<8} {e['title']}")
                print("PLANNED != runnable. LIVE requires --live and operator confirmation.")
            return 0
        if args.lab_action == "show":
            e = core.get_experiment(args.experiment_id,
                                    catalog=core.available_experiments(ROOT))
            print(json.dumps(e, indent=2, sort_keys=True))
            return 0
        if args.lab_action in ("plan", "run"):
            p = core.plan(
                args.experiment_id, root=ROOT, python=sys.executable,
                input_path=args.input_path, second_input=args.second_input,
                output_path=args.output_path, a_prime=args.a_prime,
                a_lead=args.a_lead, follow_through=args.follow_through, contact=args.contact,
                green=args.green, distance=args.distance
            )
            if args.lab_action == "plan":
                print(json.dumps(p.summary(), indent=2))
                print("PREVIEW ONLY: no Dolphin process, RAM access, or file writes.")
                return 0
            print(f"LAB RUN {p.experiment['id']} | {p.experiment['mode']} | "
                  "game outcome not automatically verified", flush=True)
            record = core.execute(p, root=ROOT, allow_live=args.live)
            print("Local run:", record["run_id"], "status:",
                  record["execution_status"], "exit:", record.get("exit_code"), flush=True)
            return 0 if record.get("exit_code") == 0 else 1
        if args.lab_action == "sync":
            from .lab.github_sync import sync_merged_main
            result = sync_merged_main(ROOT, lab_data=DATA_ROOT / "lab")
            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print("GitHub sync:", result.status, "|", result.note)
                if result.changed_tests:
                    for test_path in result.changed_tests:
                        print("  updated agent test:", test_path)
                print("Run 'py scripts/golf.py lab list' to see the merged tests.")
                if result.status == "updated":
                    print("If the Lab app is already open, restart it to load changes "
                          "to its own Python modules.")
            return 0 if result.status in ("updated", "up_to_date") else 1
        if args.lab_action == "history":
            entries = core.history(DATA_ROOT / "lab", limit=args.limit)
            if args.json:
                print(json.dumps(entries, indent=2))
            else:
                if not entries:
                    print("No lab executions yet. History is LOCAL only.")
                for e in entries:
                    print(f"{e.get('run_id')}  {e.get('experiment_id')}  "
                          f"{e.get('execution_status')}  exit={e.get('exit_code')} "
                          "(NOT a game score)")
            return 0
        if args.lab_action == "gui":
            from .lab.gui import launch
            return launch(ROOT)
        if args.lab_action == "reports":
            from .lab.reports import sanitized_reports
            entries = sanitized_reports(root=ROOT, limit=args.limit)
            if args.json:
                print(json.dumps(entries, indent=2))
            else:
                if not entries:
                    print("No sanitized outcome reports yet. Raw RAM is not inspected.")
                for row in entries:
                    print(f"{row['path']} | USER contact={row['contact_human']} "
                          f"green={row['green_human']} distance={row['distance_human']} "
                          f"{row['unit_human']} | game score NOT verified")
            return 0
    if args.group == "doctor":
        return doctor()
    if args.group in ("play", "swing"):
        argv = _game_options(args)
        if args.group == "swing":
            if not 0 <= args.follow_through_frames <= 180:
                raise ValueError("--follow-through-frames must be 0..180")
            if not 1 <= args.a_setup_frames <= 180:
                raise ValueError("--a-setup-frames must be 1..180")
            if not 0 <= args.a_prime_frames <= 180:
                raise ValueError("--a-prime-frames must be 0..180")
            argv += ["--swing", "--preset", args.preset,
                     "--follow-through-frames", str(args.follow_through_frames),
                     "--a-setup-frames", str(args.a_setup_frames),
                     "--a-prime-frames", str(args.a_prime_frames)]
            if args.report is not None:
                argv += ["--report", str(args.report)]
        return _run(_script_command("launch_golf.py", *argv), dry_run=args.dry_run)
    if args.group == "outcome":
        if not (2 <= args.pre_samples <= 10
                and 2 <= args.post_samples <= 40
                and 2 <= args.settled_samples <= 10):
            raise ValueError("outcome record: pre=2..10, post=2..40, settled=2..10")
        if not math.isfinite(args.interval) or not 0 <= args.interval <= 5:
            raise ValueError("outcome record: --interval must be finite, 0..5 seconds")
        if not 0 <= args.a_prime_requests <= 180:
            raise ValueError("outcome record: --a-prime-requests must be 0..180")
        action = [
            "--send-live-swing",
            "--a-prime-requests", str(args.a_prime_requests),
            "--pre-samples", str(args.pre_samples),
            "--post-samples", str(args.post_samples),
            "--settled-samples", str(args.settled_samples),
            "--interval", str(args.interval),
        ]
        if args.data_dir:
            action += ["--data-dir", args.data_dir]
        command = ["--script", "collect_outcome_transition.py"]
        if args.game:
            command += ["--game", args.game]
        if args.send_live:
            command.append("--send-live")
        # Exactly one canonical boot and one S002 shot collector. The
        # coordinator wraps the already-ready game; do not pass attach flags.
        print("S002 outcome collector: fixed direct unprimed swing by default "
              "(A primer requests=", args.a_prime_requests,
              "); pre-shot RAM reads + human labels, NOT a verified score.",
              flush=True)
        return _run(_script_command("run_golf_experiment.py",
                                   *command, "--", *action))
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
        if args.action == "inspect":
            if args.arguments:
                raise ValueError("bridge inspect takes no arguments")
            print(json.dumps(inspect_local_bridge(), indent=2, sort_keys=True))
            return 0
        if args.action == "ping":
            return _run(_script_command("probe_dolphin_bridge.py", "--read-only-live", *args.arguments))
        if args.action == "upgrade-swing":
            if args.arguments:
                raise ValueError("bridge upgrade-swing takes no arguments; close Dolphin first")
            source = ROOT.parent / "tools" / "mcp_bridge.py"
            output = ROOT.parent / "tools" / "mcp_bridge_swing.py"
            if not source.is_file():
                raise ValueError(f"Pinned original bridge not found: {source}")
            # Keep the port exclusively reserved while generating the bridge,
            # so a Dolphin bridge cannot start halfway through replacement.
            with reserve_bridge_port():
                print("Bridge port is available. Regenerating swing bridge V2 "
                      "(Dolphin must be closed).", flush=True)
                return _run(_script_command("patch_felk_bridge.py",
                            "--source", str(source), "--output", str(output),
                            "--enable-swing"))
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
