"""Read-only, source-gated Wii Sports USA Rev1 golf scene pointer observation.

This module has no Dolphin startup, RPC creation, controller calls, game
actions, file writes, or raw pointer outputs. S001/S000 must approve wiring it
to the canonical live startup/capture flow. Synthetic tests use injected RPC.

A successful observation establishes only a stable candidate scene chain,
NOT a confirmed RPGolMain type, swing power, ball coordinates, or score.
"""
from __future__ import annotations

from typing import Any

# Source: Rev1 executable verification (PR #122) and doldecomp/ogws
# eggSceneManager.h / RPSysSceneCreator.h / kiwi515 RPGolScene.h.
SCENE_MANAGER_STATIC_SLOT = 0x804BF4D8
GOLF_CONFIG_STATIC_SLOT = 0x804BF8C4
GAME_MODE_OFFSET = 0x94
CURRENT_SCENE_OFFSET = 0x0C
CURRENT_SCENE_ID_OFFSET = 0x18
MAIN_CANDIDATE_OFFSET = 0x9C
GOLF_SCENE_ID = 5
GREEN_TRAINING_MODE = 4
HEADER_ADDRESS = 0x80000000
HEADER_BYTES = 8
MAX_SAMPLES = 5
MAX_FRAME_SPAN = 30


class SceneChainGateError(RuntimeError):
    """A source, state, pointer, or temporal safety check did not pass."""


def _mapped(address: int, n: int = 4) -> bool:
    return (type(address) is int and address % 4 == 0 and type(n) is int
            and n > 0 and ((0x80000000 <= address and address + n <= 0x81800000)
            or (0x90000000 <= address and address + n <= 0x94000000)))


def _call(rpc: Any, method: str, params: list[int]) -> Any:
    try:
        return rpc.call(method, params)
    except Exception:
        # RPC exceptions may embed addresses or private data; suppress them.
        raise SceneChainGateError("read-only RPC request failed") from None


def _word(rpc: Any, address: int) -> int:
    if not _mapped(address):
        raise SceneChainGateError("pointer or member address outside Wii RAM")
    value = _call(rpc, "memory.read_u32", [address])
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise SceneChainGateError("invalid memory.read_u32 response")
    return value


def _frame(rpc: Any) -> int:
    value = _call(rpc, "frame.get_count", [])
    if type(value) is not int or value < 0:
        raise SceneChainGateError("invalid frame counter")
    return value


def _verify_identity(rpc: Any) -> None:
    header = _call(rpc, "memory.read_bytes", [HEADER_ADDRESS, HEADER_BYTES])
    if not isinstance(header, str) or len(header) != HEADER_BYTES * 2:
        raise SceneChainGateError("invalid disc-header response")
    try:
        raw = bytes.fromhex(header)
    except ValueError:
        raise SceneChainGateError("invalid disc-header bytes") from None
    if raw[:6] != b"RSPE01" or raw[7] != 1:
        raise SceneChainGateError("only Wii Sports USA RSPE01 Rev1 is supported")


def _snapshot(rpc: Any, max_frame_span: int) -> tuple[int, int, int, int, int]:
    start = _frame(rpc)
    # Important: no manager/gameplay reads occur before header + mode gates.
    _verify_identity(rpc)
    config = _word(rpc, GOLF_CONFIG_STATIC_SLOT)
    if not _mapped(config, GAME_MODE_OFFSET + 4):
        raise SceneChainGateError("invalid golf config instance")
    if _word(rpc, config + GAME_MODE_OFFSET) != GREEN_TRAINING_MODE:
        raise SceneChainGateError("not in Hitting the Green training mode 4")

    manager = _word(rpc, SCENE_MANAGER_STATIC_SLOT)
    if not _mapped(manager, CURRENT_SCENE_ID_OFFSET + 4):
        raise SceneChainGateError("missing or invalid scene manager")
    if _word(rpc, manager + CURRENT_SCENE_ID_OFFSET) != GOLF_SCENE_ID:
        raise SceneChainGateError("active scene is not Golf scene ID 5")
    scene = _word(rpc, manager + CURRENT_SCENE_OFFSET)
    if not _mapped(scene, MAIN_CANDIDATE_OFFSET + 4):
        raise SceneChainGateError("missing or invalid active golf scene")

    # The +0x9C field may not be a RPGolMain pointer. Read only its *word*;
    # never follow, dereference, or type-assert its contents.
    candidate = _word(rpc, scene + MAIN_CANDIDATE_OFFSET)

    if (_word(rpc, SCENE_MANAGER_STATIC_SLOT) != manager
            or _word(rpc, manager + CURRENT_SCENE_ID_OFFSET) != GOLF_SCENE_ID
            or _word(rpc, manager + CURRENT_SCENE_OFFSET) != scene):
        raise SceneChainGateError("scene or manager changed during snapshot")
    end = _frame(rpc)
    if end < start or end - start > max_frame_span:
        raise SceneChainGateError("non-atomic capture exceeded frame-span gate")
    return manager, scene, candidate, start, end


def observe_golf_scene_chain(rpc: Any, *, samples: int = 3,
                             max_frame_span: int = 12) -> dict[str, Any]:
    """Observe a stable source-grounded chain; return sanitized metadata only.

    Caller must supply canonical freshly booted, human-approved read-only RPC.
    This routine performs no launch, savestate, input, or persistent capture.
    """
    if type(samples) is not int or not 2 <= samples <= MAX_SAMPLES:
        raise ValueError("samples must be between 2 and 5")
    if type(max_frame_span) is not int or not 0 <= max_frame_span <= MAX_FRAME_SPAN:
        raise ValueError("max_frame_span must be between 0 and 30")
    readings = [_snapshot(rpc, max_frame_span) for _ in range(samples)]
    if len({row[0] for row in readings}) != 1:
        raise SceneChainGateError("scene manager changed between snapshots")
    if len({row[1] for row in readings}) != 1:
        raise SceneChainGateError("active golf scene changed between snapshots")
    if any(readings[i][3] < readings[i - 1][4] for i in range(1, len(readings))):
        raise SceneChainGateError("frame count went backwards between snapshots")
    candidate_values = [row[2] for row in readings]
    return {
        "schema_version": 1,
        "kind": "read_only_rev1_golf_scene_chain_observation",
        "source": "private DOL static slot and Rev1 scene layouts, PR #122",
        "sample_count": samples,
        "game_id": "RSPE01",
        "disc_revision": 1,
        "training_mode": GREEN_TRAINING_MODE,
        "golf_scene_id": GOLF_SCENE_ID,
        "scene_manager_current_scene_offset": "+0xC",
        "scene_manager_scene_id_offset": "+0x18",
        "candidate_scene_member_offset": "+0x9C",
        "max_observed_non_atomic_frame_span": max(e - s for _, _, _, s, e in readings),
        "manager_pointer_stable": True,
        "scene_pointer_stable": True,
        "candidate_pointer_like_count": sum(_mapped(x) for x in candidate_values),
        "candidate_word_stable": len(set(candidate_values)) == 1,
        "candidate_type_verified": False,
        "golf_main_verified": False,
        "club_pose_verified": False,
        "swing_power_verified": False,
        "ball_coordinates_verified": False,
        "score_verified": False,
        "warning": (
            "Pointer chain and scene ID gates only. Scene +0x9C is an "
            "unverified word, NOT an authoritative RPGolMain pointer. "
            "No raw RAM, heap pointers, or hit/score evidence is published."
        ),
    }
