#!/usr/bin/env python3
"""Open local, read-only P0 JSONL replay; intentionally never launches Dolphin."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", default="", help="Local SHA-verified JSONL candidate events")
    parser.add_argument("--manifest", default="", help="Matching SHA-256 manifest")
    parser.add_argument("--terrain-obj", default="", help="Opt-in private OBJ to load on startup")
    parser.add_argument("--terrain-labels", default="",
                        help="Optional local source KCL per-face JSON colors; OBJ stays unmodified")
    visual_source = parser.add_mutually_exclusive_group()
    visual_source.add_argument(
        "--visual-dae", default="",
        help="Open a specific original UV Collada DAE+TEX0 PNG")
    visual_source.add_argument(
        "--visual-course", type=int,
        help="Try an explicit LOCAL glf_course_fcN DAE export (1-9); never map a game hole from the filename")
    visual_source.add_argument(
        "--probe-visual-course", type=int,
        help="Only report whether a local FCN DAE/BRRES exists; do NOT open GUI or source assets")
    parser.add_argument(
        "--course-private-root", type=Path,
        default=None,
        help="Existing local private WiiGolfVisualPrivate root, default D:/Projects/WiiGolfVisualPrivate")
    args = parser.parse_args(argv)
    if args.terrain_labels and not args.terrain_obj:
        parser.error("--terrain-labels requires --terrain-obj for SHA binding")
    if bool(args.capture) != bool(args.manifest):
        parser.error("--capture and --manifest must be supplied together")
    visual_dae = args.visual_dae
    if args.visual_course is not None or args.probe_visual_course is not None:
        from wii_ai_golf.inspector.private_course_catalog import (
            DEFAULT_PRIVATE_ROOT, inspect_private_course,
            private_course_report)
        course = (args.visual_course if args.visual_course is not None
                  else args.probe_visual_course)
        try:
            candidate = inspect_private_course(
                course, args.course_private_root or DEFAULT_PRIVATE_ROOT)
        except ValueError as exc:
            parser.error(str(exc))
        if args.probe_visual_course is not None:
            print(json.dumps(private_course_report(candidate),
                             sort_keys=True, indent=2))
            return 0
        if candidate.exported_dae is None:
            print(json.dumps(private_course_report(candidate),
                             sort_keys=True, indent=2))
            print(
                "Cannot launch Course 2 candidate without its original local"
                " DAE export. Extract glf_course_fcN.carc from your own game"
                " and export glf_course_fcN.brres MDL0 + textures in BrawlCrate;"
                " then rerun this command. No fallback to mismatched FC1.",
                file=sys.stderr)
            return 3
        visual_dae = str(candidate.exported_dae)
    from wii_ai_golf.inspector.gui import launch
    try:
        return launch(args.capture, args.manifest, args.terrain_obj,
                      args.terrain_labels, visual_dae)
    except (OSError, RuntimeError) as exc:
        print(f"Offline inspector could not start: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
