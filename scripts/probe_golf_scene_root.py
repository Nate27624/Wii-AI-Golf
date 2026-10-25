"""Bounded, READ-ONLY Rev1 candidate scene-root triage on already running Dolphin.

Research only: a source-backed .sbss two-word interval is not proof that
either cell stores RPSysSceneMgr::spInstance. No live player/power address is
identified. All pointer VALUES remain private and are never output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.integration.rpc import FelkRPC

# doldecomp/ogws config/RSPE01_01/splits.txt, RPSysSceneMgr.cpp .sbss
ROOT_STORAGE_CELLS = (0x804BF4D8, 0x804BF4DC)
# Source-backed RPSysSceneMgr inheritance: EGG::SceneManager +0xC/+0x18.
CURRENT_SCENE_OFFSET = 0xC
CURRENT_SCENE_ID_OFFSET = 0x18
GOLF_SCENE_ID = 5
# kiwi515/ogws_info RPSportsBaseScene.h +0x54 and
# RPSportsSequenceMgr.h SPORT_GOLF == 2; independent of scene-manager ID.
SCENE_SPORT_OFFSET = 0x54
GOLF_SPORT_ID = 2
# kiwi515/ogws_info RPGolScene.h, newer decomp says unk9C.
POSSIBLE_GOLF_MAIN_OFFSET = 0x9C
# doldecomp/ogws RSPE01_01/splits.txt, RPGolScene.cpp .data.
GOLF_SCENE_DATA_START = 0x803C7718
GOLF_SCENE_DATA_END = 0x803C7798
# Source-backed RPGolConfig singleton storage and mode field.
GOLF_CONFIG_STORAGE = 0x804BF8C4
GOLF_MODE_OFFSET = 0x94
MAX_SPAN_FRAMES = 40


def _ram(addr: object, size: int = 4) -> bool:
    return (type(addr) is int and addr % 4 == 0 and size > 0
            and ((0x80000000 <= addr and addr + size <= 0x81800000)
                 or (0x90000000 <= addr and addr + size <= 0x94000000)))


def _u32(rpc: object, addr: int) -> int:
    if not _ram(addr):
        raise ValueError("read outside validated Wii RAM bounds")
    value = rpc.call("memory.read_u32", [addr])
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("invalid Wii u32 read")
    return value


def _check_game(rpc: object) -> None:
    header = rpc.call("memory.read_bytes", [0x80000000, 8])
    if type(header) is not str or len(header) != 16:
        raise RuntimeError("Cannot confirm game disc revision")
    try:
        value = bytes.fromhex(header)
    except ValueError as exc:
        raise RuntimeError("Bad game header response") from exc
    if value[:6] != b"RSPE01" or value[7] != 1:
        raise RuntimeError("Requires Wii Sports US revision 1 (RSPE01 Rev1)")
    config = _u32(rpc, GOLF_CONFIG_STORAGE)
    if not _ram(config, GOLF_MODE_OFFSET + 4):
        raise RuntimeError("Invalid RPGolConfig pointer")
    if _u32(rpc, config + GOLF_MODE_OFFSET) != 4:
        raise RuntimeError("Requires Hitting the Green training mode 4")


def _frame(rpc: object) -> int:
    value = rpc.call("frame.get_count", [])
    if type(value) is not int or value < 0:
        raise RuntimeError("Invalid emulation frame counter")
    return value


def _pass(rpc: object) -> tuple[list[dict], tuple[int, int]]:
    begin = _frame(rpc)
    candidates = []
    for slot, storage in enumerate(ROOT_STORAGE_CELLS):
        manager = _u32(rpc, storage)
        if not _ram(manager, CURRENT_SCENE_ID_OFFSET + 4):
            candidates.append({"slot": slot, "manager_ram_like": False,
                               "golf_scene_id_match": False})
            continue
        scene_id = _u32(rpc, manager + CURRENT_SCENE_ID_OFFSET)
        scene = _u32(rpc, manager + CURRENT_SCENE_OFFSET)
        scene_ram = _ram(scene, POSSIBLE_GOLF_MAIN_OFFSET + 4)
        result = {"slot": slot, "_private_manager": manager,
                  "_private_scene": scene, "manager_ram_like": True,
                  "golf_scene_id_match": scene_id == GOLF_SCENE_ID,
                  "scene_pointer_ram_like": scene_ram}
        # Only inspect source-backed scene-member offsets when BOTH gates hold.
        if scene_id == GOLF_SCENE_ID and scene_ram:
            # Do not treat a generic scene-ID match as the golf scene:
            # verify a *separate* source-backed sport member and vtable
            # plausibility before even reading the disputed +0x9C member.
            vtable = _u32(rpc, scene)
            sport = _u32(rpc, scene + SCENE_SPORT_OFFSET)
            result["scene_vtable_in_golf_data_region"] = (
                GOLF_SCENE_DATA_START <= vtable < GOLF_SCENE_DATA_END
                and vtable % 4 == 0)
            result["scene_sport_id_match"] = sport == GOLF_SPORT_ID
            if result["scene_sport_id_match"] and result["scene_vtable_in_golf_data_region"]:
                possible_main = _u32(rpc, scene + POSSIBLE_GOLF_MAIN_OFFSET)
                result["_private_possible_main"] = possible_main
                result["possible_main_pointer_ram_like"] = _ram(possible_main, 4)
        candidates.append(result)
    end = _frame(rpc)
    if end < begin or end - begin > MAX_SPAN_FRAMES:
        raise RuntimeError("Non-atomic snapshot exceeded permitted frame span")
    return candidates, (begin, end)


def probe(rpc: object) -> dict:
    """Two independent bounded passes; no guessed address scanning."""
    _check_game(rpc)
    first, (start1, end1) = _pass(rpc)
    _check_game(rpc)
    second, (start2, end2) = _pass(rpc)
    if start2 < end1:
        raise RuntimeError("Emulation frame counter rolled backwards between passes")
    stable = [row for row, other in zip(first, second)
              if row == other and row.get("golf_scene_id_match")
              and row.get("scene_pointer_ram_like")
              and row.get("scene_sport_id_match")
              and row.get("scene_vtable_in_golf_data_region")]
    return {
        "schema_version": 1,
        "kind": "golf_scene_root_candidate_triage",
        "game_id": "RSPE01",
        "revision": 1,
        "game_mode": 4,
        "candidate_static_cells_checked": len(ROOT_STORAGE_CELLS),
        "pass_count": 2,
        "max_sample_frame_span": max(end1 - start1, end2 - start2),
        "stable_golf_scene_chain_count": len(stable),
        "stable_slot_indices": [row["slot"] for row in stable],
        # Two valid-looking static cells are ambiguous, even if they
        # point to the same manager; do not auto-select either.
        "unique_stable_golf_scene_chain": len(stable) == 1,
        "vtable_in_golf_scene_data_count": sum(
            bool(row.get("scene_vtable_in_golf_data_region")) for row in stable),
        "possible_main_pointer_ram_like_count": sum(
            bool(row.get("possible_main_pointer_ram_like")) for row in stable),
        "stable_sport_id_match_count": sum(
            bool(row.get("scene_sport_id_match")) for row in stable),
        "confirmed_manager_singleton_address": False,
        "confirmed_golf_main_type": False,
        "confirmed_golf_power_address": False,
        "warning": (
            "Source-anchored 8-byte static-storage triage only; pointers were "
            "NOT type-proven, scene sport/vtable are only plausibility checks; "
            "no game power or player RAM identified. "
            "No runtime addresses or byte values are included.")
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attach-running", action="store_true",
                        help="Explicit opt-in; read-only attach to an existing Dolphin bridge")
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--out", type=Path, default=None,
                        help="Override default private-data sibling SANITIZED output file")
    parser.add_argument("--no-upload", action="store_true",
                        help="Explicitly keep sanitized result local; raw RAM is never published")
    args = parser.parse_args(argv)
    if not args.attach_running:
        parser.error("Requires --attach-running; does not boot Dolphin or load savestates")
    if not 1 <= args.port <= 65535:
        parser.error("Invalid local RPC port")
    try:
        with FelkRPC(port=args.port, timeout_s=15) as rpc:
            report = probe(rpc)
        report["id"] = (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
                        + uuid.uuid4().hex[:8])
        report["study_id"] = "S002-GOLF-SCENE-ROOT-TRIAGE"
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        destination = args.out or (ROOT.parent / "Wii-AI-Golf-Data" / "captures"
                                   / ("golf-scene-root-" + report["id"] + "-summary.json"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as file:
            file.write(payload)
        print(payload, end="")
        print("SANITIZED local report:", destination, flush=True)
        if not args.no_upload:
            try:
                # Fail closed until S000 merges the typed public-observation
                # validator AND explicitly approves this new kind.
                from wii_ai_golf.shared.public_observation import public_observation
                checked = public_observation(report)
                from research_cli import publish_summary
                print("Sanitized GitHub observation published:", publish_summary(checked), flush=True)
            except (ImportError, ValueError, RuntimeError, OSError) as exc:
                print("GitHub publisher refused or failed; safe report retained locally. "
                      "S000 privacy schema approval required: " + str(exc), file=sys.stderr)
        return 0
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        print("Scene-root read-only probe stopped: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
