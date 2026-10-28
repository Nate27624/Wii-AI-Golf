"""OFFLINE preflight only: source-gated selected-ball read inside one bridge tick.

No Felk integration, RPC, controller calls, files, network or raw public output.
The returned words/pointers are PRIVATE and must not be uploaded or logged.
"""
from __future__ import annotations

MEM1 = (0x80000000, 0x81800000)
MEM2 = (0x90000000, 0x94000000)
SCENE_DATA = (0x803C7718, 0x803C7798)
PM_DATA = (0x803C7DD0, 0x803C7DE0)
BALL_DATA = (0x803C7918, 0x803C7A50)
MANAGER_SLOT = 0x804BF4D8
CONFIG_SLOT = 0x804BF8C4
FIELD_SLOT = 0x804BF868
PM_SLOT = 0x804BF8D0
MAX_WORD_READS = 48
STAGES = ("idle_before", "idle_after", "event_before", "event_after")


class UnverifiedSample(RuntimeError):
    pass


def mapped(address, size=4, *, bank=MEM2):
    return (type(address) is int and address % 4 == 0
            and size % 4 == 0 and size >= 4
            and bank[0] <= address and address + size <= bank[1])


def data_word(word, interval):
    return (type(word) is int and word % 4 == 0
            and interval[0] <= word < interval[1])


def sample_pre_dispatch(*, read_u32, bridge_tick, stage,
                        source_contract_reviewed=False):
    """Single synchronous callback; never interpret bridge tick as real game frame."""
    if (source_contract_reviewed is not True
            or stage not in STAGES or not callable(read_u32)
            or not callable(bridge_tick)):
        raise UnverifiedSample("unreviewed source contract or callbacks")
    count = 0

    def r(addr):
        nonlocal count
        if not (mapped(addr, bank=MEM1) or mapped(addr, bank=MEM2)):
            raise UnverifiedSample("unmapped source address")
        if count >= MAX_WORD_READS:
            raise UnverifiedSample("read budget exceeded")
        count += 1
        try:
            value = read_u32(addr)
        except Exception:
            raise UnverifiedSample("native memory read failed") from None
        if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
            raise UnverifiedSample("invalid word from bridge")
        return value

    def ptr(addr, size=4, bank=MEM2):
        value = r(addr)
        if not mapped(value, size, bank=bank):
            raise UnverifiedSample("source pointer outside expected bank")
        return value

    def vec3(addr):
        if not mapped(addr, 12):
            raise UnverifiedSample("unmapped VEC3 destination")
        return [r(addr + 4 * i) for i in range(3)]

    try:
        tick0 = bridge_tick()
        if type(tick0) is not int or tick0 < 0:
            raise UnverifiedSample("no valid bridge tick")
        if (r(MEM1[0]), r(MEM1[0] + 4)) != (0x52535045, 0x30310001):
            raise UnverifiedSample("not RSPE01 Rev1")
        manager = ptr(MANAGER_SLOT, 0x24, MEM1)
        if r(manager + 0x18) != 5:
            raise UnverifiedSample("golf manager ID failed")
        scene = ptr(manager + 0xC, 0xA0)
        if (not data_word(r(scene), SCENE_DATA)
                or r(scene + 0x1C) != 5
                or r(scene + 0x20) != manager
                or r(scene + 0x54) != 2):
            raise UnverifiedSample("scene/backlink/sport gate failed")
        config = ptr(CONFIG_SLOT, 0x9C)
        if r(config + 0x94) != 4:
            raise UnverifiedSample("wrong golf mode")
        hole = r(config + 0x98)
        if hole > 17:
            raise UnverifiedSample("hole index not bounded")
        field = ptr(FIELD_SLOT, 0x54)
        start_obj = ptr(field + 0x50, 0x50)
        start_vec = ptr(start_obj + 0x4C, 12)
        if start_vec != start_obj + 0x30:
            raise UnverifiedSample("start transform self-pointer mismatch")
        pm = ptr(PM_SLOT, 0x338)
        if not data_word(r(pm), PM_DATA):
            raise UnverifiedSample("player-manager region gate failed")
        selected = ptr(pm + 0x334, 0xCC)
        index = next((i for i in range(4)
                      if selected == pm + 4 + i * 0xCC), None)
        if index is None:
            raise UnverifiedSample("selected record not inline")
        ball = ptr(selected + 0x88, 0x50)
        if not data_word(r(ball), BALL_DATA):
            raise UnverifiedSample("ball object data interval mismatch")
        ball_vec = ptr(ball + 0x4C, 12)
        private_words = {
            "selected_ball_vec": vec3(ball_vec),
            "current_start_vec": vec3(start_vec),
            "record_pos_054_vec": vec3(selected + 0x54),
            "record_pos_060_vec": vec3(selected + 0x60),
        }
        if (r(pm + 0x334) != selected
                or r(selected + 0x88) != ball
                or r(ball + 0x4C) != ball_vec
                or r(field + 0x50) != start_obj):
            raise UnverifiedSample("object chain changed mid-read")
        tick1 = bridge_tick()
        if type(tick1) is not int or tick1 != tick0:
            raise UnverifiedSample("bridge frame callback changed mid-read")
        return {
            "kind": "PRIVATE_DO_NOT_PUBLISH_ball_frame_candidate",
            "stage": stage, "bridge_tick_start": tick0, "bridge_tick_end": tick1,
            "bridge_tick_verified_as_emulated_game_frame": False,
            "source_path_gates_passed": True,
            "selected_record_index": index, "hole_index": hole,
            "selected_record_pointer": selected, "ball_owner_pointer": ball,
            "start_object_pointer": start_obj,
            "private_words": private_words,
            "read_u32_call_count": count, "read_budget": MAX_WORD_READS,
            "ball_world_xyz_verified": False, "physical_motion_verified": False,
        }
    except UnverifiedSample:
        raise
    except Exception:
        raise UnverifiedSample("unverified source read/callback") from None
