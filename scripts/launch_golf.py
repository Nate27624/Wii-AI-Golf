"""One-command local Wii Sports training launcher (Worker 1 S001).

Starts the existing savestate_session.py workflow (Dolphin --script/--exec
and an existing named checkpoint); optionally runs ONE guarded swing probe.
Game paths are prompted once and stored only in a gitignored local file.
Never captures or overwrites Dolphin savestates.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

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
        tmp.write_text(json.dumps({"schema_version": 1, "game": str(game)}, indent=2) + "\n", encoding="utf-8")
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


def make_start_command(*, game: Path, dolphin: Path, bridge: Path,
                       profile: str, catalog: Path, port: int) -> list[str]:
    if not 1 <= port <= 65535:
        raise ValueError("port must be in 1..65535")
    if not profile:
        raise ValueError("profile cannot be empty")
    for label, p in (("Dolphin", dolphin), ("swing bridge", bridge), ("state catalog", catalog)):
        if not p.is_file():
            raise ValueError(f"{label} not found: {p}")
    return [
        sys.executable, str(ROOT / "scripts" / "savestate_session.py"),
        "--catalog", str(catalog), "--port", str(port),
        "start", profile, "--dolphin", str(dolphin),
        "--bridge", str(bridge), "--game", str(game),
    ]


def make_swing_command(*, preset: str, port: int) -> list[str]:
    return [
        sys.executable, str(ROOT / "scripts" / "probe_swing.py"),
        "--preset", preset, "--port", str(port), "--send-live-swing",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One command: launch Dolphin + attach bridge + restore checkpoint")
    parser.add_argument("--game", help="First-run Wii Sports RVZ/ISO path; saved in ignored local config")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--dolphin", type=Path, default=DEFAULT_DOLPHIN)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--profile", default="green-first-shot",
                        help="Registered, previously validated savestate profile")
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--swing", action="store_true",
                        help="After startup, invoke ONE human-confirmed swing experiment")
    parser.add_argument("--preset", choices=("forward", "reverse", "sideways"), default="forward")
    args = parser.parse_args(argv)
    try:
        game = resolve_game(args.game, args.config)
        launch = make_start_command(
            game=game, dolphin=args.dolphin, bridge=args.bridge,
            profile=args.profile, catalog=args.catalog, port=args.port,
        )
        print("Starting Felk Dolphin with the swing bridge and requesting named savestate restoration...")
        print("Keep Wii Remote 1: Emulated Wii Remote; Extension: None.")
        print("Close any existing Dolphin instance before launching. This never overwrites a savestate.")
        result = subprocess.run(launch, check=False)
        if result.returncode:
            print("Launch/reset did not complete. Inspect Dolphin's Scripting log.", file=sys.stderr)
            return result.returncode
        print("Savestate load was requested; visually confirm the expected golf screen.")
        if args.swing:
            print("Starting guarded single-shot test. It waits for YOUR Enter before dispatch.")
            result = subprocess.run(make_swing_command(preset=args.preset, port=args.port), check=False)
            return result.returncode
        print("Ready. To perform one guarded swing, run: py scripts/probe_swing.py --preset forward --send-live-swing")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Golf launcher error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
