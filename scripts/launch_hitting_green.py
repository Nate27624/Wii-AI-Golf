"""Launch Wii Sports, restore existing pre-start state, navigate to swing.

Opt-in only; no savestate creation/overwrite and no game assets committed.
Use Felk Dolphin with Emulated Wii Remote 1, Extension None.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
import time

# Resolve this checkout's source before any wii_ai_golf import. A pip editable
# installation may otherwise point to an older branch/worktree.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SRC = str(_REPO_ROOT / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)
# Python -I excludes the sibling scripts/ directory from sys.path too.
# Reuse the actual launcher and probe modules from THIS checkout instead of
# relying on CWD, PYTHONPATH or a stale editable installation.
_LOCAL_SCRIPTS = str(_REPO_ROOT / "scripts")
if _LOCAL_SCRIPTS in sys.path:
    sys.path.remove(_LOCAL_SCRIPTS)
sys.path.insert(0, _LOCAL_SCRIPTS)

from wii_ai_golf.operator_dialogs import operator_input
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.savestates import StateCatalog, StateManager
from wii_ai_golf.integration.swing_client import SwingTraceClient
from wii_ai_golf.menu_sequence import planned_menu_phases, execute_menu_phases

# These scripts live alongside this entry point; reuse the existing
# launcher and swing presets instead of duplicating their implementations.
from savestate_session import _launch
from probe_swing import build_probe

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "research" / "savestates.local.json"
DEFAULT_BRIDGE = ROOT.parent / "tools" / "mcp_bridge_swing.py"


def _healthy_connection(port: int, timeout: float) -> FelkRPC:
    """Wait for live frame-progressing bridge after a savestate load."""
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        rpc = FelkRPC(port=port, timeout_s=2.0)
        try:
            rpc.connect()
            ping = rpc.call("bridge.ping")
            if not isinstance(ping, dict) or not isinstance(ping.get("bridge_version"), str):
                raise RuntimeError("unexpected Felk bridge ping")
            first = rpc.call("frame.get_count")
            second = rpc.call("frame.get_count")
            if not isinstance(first, int) or not isinstance(second, int) or second <= first:
                raise RuntimeError("Dolphin frames are not advancing")
            return rpc
        except (OSError, TimeoutError, RuntimeError, ValueError) as exc:
            last_error = exc
            rpc.close()
            time.sleep(0.25)
    raise TimeoutError(f"Bridge not ready after savestate load: {last_error}")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Launch Wii Sports, load existing pre-start savestate, navigate A > A+B > A")
    p.add_argument("--profile", default="green-pre-start",
                   help="Existing profile name from savestates.local.json; never overwritten")
    p.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    p.add_argument("--dolphin", type=Path, help="Felk Dolphin.exe path (for a fresh launch)")
    p.add_argument("--dolphin-user", type=Path,
                   help="Existing Dolphin User directory selected by the parent launcher")
    p.add_argument("--game", type=Path, help="Legally owned Wii Sports disc-image path")
    p.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE,
                   help="Existing swing-enabled bridge; do not use a --startup-profile bridge")
    p.add_argument("--attach-running", action="store_true",
                   help="Use existing responsive Dolphin instead of launching another instance")
    p.add_argument("--port", type=int, default=55355)
    p.add_argument("--remote", type=int, choices=range(4), default=0)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--startup-frames", type=int, default=120)
    p.add_argument("--first-a-frames", type=int, default=30)
    p.add_argument("--wait-frames", type=int, default=315)
    p.add_argument("--ab-frames", type=int, default=60)
    p.add_argument("--gap-frames", type=int, default=135)
    p.add_argument("--last-a-frames", type=int, default=45)
    p.add_argument("--settle-frames", type=int, default=300)
    p.add_argument("--send-live", action="store_true",
                   help="Explicit approval to launch/load and send button presses")
    p.add_argument("--swing", action="store_true",
                   help="Also send ONE experimental forward swing after menus (opt-in)")
    p.add_argument("--confirm-before-swing", action="store_true",
                   help="Require ENTER and a visual ready-to-swing check before the opt-in shot")
    args = p.parse_args()

    if args.timeout <= 0 or args.port not in range(1, 65536):
        p.error("timeout must be positive; port must be 1..65535")
    if args.swing and not args.send_live:
        p.error("--swing requires --send-live")
    if args.confirm_before_swing and not args.swing:
        p.error("--confirm-before-swing requires --swing")
    if args.attach_running and (args.dolphin is not None or args.game is not None
                                or args.dolphin_user is not None):
        p.error("--attach-running must not be combined with fresh-boot paths or --dolphin-user")

    phases = planned_menu_phases(
        startup=args.startup_frames, a_press=args.first_a_frames,
        between=args.wait_frames, ab_press=args.ab_frames,
        gap=args.gap_frames, final_a=args.last_a_frames,
        settle=args.settle_frames)
    profile = StateCatalog(args.catalog).get(args.profile)
    print(f"Pre-existing savestate: {profile.name}, slot {profile.slot} (NO save/overwrite)")
    print(json.dumps([vars(phase) for phase in phases], indent=2))
    if not args.send_live:
        print("DRY RUN: nothing launched, loaded or pressed. Add --send-live to proceed.")
        return

    if args.attach_running:
        with FelkRPC(port=args.port) as rpc:
            state = StateManager(rpc).request_load(profile)
        print("Existing Dolphin state:", json.dumps(state))
    else:
        if args.dolphin is None or args.game is None:
            p.error("Fresh launch requires --dolphin PATH and --game PATH; "
                    "otherwise pass --attach-running for a currently running Dolphin")
        # _launch checks for an already open bridge and refuses duplicate Dolphin.
        # Supply a NORMAL swing bridge, never one with --startup-profile.
        status = _launch(args, profile)
        print("Dolphin startup / state load:", json.dumps(status, indent=2))

    with closing(_healthy_connection(args.port, args.timeout)) as rpc:
        print("Felk bridge is responsive and advancing frames. Sending menu sequence.")
        reports = execute_menu_phases(rpc, phases, remote=args.remote)
        print("Button dispatch report:", json.dumps(reports, indent=2))
        print("Menu sequence sent. Actual ready-to-swing state is NOT yet verified.")
        if args.swing:
            if args.confirm_before_swing:
                answer = operator_input("Visually confirm the first ball is ready; ENTER to swing or q to cancel: ")
                if answer.strip():
                    print("Swing canceled; navigation complete.")
                    return
            else:
                print("UNATTENDED OPT-IN: cannot verify ready screen; shot may hit a menu.")
            result = SwingTraceClient(rpc, port=args.remote).run(build_probe("forward"))
            print("Experimental forward swing dispatch:", json.dumps(result, indent=2))
            print("Dispatch is not proof of ball contact or a game score.")
        else:
            print("Ready for a separate guarded swing in THIS running Dolphin: "
                  "py scripts/probe_swing.py --attach-running --preset forward --send-live-swing. "
                  "Normal probe_swing.py without --attach-running now starts a NEW full "
                  "Dolphin session with the canonical A / A+B / A intro.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        print(f"Launch/menu workflow failed: {exc}", file=sys.stderr)
        sys.exit(1)
