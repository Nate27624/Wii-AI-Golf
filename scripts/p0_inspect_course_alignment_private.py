#!/usr/bin/env python3
"""Read-only local Wii Golf course alignment / original-memory evidence audit.

Checks strict private asset files, source-authored Collada node transforms,
KCL source surface classes and, if an already running Felk bridge responds,
two independently scene/owner-gated RSPE01 Rev1 Hitting-the-Green memory
samples. Only category counts and derived scalar residuals print.

No controller commands, ROM writes, Dolphin launch, game-model edits,
private source coordinates, raw memory banks, runtime pointers or upload.
No source calibration or training claim from bounding-box registration.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from wii_ai_golf.inspector.asset_preferences import load_asset_selections
from wii_ai_golf.inspector.dae_visual import load_private_dae_visual_model
from wii_ai_golf.inspector.replay import float_hypothesis
from wii_ai_golf.inspector.scene_alignment_audit import (
    audit_collada_scene, audit_surface_registration)
from wii_ai_golf.inspector.terrain import load_private_obj
from wii_ai_golf.inspector.terrain_labels import apply_private_surface_labels
from wii_ai_golf.inspector.tree_positions import load_private_tree_positions


def source_gated_live_anchors(port: int = 55355) -> dict:
    """Attempt exactly TWO source-selected read-only packets from running Golf.

    Identity includes revision/scene/Golf mode/hole/player, tee and pin
    pointer chains, so a running but wrong scene ABSTAINS. They are sequential
    host reads, not one atomic Dolphin physics frame. No memory addresses
    or vector contents are serialized to stdout.
    """
    from wii_ai_golf.integration.rpc import FelkRPC
    from wii_ai_golf.inspector.live import ReadOnlyRPC
    from wii_ai_golf.inspector.fast import packet

    with FelkRPC(port=port, timeout_s=3.) as connection:
        rpc = ReadOnlyRPC(connection)
        a = packet(rpc, "ALIGNMENT_PRE", 0)
        b = packet(rpc, "ALIGNMENT_POST", 1)
    if a["identity"] != b["identity"]:
        raise ValueError("Source owner changed during two memory packets")
    if any(a["words"][k] != b["words"][k]
           for k in ("tee_start_candidate", "pin_candidate")):
        raise ValueError("Tee/pin position changed during non-atomic sample")
    if a["frame_bracket"][1] > b["frame_bracket"][0]:
        raise ValueError("Source memory frame bracket went backward")
    tee = tuple(float_hypothesis(w) for w in b["words"]["tee_start_candidate"])
    pin = tuple(float_hypothesis(w) for w in b["words"]["pin_candidate"])
    if any(v is None or not math.isfinite(v) or abs(v) >= 1e7
           for v in (*tee, *pin)):
        raise ValueError("Source tee/pin float32 interpretation declined")
    return {"tee":tee, "pin":pin, "hole":int(a["identity"][13]),
            "selected_player":int(a["identity"][5]),
            "rpc_calls":rpc.calls,
            "frame_bracket":(a["frame_bracket"][0], b["frame_bracket"][1])}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--terrain-obj", type=Path, help="STRICT PRIVATE source KCL OBJ")
    p.add_argument("--terrain-labels", type=Path,
                   help="STRICT PRIVATE SHA-bound KCL surface-label JSON sidecar")
    p.add_argument("--visual-dae", type=Path, help="STRICT PRIVATE original visual Collada DAE")
    p.add_argument("--trees", type=Path, help="STRICT PRIVATE original 94-tree JSON")
    p.add_argument("--port", type=int, default=55355)
    p.add_argument("--offline", action="store_true",
                   help="Skip source-gated Dolphin memory check")
    p.add_argument("--require-live", action="store_true",
                   help="Fail if live source-gated Wii memory cannot be read")
    args = p.parse_args(argv)
    if args.offline and args.require_live:
        p.error("--offline and --require-live conflict")
    if not 1 <= args.port <= 65535:
        p.error("--port must be a valid local port")

    try:
        preferences = load_asset_selections()
    except (OSError, ValueError) as exc:
        print("ABSTAIN_PREFERENCES:", type(exc).__name__)
        return 2
    terrain_path = args.terrain_obj or (
        Path(preferences.terrain_obj) if preferences.terrain_obj else None)
    if terrain_path is None:
        print("ABSTAIN_TERRAIN: no saved KCL OBJ. Choose Load PRIVATE terrain OBJ once.")
        return 2
    if args.visual_dae is not None:
        visual_path = args.visual_dae
    else:
        candidates = (
            Path("D:/Projects/WiiGolfVisualPrivate/visual_exports/glf_course_fc1/glf_course_fc1.dae"),
            terrain_path.parent / "WiiGolfVisualPrivate" / "visual_exports" /
            "glf_course_fc1" / "glf_course_fc1.dae",
            terrain_path.parent.parent / "WiiGolfVisualPrivate" / "visual_exports" /
            "glf_course_fc1" / "glf_course_fc1.dae",
        )
        visual_path = next((q for q in candidates if q.is_file()), None)
    if visual_path is None:
        print("ABSTAIN_VISUAL: original private DAE not found. Supply --visual-dae.")
        return 2
    try:
        terrain = load_private_obj(terrain_path)
        if args.terrain_labels is not None:
            terrain = apply_private_surface_labels(terrain, args.terrain_labels)
        visual = load_private_dae_visual_model(visual_path)
        scene = audit_collada_scene(visual_path)
        if args.trees is not None or preferences.tree_json:
            tree_path = args.trees or Path(preferences.tree_json)
            trees = load_private_tree_positions(tree_path)
            tree_count = len(trees.positions)
        else:
            tree_count = 0
    except (OSError, ValueError) as exc:
        # Do not echo exception paths, source vectors, or original scene nodes.
        print("ABSTAIN_SOURCE_ASSETS:", type(exc).__name__, str(exc).split(":")[0][:120])
        return 2

    # Without decoded original OGWS groups or a SHA-bound source label sidecar,
    # no cross-material contrast is possible. Do not print a misleading
    # almost-empty alignment report or silently infer surface types.
    if not any(type(attr) is int and attr in (1, 3, 6)
               for attr in terrain.face_materials):
        print("ABSTAIN_KCL_SOURCE_MATERIALS: supply --terrain-labels "
              "using the original SHA-bound PRIVATE source sidecar.")
        return 2

    live = None
    live_status = "SKIPPED_BY_OPERATOR" if args.offline else "ABSTAIN_NO_RUNNING_SOURCE_GATED_BRIDGE"
    if not args.offline:
        try:
            live = source_gated_live_anchors(args.port)
            live_status = "TWO_SOURCE_GATED_READONLY_PACKETS_PASS"
        except (OSError, ConnectionError, TimeoutError, ValueError, RuntimeError,
                KeyError, IndexError, TypeError, ImportError) as exc:
            live_status = "ABSTAIN_" + type(exc).__name__.upper()
    report = {
        "status": "SOURCE_DIAGNOSTIC_ONLY_NO_NATIVE_ALIGNMENT_CLAIM",
        "strict_source_kcl": {"sha256":terrain.sha256, "faces":len(terrain.faces)},
        "strict_source_visual": {"sha256":visual.obj_sha256,
                                "renderable_faces":len(visual.faces)},
        "private_source_tree_count": tree_count,
        "dae_visual_scene": scene,
        "live_memory": {"status":live_status},
        "geometry": audit_surface_registration(
            terrain, visual,
            tee=live["tee"] if live is not None else None,
            pin=live["pin"] if live is not None else None),
        "training_approved": False,
        "source_visual_world_alignment_verified": False,
    }
    if live is not None:
        report["live_memory"].update({
            "hole_index":live["hole"],
            "selected_player_index":live["selected_player"],
            "read_only_rpc_calls":live["rpc_calls"],
            "guest_frame_read_bracket":live["frame_bracket"],
            "identity_stable_between_samples":True,
            "native_world_transform_proven":False,
        })
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_live and live is None:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
