"""Reusable named Dolphin savestate capture/reset/launch workflow.

All names/paths are local and do not leak into git. For multi-game use, give
separate catalogs or separate Dolphin --user directories to avoid slot reuse.
"""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.savestates import MAX_SLOT, StateCatalog, StateManager, StateProfile

DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "research" / "savestates.local.json"


def _reply(data):
    print(json.dumps(data, indent=2))


def _connected(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _launch(args, profile):
    game = Path(args.game).expanduser().resolve()
    exe = Path(args.dolphin).expanduser().resolve()
    script = Path(args.bridge).expanduser().resolve()
    for name, path in (("Dolphin executable", exe), ("game image", game), ("bridge script", script)):
        if not path.is_file():
            raise ValueError(f"{name} not found: {path}")
    if _connected(args.port):
        raise RuntimeError("port is already open: close existing Dolphin/bridge before start")
    process = subprocess.Popen([str(exe), "--script", str(script), "--exec", str(game)], cwd=str(exe.parent))
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Dolphin exited before bridge preflight, code={process.returncode}")
        try:
            with FelkRPC(port=args.port, timeout_s=1.0) as rpc:
                outcome = StateManager(rpc).request_load(profile)
            return {"action": "launched_and_load_requested", "pid": process.pid, **outcome}
        except (OSError, TimeoutError):
            time.sleep(0.25)
    raise TimeoutError("Dolphin launched but bridge did not respond within timeout; inspect Scripting log")


def main():
    parser = argparse.ArgumentParser(description="Named, reusable Felk savestate workflow")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--port", type=int, default=55355)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="Display locally registered savestate profiles")
    register = sub.add_parser("register", help="Label an existing Dolphin savestate slot; no emulator write")
    register.add_argument("name")
    register.add_argument("--slot", type=int, required=True, choices=range(MAX_SLOT + 1), metavar=f"0..{MAX_SLOT}")
    register.add_argument("--description", default="")
    register.add_argument("--game-id", default="")
    capture = sub.add_parser("capture", help="Save current game into registered slot (destructive)")
    capture.add_argument("name")
    capture.add_argument("--overwrite-slot", action="store_true", required=False)
    reset = sub.add_parser("reset", help="Request load of a named savestate in running Dolphin")
    reset.add_argument("name")
    start = sub.add_parser("start", help="Launch Dolphin + bridge + game then restore a registered state")
    start.add_argument("name")
    start.add_argument("--dolphin", required=True)
    start.add_argument("--game", required=True)
    start.add_argument("--bridge", required=True)
    start.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1..65535")
    catalog = StateCatalog(args.catalog)
    if args.command == "list":
        _reply({"catalog": str(args.catalog), "profiles": [vars(p) for p in catalog.profiles.values()]})
        return
    if args.command == "register":
        catalog.add(StateProfile(args.name, args.slot, args.description, args.game_id))
        catalog.save()
        _reply({"action": "registered", "name": args.name, "slot": args.slot,
                "warning": "Registration only labels a slot; it does not create a Dolphin savestate"})
        return
    profile = catalog.get(args.name)
    if args.command == "start":
        if args.timeout <= 0:
            parser.error("timeout must be positive")
        _reply(_launch(args, profile))
        return
    with FelkRPC(port=args.port) as rpc:
        manager = StateManager(rpc)
        if args.command == "capture":
            _reply(manager.request_capture(profile, allow_overwrite=args.overwrite_slot))
        elif args.command == "reset":
            _reply(manager.request_load(profile))


if __name__ == "__main__":
    try:
        main()
    except (OSError, TimeoutError, ValueError, RuntimeError) as exc:
        print(f"savestate workflow error: {exc}", file=sys.stderr)
        sys.exit(1)
