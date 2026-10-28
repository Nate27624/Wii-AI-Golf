"""Guarded, attach-only V1/45-or-90-frame-A contact recheck for an already-ready golfer.

No Dolphin boot, savestate load, controller waveform changes, or automatic
success labeling. Reuses collect_outcome_transition.py exclusively. The
historical single V1 A45 hit is not a repeatability guarantee.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = str(ROOT / "src")
if SRC in sys.path:
    sys.path.remove(SRC)
sys.path.insert(0, SRC)
BRIDGE = ROOT.parent / "tools" / "mcp_bridge_swing_legacy_eval.py"


def build_collector_command(*, python: str = sys.executable, root: Path = ROOT,
                            port: int = 55355, a_lead_frames: int = 45) -> list[str]:
    """Do not add a fresh launcher, change the waveform, or prime by RPC count."""
    if type(a_lead_frames) is not int or a_lead_frames not in (45, 90):
        raise ValueError('V1 timing comparison accepts only 45 or 90 observed A-lead frames')
    collector = root / "scripts" / "collect_outcome_transition.py"
    if not collector.is_file():
        raise ValueError("canonical attached RAM/shot collector missing")
    return [
        python, str(collector), "--send-live-swing",
        "--a-prime-requests", "0", "--a-lead-frames", str(a_lead_frames),
        "--observe-start-pose", "--ask-power", "--port", str(port),
    ]


def check_local_v1_source(bridge: Path) -> None:
    """Validate expected local source; DOES NOT prove which bridge is loaded."""
    from wii_ai_golf.shared.bridge_provenance import inspect_bridge_file
    if not bridge.is_file():
        raise ValueError("isolated local V1 bridge missing; do not substitute V2")
    meta = inspect_bridge_file(bridge)
    if (meta.get("revision") != "V1-neutral-swing-calls"
            or meta.get("safe_for_isolated_legacy_copy") is not True):
        raise ValueError("expected reviewed no-autoload V1 bridge source not found")


def ensure_running_bridge(port: int, *, delay: float = 0.15) -> None:
    """Read-only live-frame check. Paused or wrong bridge => no swing."""
    from wii_ai_golf.integration.rpc import FelkRPC
    with FelkRPC(port=port, timeout_s=2.0) as rpc:
        info = rpc.call("bridge.ping")
        if not isinstance(info, dict) or not isinstance(info.get("bridge_version"), str):
            raise RuntimeError("expected Felk RPC bridge not active")
        before = rpc.call("frame.get_count")
        time.sleep(delay)
        after = rpc.call("frame.get_count")
        if (type(before) is not int or type(after) is not int
                or after <= before):
            raise RuntimeError("Dolphin frames are not advancing; unpause before retry")
        # V2 should not be confused with the selected reviewed V1 setup.
        try:
            caps = rpc.call("trace.swing_capabilities", [])
        except Exception:
            caps = None  # V1 does not advertise V2 swing capabilities.
        if isinstance(caps, dict) and caps.get("swing_protocol") == 2:
            raise RuntimeError("running bridge reports V2; V1 A45 comparison refused")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--send-live-swing", action="store_true",
                   help="explicit permission for ONE shot after collector prompts")
    p.add_argument("--port", type=int, default=55355)
    p.add_argument("--a-lead-frames", type=int, choices=(45, 90), default=45,
                   help='45 previously observed hitting trial, or controlled 90-frame prehold retry')
    p.add_argument("--expected-bridge", type=Path, default=BRIDGE)
    args = p.parse_args(argv)
    if args.port not in range(1, 65536):
        p.error("port must be between 1 and 65535")
    try:
        command = build_collector_command(port=args.port, a_lead_frames=args.a_lead_frames)
        check_local_v1_source(args.expected_bridge)
        if not args.send_live_swing:
            print("DRY RUN ONLY. Attached collector command:", command)
            print("No emulator, savestate, controller input, or RAM write performed.")
            return 0
        ensure_running_bridge(args.port)
        print("READY-BALL V1 A45 recheck: existing advancing Dolphin only; NO reset.", flush=True)
        print("Local V1 file is validated but loaded bridge identity is not proven by ping.", flush=True)
        print(f"Original 89-sample forward waveform; measured {args.a_lead_frames}-frame A prehold.", flush=True)
        print("Human observation still required; dispatch is NOT proof of contact.", flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        return int(result.returncode)
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        print(f"Ready-ball recheck refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
