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


# Resolve the canonical source checkout BEFORE importing wii_ai_golf.
# Editable pip installs may point at a different Git worktree.
# This also works with Python -I (isolated mode) and from any CWD.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SRC = str(_REPO_ROOT / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)

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


def _early_exit_message(returncode: int) -> str:
    """Explain a native startup failure without guessing its faulting module.

    This is an output-only diagnostic. It must never restart Dolphin or
    attempt a savestate, menu input, bridge connection, or swing.
    """
    message = f"Dolphin exited before bridge preflight, code={returncode}"
    # Windows can surface the NTSTATUS as either a signed or unsigned int.
    if (returncode & 0xFFFFFFFF) == 0xC0000005:
        return (
            message + " (0xC0000005: Windows native access violation). "
            "Bridge readiness was not established; no confirmed game action. "
            "Inspect the matching Windows Application Error event (ID 1000) "
            "for faulting module and offset before attempting another shot."
        )
    return message + "; bridge readiness was not established."


def _launch(args, profile):
    game = Path(args.game).expanduser().resolve()
    exe = Path(args.dolphin).expanduser().resolve()
    script = Path(args.bridge).expanduser().resolve()
    for name, path in (("Dolphin executable", exe), ("game image", game), ("bridge script", script)):
        if not path.is_file():
            raise ValueError(f"{name} not found: {path}")
    if _connected(args.port):
        raise RuntimeError("port is already open: close existing Dolphin/bridge before start")
    command = [str(exe)]
    selected_user = getattr(args, "dolphin_user", None)
    if selected_user is not None:
        # Upstream Dolphin's -u selects this *process's* user folder. Merely
        # editing an INI through a parent process does not select it at boot.
        user_dir = Path(selected_user).expanduser().resolve()
        if not user_dir.is_dir() or not (user_dir / "Config" / "WiimoteNew.ini").is_file():
            raise ValueError("Explicit Dolphin user root lacks existing Config/WiimoteNew.ini; no launch")
        command.extend(["-u", str(user_dir)])
    command.extend(["--script", str(script), "--exec", str(game)])
    process = subprocess.Popen(command, cwd=str(exe.parent))
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(_early_exit_message(process.returncode))
        try:
            with FelkRPC(port=args.port, timeout_s=1.0) as rpc:
                outcome = StateManager(rpc).request_load(profile)
            return {"action": "launched_and_load_requested", "pid": process.pid, "state_load": outcome}
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
    start.add_argument("--dolphin-user", type=Path,
                       help="Existing Dolphin User directory (passed to Dolphin -u)")
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
