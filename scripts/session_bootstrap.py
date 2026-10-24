"""Common launch contract for ALL live S002 data-capture CLIs.

Run the integrator-owned canonical launch_hitting_green.py exactly once:
existing named green-pre-start savestate -> A -> A+B -> A -> settle.
Never synthesize menu timings or send an automatic golf swing here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT if ROOT.name.casefold() == "wii-ai-golf" else ROOT.parent / "Wii-AI-Golf"
DEFAULT_DOLPHIN = CANONICAL.parent / "tools" / "FelkDolphin" / "Dolphin.exe"
DEFAULT_BRIDGE = CANONICAL.parent / "tools" / "mcp_bridge_swing.py"


def bridge_open(port: int) -> bool:
    """Connectivity test, not proof of correct bridge/game mode."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def add_boot_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--startup", choices=("auto", "fresh", "attach", "skip"), default="auto",
        help="DEFAULT auto: attach if bridge exists, otherwise launch Dolphin; skip is explicit",
    )
    parser.add_argument("--canonical", type=Path, default=CANONICAL)
    parser.add_argument("--prestart-profile", default="green-pre-start")
    parser.add_argument("--game", type=Path,
                        help="owned Wii Sports image; otherwise read canonical local launch settings")
    parser.add_argument("--dolphin", type=Path, default=DEFAULT_DOLPHIN)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)


def game_from_local_settings(canonical: Path) -> Path | None:
    """Use existing gitignored settings produced by the integration launcher."""
    file = canonical / "research" / "launch.local.json"
    if not file.is_file():
        return None
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("game"), str):
        return None
    path = Path(data["game"])
    return path if path.is_file() else None


def boot_command(*, canonical: Path, profile: str, port: int, attach: bool,
                 dolphin: Path | None = None, bridge: Path | None = None,
                 game: Path | None = None) -> list[str]:
    """Delegate the savestate and exact A/A+B/A sequence to Worker 1."""
    launcher = canonical / "scripts" / "launch_hitting_green.py"
    catalog = canonical / "research" / "savestates.local.json"
    if not launcher.is_file():
        raise FileNotFoundError(
            "Canonical launch_hitting_green.py is missing; update the main checkout."
        )
    if not catalog.is_file():
        raise FileNotFoundError(
            "Canonical savestate catalog missing; register the pre-start checkpoint first."
        )
    cmd = [
        sys.executable, str(launcher),
        "--profile", profile, "--catalog", str(catalog),
        "--port", str(port), "--send-live",
    ]
    if attach:
        return cmd + ["--attach-running"]
    for label, path in (("Dolphin executable", dolphin),
                        ("Felk swing bridge", bridge), ("Wii Sports game image", game)):
        if path is None or not path.is_file():
            raise FileNotFoundError(
                f"{label} missing: {path}. Use --game PATH if needed; "
                "do not launch a second Dolphin or invent an emulator path."
            )
    return cmd + ["--dolphin", str(dolphin),
                  "--bridge", str(bridge), "--game", str(game)]


def dolphin_process_running() -> bool:
    """Windows duplicate-emulator guard if an old Dolphin lacks its bridge."""
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Dolphin.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        return result.returncode == 0 and '"Dolphin.exe"' in result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def prepare_emulated_remote(canonical: Path, dolphin: Path) -> dict:
    """Reuse Worker 1's fail-closed Dolphin controller preparation, not a copy."""
    module_path = canonical / "src" / "wii_ai_golf" / "integration" / "dolphin_controller_config.py"
    if not module_path.is_file():
        raise FileNotFoundError("Canonical emulated-controller helper is missing: " + str(module_path))
    spec = importlib.util.spec_from_file_location("_wii_golf_canonical_remote", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load canonical Wii Remote configuration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    local = canonical / "research" / "launch.local.json"
    user_dir = None
    if local.is_file():
        try:
            config = json.loads(local.read_text(encoding="utf-8"))
            path = config.get("dolphin_user") if isinstance(config, dict) else None
            if isinstance(path, str) and path.strip():
                user_dir = Path(path)
        except (OSError, ValueError):
            pass
    state = module.ensure_emulated_controller(dolphin, user_dir=user_dir)
    print("Controller prepared:", state["source"], "| Extension:", state["extension"])
    return state


def ensure_intro(args: argparse.Namespace) -> str:
    """Perform exactly one canonical savestate restore and menu navigation.

    The default 'auto' mode fixes ConnectionRefusedError by starting Dolphin
    when no bridge exists. Does not start data capture until boot succeeds.
    """
    startup = getattr(args, "startup", "auto")
    if startup == "skip":
        print("Explicit --startup skip: game must ALREADY be ready to swing.")
        return "skipped"
    port = args.port
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Felk RPC port must be 1..65535")
    canonical = Path(args.canonical)
    catalog = canonical / "research" / "savestates.local.json"
    profile = args.prestart_profile
    # Import from THIS worktree while relying on canonical catalog data.
    from wii_ai_golf.integration.savestates import StateCatalog
    StateCatalog(catalog).get(profile)
    listening = bridge_open(port)
    if startup == "attach" and not listening:
        raise ConnectionError("No Felk bridge; use --startup auto to launch Dolphin.")
    if startup == "fresh" and listening:
        raise RuntimeError("A Felk bridge is already running; use --startup auto.")
    attach = listening if startup == "auto" else startup == "attach"
    if not attach and dolphin_process_running():
        raise RuntimeError(
            "Dolphin.exe is already running without a responsive bridge. "
            "Close it before the automatic fresh launch to avoid two instances."
        )
    game = args.game or game_from_local_settings(canonical)
    command = boot_command(
        canonical=canonical, profile=profile, port=port, attach=attach,
        dolphin=args.dolphin, bridge=args.bridge, game=game,
    )
    if not attach:
        # Same existing safety logic as canonical launch_golf.py, before boot.
        prepare_emulated_remote(canonical, args.dolphin)
    print("STANDARD GOLF INTRO:", "attach" if attach else "fresh Felk Dolphin")
    print("Restore named pre-start state -> A -> wait -> A+B -> release -> A -> settle")
    print("Using integrator-owned timing; NO second restore and NO automatic swing.")
    environment = dict(os.environ, PYTHONPATH=str(canonical / "src"))
    result = subprocess.run(command, cwd=canonical, env=environment, check=False)
    if result.returncode:
        raise RuntimeError(
            f"Canonical intro launcher failed with exit code {result.returncode}; "
            "no observations were recorded."
        )
    print("Intro dispatched. Verify visually that the golfer is at the first ball.")
    return "attached" if attach else "launched"
