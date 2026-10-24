"""Run one real-golf experiment ONLY after a fresh, canonical Dolphin boot.

Delegates startup to scripts/launch_golf.py, which configures Emulated Wii
Remote, launches Felk Dolphin and Wii Sports, restores the EXISTING named
green-pre-start checkpoint, then dispatches the confirmed A / A+B / A intro.

Offline utilities and specialized non-first-shot checkpoints are deliberately
outside this S001 first-shot wrapper. No savestate write/overwrite happens here.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
DEFAULT_PROFILE = "green-pre-start"
# These scripts bootstrap/reset themselves or administer configuration rather
# than consume the already booted, ready-to-swing game. Double launch is unsafe.
DISALLOWED_TARGETS = frozenset({
    "run_golf_experiment.py", "launch_golf.py", "launch_hitting_green.py",
    "savestate_session.py", "start_golf_recording.py",
    "patch_felk_bridge.py", "plan_scenarios.py",
})
# Probes may load another checkpoint themselves. That would undo the menu intro.
DISALLOWED_CHILD_FLAGS = frozenset({
    "--reset-profile", "--attach-running", "--fresh",
    "--startup-profile", "--startup-slot",
})


def resolve_target(script: str, *, scripts_dir: Path = SCRIPT_DIR) -> Path:
    """Only allow Python scripts inside the canonical scripts folder.

    Future evaluation/training actions can be added under scripts/ without
    changing this dispatcher. Startup/reset/configuration scripts are blocked.
    """
    normalized = script.replace("\\", "/")
    if normalized.startswith("scripts/"):
        normalized = normalized[len("scripts/"):]
    if "/" in normalized or not re.fullmatch(r"[a-z][a-z0-9_]*\.py", normalized):
        raise ValueError("Action must be a simple scripts/*.py filename; no arbitrary paths")
    if normalized in DISALLOWED_TARGETS:
        raise ValueError(f"{normalized} launches/resets Dolphin or is not a live experiment. "
                         "Use a read-only/probe action script instead to avoid duplicate resets.")
    target = (scripts_dir / normalized).resolve()
    if not target.is_file() or target.parent != scripts_dir.resolve():
        raise ValueError(f"Action script not found in canonical scripts directory: {normalized}")
    return target


def build_commands(*, action: str, action_args: list[str],
                   game: str | None, dolphin: str | None, bridge: str | None,
                   config: str | None, catalog: str | None,
                   dolphin_user: str | None, port: int = 55355,
                   profile: str = DEFAULT_PROFILE,
                   scripts_dir: Path = SCRIPT_DIR,
                   python: str = sys.executable) -> tuple[list[str], list[str]]:
    """Validate every argument before starting Dolphin or changing any files."""
    if profile != DEFAULT_PROFILE:
        raise ValueError("This full-menu workflow requires green-pre-start; "
                         "use an explicit scenario-specific ready-state runner for other savestates")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("bridge port must be 1..65535")
    if not isinstance(action_args, list) or any(not isinstance(x, str) for x in action_args):
        raise ValueError("action_args must be a list of strings")
    if any(flag.split("=", 1)[0] in DISALLOWED_CHILD_FLAGS for flag in action_args):
        raise ValueError("Action must not launch/reset again or override the saved checkpoint")

    target = resolve_target(action, scripts_dir=scripts_dir)
    launcher = scripts_dir / "launch_golf.py"
    if not launcher.is_file():
        raise ValueError(f"Canonical launcher is missing: {launcher}")

    boot = [python, str(launcher), "--profile", profile, "--port", str(port)]
    for key, value in (("--game", game), ("--dolphin", dolphin),
                       ("--bridge", bridge), ("--config", config),
                       ("--catalog", catalog), ("--dolphin-user", dolphin_user)):
        if value is not None:
            boot.extend([key, value])

    # Honor target script's own arguments. Pass the canonical port if it
    # supports the standard --port flag (all known live bridge probes do).
    # Worker 1 made probe_swing.py self-boot by default. The dispatcher has
    # ALREADY completed launch_golf.py and its A/A+B/A navigation, so the
    # probe must explicitly consume this running session without relaunching.
    # Keep --attach-running forbidden in user-supplied action_args: only this
    # trusted post-boot handoff may inject it, never a bare user command.
    handoff_args = ["--attach-running"] if target.name == "probe_swing.py" else []
    action_command = [python, str(target), *handoff_args, *action_args]
    if not any(x == "--port" or x.startswith("--port=") for x in action_args):
        action_command.extend(["--port", str(port)])
    return boot, action_command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fresh Dolphin + named pre-start savestate + A/A+B/A intro, THEN one experiment",
        epilog=("Example: py scripts/run_golf_experiment.py --send-live "
                '--game "PATH_TO_YOUR_WII_SPORTS.wbfs" '
                "--script probe_swing.py -- --preset forward --send-live-swing"),
    )
    parser.add_argument("--send-live", action="store_true",
                        help="Explicitly opt in to fresh game boot and experiment")
    parser.add_argument("--script", required=True,
                        help="Live probe/collector script under canonical scripts/; NOT a launcher")
    parser.add_argument("--game", help="Wii Sports disc image. Omit after launch_golf.py saved it locally.")
    parser.add_argument("--dolphin", help="Override local Felk Dolphin.exe location")
    parser.add_argument("--bridge", help="Override local mcp_bridge_swing.py location")
    parser.add_argument("--config", help="Override gitignored launcher settings file")
    parser.add_argument("--catalog", help="Override canonical named-savestate catalog")
    parser.add_argument("--dolphin-user", help="Override Felk Dolphin user directory")
    parser.add_argument("--profile", default=DEFAULT_PROFILE,
                        help="Must be green-pre-start for this menu intro")
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("script_args", nargs=argparse.REMAINDER,
                        help="Action arguments after -- (for example -- --preset forward --send-live-swing)")
    args = parser.parse_args(argv)
    child_args = list(args.script_args)
    if child_args and child_args[0] == "--":
        child_args.pop(0)
    try:
        boot, action = build_commands(
            action=args.script, action_args=child_args,
            game=args.game, dolphin=args.dolphin, bridge=args.bridge,
            config=args.config, catalog=args.catalog,
            dolphin_user=args.dolphin_user, port=args.port,
            profile=args.profile,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print("STARTUP: fresh Felk Dolphin -> existing green-pre-start savestate -> "
          "calibrated A / A+B / A intro -> requested experiment.", flush=True)
    print("Existing Dolphin must be closed; do not run an additional bridge.", flush=True)
    if not args.send_live:
        print(f"DRY RUN boot: {boot!r}")
        print(f"DRY RUN action: {action!r}")
        print("No Dolphin process launched and no controller input sent.")
        return 0

    result = subprocess.run(boot, cwd=ROOT, check=False)
    if result.returncode:
        print("Canonical Dolphin boot/intro failed; live action NOT started.", file=sys.stderr)
        return result.returncode
    print("Startup dispatch completed (screen readiness still requires observation).", flush=True)
    result = subprocess.run(action, cwd=ROOT, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
