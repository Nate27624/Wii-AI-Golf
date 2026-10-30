#!/usr/bin/env python3
"""Read-only, operator-gated Wii Sports US Rev1 no-A versus aim-only comparison.

Requires an ALREADY RUNNING Felk bridge. Reads bounded source-candidate words
via localhost; never launches Dolphin, sends input, loads savestates, writes
memory, publishes private data, or certifies rendered ball/guest physics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCENE_STATIC = 0x804BF4D8
FIELD_STATIC = 0x804BF868
CONFIG_STATIC = 0x804BF8C4
PLAYER_MANAGER_STATIC = 0x804BF8D0
STRIDE = 0xCC
ROOT = Path(__file__).resolve().parents[1]


def in_bank(value: object, length: int = 4, bank: str | None = None) -> bool:
    if type(value) is not int or type(length) is not int or value % 4 or length <= 0:
        return False
    ranges = {"MEM1": (0x80000000, 0x81800000),
              "MEM2": (0x90000000, 0x94000000)}
    return any(lo <= value and value + length <= hi
               for name, (lo, hi) in ranges.items()
               if bank is None or name == bank)


def take_snapshot(rpc) -> dict:
    """Source-gated small non-atomic reads; values never leave this process."""
    def word(address: int) -> int:
        if not in_bank(address):
            raise ValueError("source address out of guest RAM")
        result = rpc.call("memory.read_u32", [address])
        if type(result) is not int or not 0 <= result <= 0xFFFFFFFF:
            raise ValueError("invalid typed bridge response")
        return result

    def ptr(address: int, bank: str, length: int = 4) -> int:
        if not in_bank(address, length, bank):
            raise ValueError("invalid source object pointer")
        return address

    def vec(address: int) -> tuple[int, int, int]:
        ptr(address, "MEM2", 12)
        return (word(address), word(address + 4), word(address + 8))

    before = rpc.call("frame.get_count", [])
    if type(before) is not int or before < 0:
        raise ValueError("invalid bridge frame bracket")
    head_hex = rpc.call("memory.read_bytes", [0x80000000, 8])
    if type(head_hex) is not str or len(head_hex) != 16:
        raise ValueError("invalid revision header")
    try:
        header = bytes.fromhex(head_hex)
    except ValueError:
        raise ValueError("invalid revision header") from None
    if header[:6] != b"RSPE01" or header[7] != 1:
        raise ValueError("not Wii Sports USA Rev1")
    mgr = ptr(word(SCENE_STATIC), "MEM1", 0x20)
    if word(SCENE_STATIC + 4) != 0 or word(mgr + 0x18) != 5:
        raise ValueError("not active Golf scene")
    scene = ptr(word(mgr + 0xC), "MEM2", 0xA0)
    if (word(scene + 0x1C) != 5 or word(scene + 0x20) != mgr or
            word(scene + 0x54) != 2 or
            not 0x803C7718 <= word(scene) < 0x803C7798):
        raise ValueError("scene source/owner mismatch")
    config = ptr(word(CONFIG_STATIC), "MEM2", 0x9C)
    field = ptr(word(FIELD_STATIC), "MEM2", 0xA8)
    if word(config + 0x94) != 4:
        raise ValueError("not Hitting-the-Green mode 4")
    hole = word(config + 0x98)
    if hole > 8:
        raise ValueError("invalid hole index")
    pm = ptr(word(PLAYER_MANAGER_STATIC), "MEM2", 0x33C)
    if not 0x803C7DD0 <= word(pm) < 0x803C7DE0:
        raise ValueError("source player-manager type mismatch")
    selector = word(pm + 0x334)
    selected = [i for i in range(4) if selector == pm + 4 + i * STRIDE]
    if len(selected) != 1:
        raise ValueError("ambiguous selected player")
    record = ptr(selector, "MEM2", STRIDE)
    ball = ptr(word(record + 0x88), "MEM2", 0x120)
    if not 0x803C7918 <= word(ball) < 0x803C7A50:
        raise ValueError("selected ball type mismatch")
    translation = ptr(word(ball + 0x4C), "MEM2", 12)
    start = ptr(word(field + 0x50), "MEM2", 0x50)
    pin = ptr(word(field + 0x44), "MEM2", 0x50)
    start_vector = ptr(word(start + 0x4C), "MEM2", 12)
    pin_vector = ptr(word(pin + 0x4C), "MEM2", 12)
    values = {
        "selected_nested_plus_0x4c": vec(translation),
        "selected_ball_plus_0x30": vec(ball + 0x30),
        "selected_ball_cache_plus_0xcc": vec(ball + 0xCC),
        "selected_ball_cache_plus_0xf0": vec(ball + 0xF0),
        "selected_ball_cache_plus_0xfc": vec(ball + 0xFC),
        "record_initial_plus_0x54": vec(record + 0x54),
        "record_start_copy_plus_0x60": vec(record + 0x60),
        "tee_start_candidate": vec(start_vector),
        "pin_candidate": vec(pin_vector),
        "aim_candidate_plus_0x3c": (word(record + 0x3C),),
    }
    after = rpc.call("frame.get_count", [])
    if type(after) is not int or after < before:
        raise ValueError("invalid bridge frame order")
    return {"identity": (mgr, scene, config, field, pm, selected[0],
                         record, ball, translation, start, start_vector,
                         pin, pin_vector, hole),
            "values": values, "frame_bracket": (before, after)}


def compare(a: dict, b: dict) -> dict[str, int]:
    if a["identity"] != b["identity"]:
        raise ValueError("source scene/hole/object identity changed")
    if a["frame_bracket"][1] > b["frame_bracket"][0]:
        raise ValueError("bridge sample sequence reversed")
    if a["values"].keys() != b["values"].keys():
        raise ValueError("candidate key mismatch")
    return {name: sum(before != after for before, after in
                      zip(words, b["values"][name]))
            for name, words in a["values"].items()}


def summarize(b0: dict, b1: dict, a0: dict) -> dict:
    idle = compare(b0, b1)
    aim = compare(b1, a0)
    return {
        "status": "CANDIDATE_COMPARISON_ONLY",
        "kind": "operator-local-p0-no-a-idle-vs-aim-only",
        "game_id_header_checked": True,
        "scene_hole_selected_owner_candidates_stable": True,
        "no_a_operator_attestation_only": True,
        "visual_aim_operator_attestation_only": True,
        "bridge_frame_count_is_not_guest_physics_step": True,
        "idle_repeat_changed_components": idle,
        "aim_only_changed_components": aim,
        "fields_stable_in_idle_but_changed_aim_only": [
            name for name in idle if idle[name] == 0 and aim[name] > 0],
        "guest_physics_frame_verified": False,
        "rendered_ball_world_xyz_verified": False,
        "contact_verified": False,
        "velocity_verified": False,
        "same_shot_native_outcome_verified": False,
        "training_approved": False,
    }


def selftest() -> dict:
    a = {"identity": tuple(range(14)),
         "values": {"aim_candidate_plus_0x3c": (1,), "pin_candidate": (10, 11, 12)},
         "frame_bracket": (1, 2)}
    b = {**a, "frame_bracket": (3, 4)}
    c = {**a, "frame_bracket": (5, 6),
         "values": {**a["values"], "aim_candidate_plus_0x3c": (2,)}}
    assert summarize(a, b, c)["fields_stable_in_idle_but_changed_aim_only"] == ["aim_candidate_plus_0x3c"]
    assert summarize(a, b, c)["training_approved"] is False
    try:
        compare(a, {**c, "identity": tuple(range(13)) + (99,)})
    except ValueError:
        pass
    else:
        raise AssertionError("cross-scene/hole join accepted")
    assert not in_bank(True) and not in_bank(0x81FFFFFF, 12)
    return {"status": "SELFTEST_PASS", "cases": 4, "dolphin_contacted": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        print(json.dumps(selftest(), sort_keys=True))
        return 0
    if not (ROOT / "src" / "wii_ai_golf" / "integration" / "rpc.py").is_file():
        print('{"status":"ABSTAIN_REPO_NOT_FOUND","training_approved":false}')
        return 2
    sys.path.insert(0, str(ROOT / "src"))
    from wii_ai_golf.integration.rpc import FelkRPC
    try:
        print("P0 NO-CONTACT EXPERIMENT: never press A or swing.", file=sys.stderr)
        with FelkRPC(port=args.port, timeout_s=8.0) as rpc:
            if input("B0: Idle, no A/input. Type YES to sample: ").strip() != "YES":
                raise ValueError("B0 not confirmed")
            b0 = take_snapshot(rpc)
            if input("B1: Remain idle several seconds, then type YES: ").strip() != "YES":
                raise ValueError("B1 not confirmed")
            b1 = take_snapshot(rpc)
            if input("A0: Aim left/right visibly without A/swing, then type YES: ").strip() != "YES":
                raise ValueError("A0 not confirmed")
            a0 = take_snapshot(rpc)
        print(json.dumps(summarize(b0, b1, a0), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError, EOFError):
        print('{"status":"ABSTAIN_BRIDGE_OR_SOURCE_IDENTITY_GATE","training_approved":false}')
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
