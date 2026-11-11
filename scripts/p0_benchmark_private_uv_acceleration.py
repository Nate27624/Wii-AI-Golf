#!/usr/bin/env python3
"""Read-only local benchmark for the original-source compiled UV renderer.

Does not upload, copy, export, modify or commit private game assets.
Benchmarks CPU rendering ONLY; Tk image transfer and GUI event scheduling
are measured separately by the integrated inspector's on-screen ms status.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dae", type=Path, required=True)
    ap.add_argument("--width", type=int, default=900)
    ap.add_argument("--height", type=int, default=550)
    ap.add_argument("--frames", type=int, default=8)
    args = ap.parse_args(argv)
    if not 16 <= args.width <= 1280 or not 16 <= args.height <= 800:
        ap.error("Viewport dimensions outside safe preview limits")
    if not 3 <= args.frames <= 20:
        ap.error("Frame sample count outside bounded measurement window")

    from wii_ai_golf.inspector.fast_texture_render import (
        accelerated_available, prepare_fast_scene, render_fast)
    if not accelerated_available():
        print("NUMBA_ACCELERATION_UNAVAILABLE: use "
              "py -3 -m pip install 'numba>=0.68.1,<0.69'")
        return 3

    from wii_ai_golf.inspector.dae_visual import load_private_dae_visual_model
    from wii_ai_golf.inspector.texture_render import prepare_textures
    from wii_ai_golf.inspector.scene_camera import fit_camera, look_in_place

    model = load_private_dae_visual_model(args.dae)
    textures = prepare_textures(model)
    source = prepare_fast_scene(model, textures)
    camera = fit_camera(model.vertices)
    first_started = time.perf_counter()
    _, first_visible = render_fast(source, args.width, args.height, camera)
    first_ms = (time.perf_counter()-first_started)*1000.
    durations = []
    for index in range(args.frames):
        # New camera orientation exercises actual projection AND raster.
        cam = look_in_place(camera, index*2.5, index*.25)
        start = time.perf_counter()
        _, _ = render_fast(source, args.width, args.height, cam)
        durations.append((time.perf_counter()-start)*1000.)
    print("SOURCE_PRIVATE_UV_ACCELERATION_BENCHMARK_PASS")
    print("source_triangle_count:", len(model.faces))
    print("source_original_pngs:", len(model.textures))
    print("source_unresolved_faces:", model.skipped_source_faces)
    print("benchmark_viewport:", f"{args.width}x{args.height}")
    print("first_frame_with_JIT_ms:", round(first_ms, 1))
    print("warm_frame_median_ms:", round(statistics.median(durations), 1))
    print("warm_frame_max_ms:", round(max(durations), 1))
    print("first_frame_visible_triangles:", first_visible)
    print("warning: Tk upload/presentation and native Wii GX shaders not measured")
    print("source_visual_world_KCL_alignment_verified: False")
    print("training_approved: False")
    return 0


if __name__ == "__main__":
    sys.exit(main())
