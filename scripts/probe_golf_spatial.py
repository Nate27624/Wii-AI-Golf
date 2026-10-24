"""Read-only candidate 3D golf-map coordinates (US Rev1 only)."""
import argparse
import json
from pathlib import Path

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.observation_capture import write_snapshot
from wii_ai_golf.spatial_probe import capture_spatial_rev1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--label", required=True,
                        help="unique basename, e.g. green01-before-spatial")
    args = parser.parse_args()
    if not args.label.isascii() or not args.label.replace("-", "").replace("_", "").isalnum():
        parser.error("label must be ASCII letters, numbers, hyphen or underscore")
    path = Path("research/game-data.local") / f"{args.label}.json"
    if path.exists():
        parser.error(f"refusing to overwrite existing evidence file: {path}")
    with FelkRPC(port=args.port, timeout_s=15) as rpc:
        result = capture_spatial_rev1(rpc)
    result["label"] = args.label
    write_snapshot(result, path)
    print(json.dumps({"saved": str(path), **result}, indent=2))


if __name__ == "__main__":
    main()
