"""Local-only generator for an experimental atomic-input Felk bridge patch."""
import argparse
from pathlib import Path

from wii_ai_golf.integration.atomic_patch import patch_bridge, git_blob_sha


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch a pinned upstream mcp_bridge.py; retains its MIT licensing")
    parser.add_argument("--source", type=Path, required=True, help="Source mcp_bridge.py obtained from upstream")
    parser.add_argument("--output", type=Path, required=True, help="A separate output path; never overwrites input")
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Output must not overwrite the original bridge")
    source = args.source.read_text(encoding="utf-8")
    new = patch_bridge(source)
    args.output.write_text(new, encoding="utf-8")
    print(f"Wrote EXPERIMENTAL bridge at {args.output}; original blob SHA {git_blob_sha(source)}")
    print("This patch requires validation in Felk Dolphin; NO gameplay success is implied.")


if __name__ == "__main__":
    main()
