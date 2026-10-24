"""EXPERIMENTAL: runs ONLY after a locally validated patched Felk bridge is loaded."""
import argparse
import json

from wii_ai_golf.integration.atomic_client import AtomicSample, AtomicTraceClient
from wii_ai_golf.integration.rpc import FelkRPC


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one atomic sample batch to patched Felk bridge")
    parser.add_argument("--send-live-trace", action="store_true", help="Required acknowledgment of real input")
    parser.add_argument("--port", type=int, default=55355)
    args = parser.parse_args()
    if not args.send_live_trace:
        parser.error("Explicit --send-live-trace required; use read-only probe first")
    # Not a calibrated swing; only controller connectivity demonstration.
    samples = [AtomicSample(True, (0.0, 1.0, 0.0)) for _ in range(6)]
    samples += [AtomicSample(True, (0.0, 2.0, 0.0)) for _ in range(6)]
    samples += [AtomicSample(False, (0.0, 1.0, 0.0)) for _ in range(3)]
    with FelkRPC(port=args.port) as bridge:
        result = AtomicTraceClient(bridge).run(samples)
    print(json.dumps({"source": "experimental-patched-emulator", "result": result,
                      "warning": "No game recognition or scoring proven"}, indent=2))


if __name__ == "__main__":
    main()
