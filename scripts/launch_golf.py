"""One-command local Wii Sports training launcher (Worker 1 S001).

Delegates to launch_hitting_green.py, which launches Dolphin, loads the
existing green-pre-start state, then executes the user-verified A -> A+B -> A
intro sequence. Optionally runs ONE human-confirmed swing probe.
Game paths are prompted once and stored only in a gitignored local file.
Never captures or overwrites Dolphin savestates.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path
import subprocess
import sys


# Resolve the canonical source checkout BEFORE importing wii_ai_golf.
# Editable pip installs may point at a different Git worktree.
# This also works with Python -I (isolated mode) and from any CWD.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SRC = str(_REPO_ROOT / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)

from wii_ai_golf.integration.post_boot import post_boot_action_args
from wii_ai_golf.integration.savestates import MAX_SLOT, StateCatalog
from wii_ai_golf.integration.dolphin_controller_config import (
    ControllerConfigError, ensure_emulated_controller,
)

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT.parent / "tools"
CONFIG = ROOT / "research" / "launch.local.json"
CATALOG = ROOT / "research" / "savestates.local.json"
DEFAULT_DOLPHIN = TOOLS / "FelkDolphin" / "Dolphin.exe"
DEFAULT_BRIDGE = TOOLS / "mcp_bridge_swing.py"
GAME_EXTENSIONS = {".rvz", ".iso", ".wbfs", ".gcz", ".wia", ".gcm", ".ciso"}


def game_path(text: str) -> Path:
    raw = text.strip().strip('"').strip("'")
    if not raw:
        raise ValueError("game image path is blank")
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"game image not found: {path}")
    if path.suffix.lower() not in GAME_EXTENSIONS:
        raise ValueError(f"unexpected disc image extension: {path.suffix}")
    return path


def read_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("game"), str):
        raise ValueError("unsupported launch configuration; expected schema_version 1 and a game string")
    return value


def save_game(path: Path, game: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        # Preserve an operator-selected checkpoint when --game replaces the image path.
        old = read_config(path)
        updated = {"schema_version": 1, "game": str(game)}
        for key in ("profile", "dolphin_user"):
            if isinstance(old.get(key), str):
                updated[key] = old[key]
        tmp.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def resolve_game(game_arg: str | None, config: Path, *, prompt=input) -> Path:
    if game_arg:
        value = game_path(game_arg)
        save_game(config, value)
        return value
    saved = read_config(config).get("game")
    if saved:
        return game_path(saved)
    print("One-time setup: paste the full path to your Wii Sports .rvz/.iso disc image.")
    print(f"It will be saved locally in {config} (gitignored, never uploaded).")
    return_value = prompt("Game file path: ")
    value = game_path(return_value)
    save_game(config, value)
    return value

def resolve_profile(profile_arg: str | None, slot_arg: int | None,
                    config: Path, catalog_path: Path):
    """Require a registered profile and persist operator's selection locally.

    --slot resolves via the StateCatalog; it never blindly writes/loads an
    unnamed slot and never captures a new savestate.
    """
    catalog = StateCatalog(catalog_path)
    if slot_arg is not None:
        if not 0 <= slot_arg <= MAX_SLOT:
            raise ValueError(f"slot must be between 0 and {MAX_SLOT}")
        matches = [p for p in catalog.profiles.values() if p.slot == slot_arg]
        if not matches:
            raise ValueError(
                f"slot {slot_arg} is not registered in {catalog_path}; "
                "register it first with savestate_session.py"
            )
        selected = matches[0].name
    elif profile_arg:
        selected = profile_arg
    else:
        selected = read_config(config).get("profile") or "green-pre-start"

    profile = catalog.get(selected)
    # Only the operator's explicit --slot/--profile overrides the saved choice.
    if slot_arg is not None or profile_arg is not None:
        value = read_config(config)
        if not value.get("game"):
            raise ValueError("game must be configured before selecting the checkpoint")
        value["profile"] = profile.name
        temp = config.with_name(config.name + ".tmp")
        try:
            temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            os.replace(temp, config)
        finally:
            if temp.exists():
                temp.unlink()
    return profile


def remember_dolphin_user(config: Path, selected: str) -> None:
    """Persist an explicit user folder without erasing game/profile settings."""
    value = read_config(config)
    if not value.get("game"):
        raise ValueError("save the game path before choosing a Dolphin user folder")
    value["dolphin_user"] = selected
    temp = config.with_name(config.name + ".tmp")
    try:
        temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, config)
    finally:
        if temp.exists():
            temp.unlink()


def is_bridge_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def require_portable_user_root_match(dolphin: Path, user_dir: Path | None) -> None:
    """Reject config edits that portable Dolphin cannot use.

    portable.txt selects <Dolphin executable folder>/User independently of
    an explicit or remembered --dolphin-user path. This is a pre-boot
    consistency check, NOT proof that a native Dolphin process started.
    """
    if user_dir is None:
        return
    exe = Path(dolphin).expanduser().resolve()
    if not (exe.parent / "portable.txt").exists():
        return
    if Path(user_dir).expanduser().resolve() != (exe.parent / "User").resolve():
        raise ControllerConfigError(
            "Portable Dolphin user-root mismatch: the selected --dolphin-user "
            "(or remembered folder) differs from the executable's portable "
            "User folder. No controller INI was changed and Dolphin was not "
            "launched. Select that portable User folder before retrying."
        )


def make_start_command(*, game: Path, dolphin: Path, bridge: Path,
                       profile: str, catalog: Path, port: int) -> list[str]:
    if not 1 <= port <= 65535:
        raise ValueError("port must be in 1..65535")
    if profile != "green-pre-start":
        raise ValueError("Standard gameplay intro requires green-pre-start; "
                         "use --profile green-pre-start (or --slot for its registered slot). "
                         "For advanced at-ball checkpoints, use savestate_session.py directly.")
    for label, p in (("Dolphin", dolphin), ("swing bridge", bridge), ("state catalog", catalog)):
        if not p.is_file():
            raise ValueError(f"{label} not found: {p}")
    return [
        sys.executable, str(ROOT / "scripts" / "launch_hitting_green.py"),
        "--catalog", str(catalog), "--port", str(port),
        "--profile", profile, "--dolphin", str(dolphin),
        "--bridge", str(bridge), "--game", str(game),
        "--send-live",
    ]


def make_swing_command(*, preset: str, port: int,
                       follow_through_frames: int = 30, remote: int = 0,
                       report: Path | None = None,
                       a_setup_frames: int = 12,
                       a_prime_frames: int = 60) -> list[str]:
    """The launcher ALREADY ran the intro; child must explicitly attach.

    Without --attach-running the probe would invoke launch_golf again,
    causing recursion and/or a second Dolphin process.
    """
    if not 0 <= follow_through_frames <= 180:
        raise ValueError("follow_through_frames must be between 0 and 180")
    if type(a_setup_frames) is not int or not 1 <= a_setup_frames <= 180:
        raise ValueError("a_setup_frames must be between 1 and 180")
    if type(a_prime_frames) is not int or not 0 <= a_prime_frames <= 180:
        raise ValueError("a_prime_frames must be between 0 and 180")
    if remote not in range(4):
        raise ValueError("remote must be 0..3")
    cmd = [
        sys.executable, str(ROOT / "scripts" / "probe_swing.py"),
        *post_boot_action_args("probe_swing.py", []), "--preset", preset, "--port", str(port),
        "--follow-through-frames", str(follow_through_frames),
        "--a-setup-frames", str(a_setup_frames),
        "--a-prime-frames", str(a_prime_frames),
        "--remote", str(remote), "--send-live-swing",
    ]
    if report is not None:
        cmd += ["--report", str(report)]
    return cmd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One command: launch Dolphin, restore green-pre-start, navigate A -> A+B -> A intro")
    parser.add_argument("--game", help="First-run Wii Sports RVZ/ISO path; saved in ignored local config")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--dolphin", type=Path, default=DEFAULT_DOLPHIN)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--dolphin-user", type=Path,
                        help="One-time Dolphin user folder override; remembered locally")
    checkpoint = parser.add_mutually_exclusive_group()
    checkpoint.add_argument("--profile", help="Select and remember registered checkpoint by name")
    checkpoint.add_argument("--slot", type=int, help="Select and remember a REGISTERED savestate slot, e.g. 2")
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--swing", action="store_true",
                        help="After validated intro dispatch, prompt for ONE human-confirmed swing experiment")
    parser.add_argument("--preset", choices=("forward", "reverse", "sideways"), default="forward")
    parser.add_argument("--follow-through-frames", type=int, default=30,
                        help="Extra frames holding A through swing (0..180, default 30)")
    parser.add_argument("--a-setup-frames", type=int, default=12,
                        help="Neutral A-held samples inside the swing trace (1..180; known-good 12)")
    parser.add_argument("--a-prime-frames", type=int, default=60,
                        help="Separate button-only A press requests BEFORE swing API (0..180, default 60)")
    parser.add_argument("--remote", type=int, choices=range(4), default=0)
    parser.add_argument("--report", type=Path,
                        help="Optional local JSONL observation path, passed to guarded swing child")
    args = parser.parse_args(argv)
    if not 0 <= args.follow_through_frames <= 180:
        parser.error("--follow-through-frames must be 0..180")
    if not 1 <= args.a_setup_frames <= 180:
        parser.error("--a-setup-frames must be 1..180")
    if not 0 <= args.a_prime_frames <= 180:
        parser.error("--a-prime-frames must be 0..180")
    try:
        game = resolve_game(args.game, args.config)
        profile = resolve_profile(args.profile, args.slot, args.config, args.catalog)
        if args.swing:
            # Prevent a normal full boot/menu sequence when the generated bridge
            # still invokes set_wiimote_swing on idle frames. Verify source
            # marker before touching Dolphin or controller settings.
            from wii_ai_golf.integration.swing_patch import SWING_NEUTRAL_V2_MARKER
            bridge_text = args.bridge.read_text(encoding="utf-8") if args.bridge.is_file() else ""
            if SWING_NEUTRAL_V2_MARKER not in bridge_text:
                raise ValueError(
                    "Swing bridge V2 not installed. Close Dolphin, run "
                    "'py scripts/golf.py bridge upgrade-swing', then retry. "
                    "The upgrade keeps a backup of the previous generated bridge."
                )
        print(f"Selected checkpoint: {profile.name} (Dolphin slot {profile.slot})")
        if profile.description:
            print(f"Checkpoint description: {profile.description}")
        launch = make_start_command(
            game=game, dolphin=args.dolphin, bridge=args.bridge,
            profile=profile.name, catalog=args.catalog, port=args.port,
        )
        if is_bridge_port_open(args.port):
            raise ValueError(
                "Felk bridge port is already occupied. Close Dolphin before "
                "updating the controller configuration or starting a new game."
            )
        remembered = read_config(args.config).get("dolphin_user")
        selected_user = args.dolphin_user or (Path(remembered) if remembered else None)
        # Do not modify a different INI than portable Dolphin will actually read.
        require_portable_user_root_match(args.dolphin, selected_user)
        controller = ensure_emulated_controller(args.dolphin, user_dir=selected_user)
        print("Controller ready BEFORE boot:", controller["source"],
              "| Extension:", controller["extension"])
        print("Dolphin user config:", controller["ini"])
        print("Controller config updated:", controller["changed"])
        if controller["backup"]:
            print("Original controller backup:", controller["backup"])
        if args.dolphin_user:
            remember_dolphin_user(args.config, controller["user_dir"])
        print("Starting Felk Dolphin, restoring green-pre-start, and dispatching calibrated A / A+B / A intro...")
        print("Keep Wii Remote 1: Emulated Wii Remote; Extension: None.")
        print("Close any existing Dolphin instance before launching. This never overwrites a savestate.")
        result = subprocess.run(launch, check=False)
        if result.returncode:
            print("Launch/reset did not complete. Inspect Dolphin's Scripting log.", file=sys.stderr)
            return result.returncode
        print("Calibrated intro dispatched; visually confirm the golfer reached the ready-to-swing screen.")
        if args.swing:
            print("Starting guarded single-shot test. It waits for YOUR Enter before dispatch.")
            result = subprocess.run(make_swing_command(
                preset=args.preset, port=args.port,
                follow_through_frames=args.follow_through_frames,
                a_setup_frames=args.a_setup_frames,
                a_prime_frames=args.a_prime_frames,
                remote=args.remote, report=args.report), check=False)
            return result.returncode
        print("Intro complete (screen not machine-verified). For the next full session, run "
              "py scripts/launch_golf.py --swing. Do NOT assume a standalone probe "
              "has a running bridge unless using --attach-running explicitly.")
        return 0
    except (OSError, ValueError, ControllerConfigError, json.JSONDecodeError) as exc:
        print(f"Golf launcher error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
