"""Run locally via: python scripts/probe_dolphin_bridge.py [--read-only-live]."""
import argparse
import json

from wii_ai_golf.integration import FelkRPC, OfflineFelkBridge, TraceEvent, TraceRehearsal


def main() -> None:
    parser = argparse.ArgumentParser(description="Felk Wii Remote integration preflight; defaults to offline")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--read-only-live", action="store_true", help="Ping and read frame counts on localhost")
    modes.add_argument("--send-live-probe", action="store_true", help="Send experimental input; affects running game")
    parser.add_argument("--i-understand-active-input", action="store_true")
    parser.add_argument("--port", type=int, default=55355, help="TCP bridge port")
    args = parser.parse_args()
    if args.send_live_probe and not args.i_understand_active_input:
        parser.error("--send-live-probe requires --i-understand-active-input")
    if args.read_only_live or args.send_live_probe:
        with FelkRPC(port=args.port) as bridge:
            rehearsal = TraceRehearsal(bridge)
            if args.read_only_live:
                data = {"source": "live-bridge-read-only", **rehearsal.preflight()}
            else:
                # A is pressed, accel pulses are NOT atomic and may be missed in Wii Sports.
                data = rehearsal.run([TraceEvent(0, (0.0, 1.0, 0.0)),
                                      TraceEvent(12, (0.0, 2.0, 0.0))]).as_dict()
    else:
        data = TraceRehearsal(OfflineFelkBridge()).run([
            TraceEvent(0, (0.0, 1.0, 0.0)), TraceEvent(12, (0.0, 2.0, 0.0))]).as_dict()
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
