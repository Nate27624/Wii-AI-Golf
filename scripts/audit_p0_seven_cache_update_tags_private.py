"""Read-only P0 cache-tag equality study over the seven original source-gated pairs.

Only two 32-bit fields (+0x118 / +0x11C) touched by the documented
Rev1 conditional F0/FC update routines are compared. Their semantics,
writer execution, physics and timing are NOT established.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

PHASES = tuple(range(1, 8))
EDGES = ((1, 2), (5, 6), (6, 7), (5, 7))
TAGS = (0x118, 0x11C)
CACHES = ("ball_cache_0x0f0", "ball_cache_0x0fc")

def _u32(v):
    if type(v) is not int or not 0 <= v <= 0xFFFFFFFF:
        raise ValueError("invalid metadata word")
    return v

def _vec(v):
    if type(v) is not tuple or len(v) != 3:
        raise ValueError("invalid source triplet")
    return tuple(_u32(x) for x in v)

def _check(s):
    if (type(s) is not dict or type(s.get("selected_index")) is not int
            or s["selected_index"] not in range(4)
            or type(s.get("hole")) is not int or not 0 <= s["hole"] <= 8):
        raise ValueError("source selection missing")
    refs = s.get("refs")
    if type(refs) is not dict or set(refs) != {"field","record","ball","pin","start"}:
        raise ValueError("source object references missing")
    for ptr in refs.values():
        _u32(ptr)
    for key in ("cfg_bc","cfg_c0","cfg_c4"):
        _u32(s.get(key))
    for key in ("start_triplet","pin_triplet","live_triplet",*CACHES):
        _vec(s.get(key))
    tags = s.get("tags")
    balls = s.get("ball_refs")
    if (type(tags) is not tuple or len(tags) != 4
            or type(balls) is not tuple or len(balls) != 4
            or len(set(balls)) != 4
            or balls[s["selected_index"]] != refs["ball"]):
        raise ValueError("source four-slot roster missing or aliased")
    for ball in balls:
        _u32(ball)
    for pair in tags:
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError("source two-tag record missing")
        _u32(pair[0]); _u32(pair[1])

def summarize(samples):
    if type(samples) is not dict or set(samples) != set(PHASES):
        raise ValueError("exact seven source phases required")
    for s in samples.values():
        _check(s)
    rows = []
    for a,b in EDGES:
        x,y = samples[a],samples[b]
        if (x["selected_index"] != y["selected_index"] or x["hole"] != y["hole"]
                or x["refs"] != y["refs"] or x["ball_refs"] != y["ball_refs"]
                or any(x[k] != y[k] for k in
                       ("cfg_bc","cfg_c0","cfg_c4","pin_triplet","start_triplet"))):
            raise ValueError("source owner or course/geometry confound")
        sel = x["selected_index"]
        changes = [x["tags"][sel][j] != y["tags"][sel][j] for j in range(2)]
        other = [sum(x["tags"][slot][j] != y["tags"][slot][j]
                     for slot in range(4) if slot != sel) for j in range(2)]
        cache = [sum(u != v for u,v in zip(x[k],y[k])) for k in CACHES]
        rows.append({
            "edge": f"{a}_to_{b}",
            "selected_tag_0x118_changed": changes[0],
            "selected_tag_0x11C_changed": changes[1],
            "inactive_slots_tag_0x118_changed_count": other[0],
            "inactive_slots_tag_0x11C_changed_count": other[1],
            "selected_cache_F0_changed_components": cache[0],
            "selected_cache_FC_changed_components": cache[1],
            "tag_118_changed_without_cache_F0_bit_change": changes[0] and cache[0] == 0,
            "tag_11C_changed_without_cache_FC_bit_change": changes[1] and cache[1] == 0,
            "selected_live_changed_components": sum(u != v for u,v in
                zip(x["live_triplet"],y["live_triplet"])),
        })
    return {
        "kind": "P0-SEVEN-CACHE-CONDITIONAL-TAG-EQUALITY-CONTROLS",
        "archive_14_banks_sha_gated": True,
        "seven_phase_source_roster_gated": True,
        "source_cache_tag_store_sites_documented": True,
        "human_phase_labels_independently_machine_verified": False,
        "cache_tag_semantics_verified": False,
        "tag_is_guest_frame_counter_verified": False,
        "executed_cache_writer_verified": False,
        "source_global_ball_receiver_identity_verified": False,
        "actual_ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "swing_power_verified": False,
        "impact_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "within_shot_edges": rows,
    }

def analyze(archive: Path):
    # Import canonical reviewed sibling readers only; no second scanner.
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir in sys.path:
        sys.path.remove(script_dir)
    sys.path.insert(0, script_dir)
    import audit_p0_seven_numbered_source_pairs_private as seven
    from audit_golf_two_bank_roster_private import (
        TwoBankReader, _bank, ROSTER_STRIDE, PLAYER_MANAGER_STATIC_CANDIDATE
    )
    folders = seven._check_archive(archive)  # verify all 14 original bank hashes
    with ExitStack() as stack:
        samples = {}
        for phase in PHASES:
            banks = []
            for j,size in enumerate(seven.SIZE):
                path = seven.src._file(folders[phase], f"{phase}.{j+1}.raw", size)
                stream = stack.enter_context(path.open("rb"))
                banks.append(stack.enter_context(mmap.mmap(
                    stream.fileno(), 0, access=mmap.ACCESS_READ)))
            rd = TwoBankReader(*banks)
            s = seven._get(rd)  # source-gates original Rev1 scene/ball/pin
            u = rd.u32
            manager = u(PLAYER_MANAGER_STATIC_CANDIDATE)
            slot = s["selected_index"]
            rec = manager + 4 + slot * ROSTER_STRIDE
            ball = u(rec + 0x88)
            if _bank(ball, 0x1AC) != "MEM2" or u(ball + 0x4C) != ball + 0x30:
                raise ValueError("selected ball source ref invalid")
            balls,tags = [],[]
            for i in range(4):
                record = manager + 4 + i * ROSTER_STRIDE
                b = u(record + 0x88)
                if (_bank(record, ROSTER_STRIDE) != "MEM2"
                        or _bank(b, 0x1AC) != "MEM2"
                        or u(b + 0x4C) != b + 0x30):
                    raise ValueError("four-slot source roster incomplete")
                balls.append(b)
                tags.append((u(b + TAGS[0]), u(b + TAGS[1])))
            samples[phase] = {
                "selected_index": slot, "hole": s["hole"],
                "refs": {"field":s["field"],"record":rec,"ball":ball,
                         "pin":s["pin_obj"],"start":s["start_obj"]},
                "ball_refs":tuple(balls), "tags":tuple(tags),
                "cfg_bc":s["cfg_bc"],"cfg_c0":s["cfg_c0"],"cfg_c4":s["cfg_c4"],
                "live_triplet":s["triplets"]["ball_object_0x030"],
                "start_triplet":s["triplets"]["source_current_start"],
                "pin_triplet":s["pin"],
                "ball_cache_0x0f0":s["triplets"]["ball_cache_0x0f0"],
                "ball_cache_0x0fc":s["triplets"]["ball_cache_0x0fc"],
            }
        result = summarize(samples)
    seven._check_archive(archive)  # refuse mutated banks at end of read
    return result

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    args = p.parse_args(argv)
    try:
        result = analyze(args.archive)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,json.JSONDecodeError):
        print("P0 tag study ABSTAIN: archive SHA, Rev1 source/owner/geometry failed; no private data printed.",file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
