"""Manual-visual controller preflight: repeated one-frame Wii Remote Plus or A.

Explicitly changes game input; avoid during training. ACK does not prove game
consumed buttons. Use Plus because many Wii Sports screens visibly pause.
"""
import argparse
import json
import sys
from pathlib import Path

# Select the source tree of THIS checkout instead of an older editable install.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SRC = str(_REPO_ROOT / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)

from wii_ai_golf.integration.rpc import FelkRPC


def main():
    parser = argparse.ArgumentParser(description="Visual Wii Remote connection test (no actual golf swing)")
    parser.add_argument("--send-live-button", action="store_true", required=True)
    parser.add_argument("--button", choices=("Plus", "A"), default="Plus")
    parser.add_argument("--frames", type=int, default=45)
    parser.add_argument("--remote", type=int, choices=range(4), default=0)
    parser.add_argument("--port", type=int, default=55355)
    args = parser.parse_args()
    if not args.send_live_button or not 1 <= args.frames <= 120:
        parser.error("--send-live-button and --frames 1..120 required")
    with FelkRPC(port=args.port) as rpc:
        info = rpc.call("bridge.ping")
        before = rpc.call("controller.get_wiimote_buttons", [args.remote])
        for _ in range(args.frames):
            rpc.call("controller.set_wiimote_buttons", [args.remote, {args.button: True}])
        for _ in range(4):
            rpc.call("controller.set_wiimote_buttons", [args.remote, {args.button: False}])
        after = rpc.call("controller.get_wiimote_buttons", [args.remote])
    print(json.dumps({"source": "live-controller-request", "bridge_version": info.get("bridge_version"),
                      "remote": args.remote, "button": args.button, "requested_frames": args.frames,
                      "before": before, "after": after,
                      "warning": "RPC acknowledgements are NOT proof that Wii Sports observed the button; report on-screen reaction"}, indent=2))


if __name__ == "__main__":
    main()
