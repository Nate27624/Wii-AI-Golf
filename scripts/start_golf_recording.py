"""Start a golf motion capture using the integrator's EXACT savestate + A/A+B/A intro.

Delegates ALL boot/navigation to canonical scripts/launch_hitting_green.py.
No duplicated menu-frame constants. Never sends a swing automatically.
Designed for the sibling Wii-AI-Golf-Data evaluation worktree.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys

EVALUATION_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANONICAL = (
    EVALUATION_ROOT if EVALUATION_ROOT.name.casefold() == "wii-ai-golf"
    else EVALUATION_ROOT.parent / "Wii-AI-Golf"
)
DEFAULT_DOLPHIN = DEFAULT_CANONICAL.parent / "tools" / "FelkDolphin" / "Dolphin.exe"
DEFAULT_BRIDGE = DEFAULT_CANONICAL.parent / "tools" / "mcp_bridge_swing.py"
SCAN_SCRIPT = EVALUATION_ROOT / "scripts" / "discover_golf_motion.py"


def bridge_open(port: int) -> bool:
    """Connectivity only, NOT proof that the expected bridge is running."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def boot_command(*, canonical: Path, profile: str, port: int,
                 attach_running: bool, dolphin: Path | None = None,
                 bridge: Path | None = None,
                 game: Path | None = None) -> list[str]:
    """Reuse the integrator's launcher, including its exact current defaults."""
    launcher = canonical / "scripts" / "launch_hitting_green.py"
    catalog = canonical / "research" / "savestates.local.json"
    if not launcher.is_file():
        raise FileNotFoundError(
            f"Integrator's launcher missing: {launcher}. "
            "Update your canonical Wii-AI-Golf checkout first."
        )
    if not catalog.is_file():
        raise FileNotFoundError(
            f"Canonical named-savestate catalog missing: {catalog}. "
            "Run savestate_session.py list/register from canonical checkout."
        )
    cmd = [
        sys.executable, str(launcher),
        "--profile", profile, "--catalog", str(catalog),
        "--port", str(port), "--send-live",
    ]
    if attach_running:
        cmd.append("--attach-running")
    else:
        if dolphin is None or bridge is None or game is None:
            raise ValueError("fresh launch requires --dolphin, --bridge and --game")
        for name, path in (("Dolphin", dolphin), ("bridge", bridge), ("game", game)):
            if not path.is_file():
                raise FileNotFoundError(f"{name} not found: {path}")
        cmd.extend(["--dolphin", str(dolphin), "--bridge", str(bridge),
                    "--game", str(game)])
    # Deliberately omit --swing. The user/modeling agent owns swing timing.
    return cmd


def scan_command(*, seconds: float, interval: float, profile: str,
                 port: int, no_upload: bool) -> list[str]:
    cmd = [
        sys.executable, str(SCAN_SCRIPT),
        "--seconds", str(seconds), "--interval", str(interval),
        "--profile", profile, "--port", str(port),
    ]
    if no_upload:
        cmd.append("--no-upload")
    return cmd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--attach-running", action="store_true",
                      help="reset pre-start checkpoint in currently running Dolphin (default)")
    mode.add_argument("--fresh", action="store_true",
                      help="launch Dolphin with swing-enabled bridge, then restore checkpoint")
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL,
                        help="canonical integration checkout containing local savestate catalog")
    parser.add_argument("--savestate-profile", default="green-pre-start",
                        help="existing PRE-START menu savestate, NOT first-ball checkpoint")
    parser.add_argument("--game", type=Path, help="required for --fresh")
    parser.add_argument("--dolphin", type=Path, default=DEFAULT_DOLPHIN)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--interval", type=float, default=0.6)
    parser.add_argument("--scan-profile", choices=("fast", "broad"), default="fast")
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args(argv)

    if not 1 <= args.port <= 65535:
        parser.error("port must be 1..65535")
    if not 5 <= args.seconds <= 180 or not 0.2 <= args.interval <= 10:
        parser.error("seconds must be 5..180 and interval 0.2..10")
    if not args.savestate_profile or "/" in args.savestate_profile or "\\" in args.savestate_profile:
        parser.error("use a registered savestate profile name")
    if not SCAN_SCRIPT.is_file():
        raise FileNotFoundError(f"Evaluation scanner not found: {SCAN_SCRIPT}")

    attach = not args.fresh
    if attach and not bridge_open(args.port):
        raise ConnectionError(
            "No bridge listening at 127.0.0.1:"
            f"{args.port}. Start Felk Dolphin with its scripting bridge, "
            "or use --fresh --game PATH after closing Dolphin."
        )
    if args.fresh and bridge_open(args.port):
        raise RuntimeError(
            "A bridge is already listening. Use --attach-running, "
            "or close Dolphin before --fresh. Never start two bridges."
        )

    # Fail before sending input if the launcher/catalog/profile is missing.
    from wii_ai_golf.integration.savestates import StateCatalog
    catalog = args.canonical / "research" / "savestates.local.json"
    if not catalog.is_file():
        raise FileNotFoundError(f"Missing canonical savestate catalog: {catalog}")
    StateCatalog(catalog).get(args.savestate_profile)
    command = boot_command(
        canonical=args.canonical, profile=args.savestate_profile,
        port=args.port, attach_running=attach,
        dolphin=args.dolphin, bridge=args.bridge, game=args.game,
    )
    print("Using integrator-owned launch_hitting_green.py for existing savestate restore")
    print("and its established A -> wait -> A+B -> release -> A -> settle sequence.")
    print("No extra savestate loads or menu presses will be sent by the evaluation scanner.")
    boot_env = dict(os.environ, PYTHONPATH=str(args.canonical / "src"))
    status = subprocess.run(command, cwd=args.canonical, env=boot_env, check=False)
    if status.returncode:
        print("Integrator launcher failed; memory recording NOT started.", file=sys.stderr)
        return status.returncode

    print("Menu input requests completed. Check that the golfer is actually at the ball.")
    print("Recording starts now: swing manually when ready. Ctrl+C saves/uploads early.")
    scan_env = dict(os.environ, PYTHONPATH=str(EVALUATION_ROOT / "src"))
    status = subprocess.run(
        scan_command(seconds=args.seconds, interval=args.interval,
                     profile=args.scan_profile, port=args.port,
                     no_upload=args.no_upload),
        cwd=EVALUATION_ROOT, env=scan_env, check=False,
    )
    return status.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Golf capture startup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
