"""Auto-enter Hitting the Green via canonical repo launcher, no shot.

This thin wrapper calls the MAIN checkout's existing scripts/launch_golf.py
--profile green-pre-start, which restores the existing named save and
dispatches A, A+B, A. It performs NO swing or save-state write.

The ignored launch and savestate catalog config are kept in the MAIN
checkout, not copied to the research worktree. A named slot does NOT
prove the clean portable Dolphin User contains the save bytes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "Wii-AI-Golf"
CLEAN = ROOT / "tools" / "FelkDolphin-Clean"
KNOWN_CLEAN_BRIDGE = ROOT / "tools" / "mcp_bridge_swing_legacy_eval.py"
PROFILE = "green-pre-start"


def _read_catalog(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Main savestate catalog schema is invalid")
    profiles = data.get("profiles")
    if not isinstance(profiles, list):
        raise ValueError("Main savestate profiles are not registered")
    matching = [p for p in profiles
                if isinstance(p, dict) and p.get("name") == PROFILE]
    if len(matching) != 1 or type(matching[0].get("slot")) is not int or not 0 <= matching[0]["slot"] <= 99:
        raise ValueError("green-pre-start is NOT registered in main local savestate catalog")
    return matching[0]["slot"]


def _read_game(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Main local launch config schema invalid")
    game = data.get("game")
    if not isinstance(game, str) or not game:
        raise ValueError("No saved game path in the MAIN checkout")
    file = Path(game).expanduser()
    if not file.is_file() or file.suffix.lower() not in (
            ".rvz", ".iso", ".wbfs", ".gcz", ".wia", ".gcm", ".ciso"):
        raise ValueError("Main checkout saved Wii Sports game missing or unsupported")
    return file


def build_command(*, main=MAIN, clean=CLEAN, bridge=KNOWN_CLEAN_BRIDGE,
                  port=55355):
    main, clean, bridge = Path(main), Path(clean), Path(bridge)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Bad local bridge port")
    launch = main / "scripts" / "launch_golf.py"
    config = main / "research" / "launch.local.json"
    catalog = main / "research" / "savestates.local.json"
    exe = clean / "Dolphin.exe"
    user = clean / "User"
    ini = user / "Config" / "WiimoteNew.ini"
    for label, p in (
            ("canonical launcher", launch),
            ("main local game config", config),
            ("main local savestate catalog", catalog),
            ("clean Dolphin executable", exe),
            ("clean portable Wii Remote config", ini),
            ("selected previously successful startup bridge", bridge),
            ("clean portable.txt", clean / "portable.txt")):
        if not p.is_file():
            raise ValueError(f"Missing {label}: no Dolphin was started")
    game = _read_game(config)
    slot = _read_catalog(catalog)
    command = [
        sys.executable, str(launch), "--profile", PROFILE,
        "--config", str(config), "--catalog", str(catalog),
        "--dolphin", str(exe), "--dolphin-user", str(user),
        "--bridge", str(bridge), "--port", str(port),
    ]
    return command, {
        "profile": PROFILE,
        "slot": slot,
        "main_local_game_present": game.is_file(),
        "clean_portable_controller_config_present": True,
        "clean_portable_install_present": True,
        "live_savestate_bytes_independently_verified": False,
        "no_swing_requested": True,
    }


def _port_in_use(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.35):
            return True
    except OSError:
        return False


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--main-repo", type=Path, default=MAIN)
    p.add_argument("--clean-dolphin", type=Path, default=CLEAN)
    p.add_argument("--bridge", type=Path, default=KNOWN_CLEAN_BRIDGE)
    p.add_argument("--port", type=int, default=55355)
    p.add_argument("--dry-run", action="store_true",
                   help="Check only, without launching Dolphin")
    args = p.parse_args(argv)
    try:
        command, checks = build_command(
            main=args.main_repo, clean=args.clean_dolphin,
            bridge=args.bridge, port=args.port)
        if _port_in_use(args.port):
            raise ValueError(
                "A Dolphin bridge is already running. Do not boot a second "
                "process; close existing Dolphin normally or use the "
                "canonical attach-running intro with explicit operator intent.")
        print(json.dumps({
            "kind": "local_golf_shot_study_autolaunch",
            "checks": checks,
            "dry_run": bool(args.dry_run),
            "action": "restore_green_pre_start_and_dispatch_A_AplusB_A",
            "requires_visual_ready_to_swing_confirmation": True,
            "launches_canonical_main_checkout": True,
            "note": ("The clean portable User may not contain the previously "
                     "registered state slot. If restoration fails, inspect "
                     "saved states; never pretend the intro succeeded.")
        }, indent=2, sort_keys=True), flush=True)
        if args.dry_run:
            return 0
        completed = subprocess.run(command, check=False, cwd=str(args.main_repo))
        return completed.returncode
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Golf study auto-intro REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
