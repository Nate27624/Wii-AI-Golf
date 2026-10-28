"""Private W5->W6->W7 ordinal distance-to-cache/target source study.

Only SHA-pinned, seven-pair archived snapshots accepted. Reuses canonical
S002 #231 source decoder and checks target/owner invariants. Numeric vectors,
distances, raw RAM, pointers, hashes and paths NEVER leave this process.
Output is strictly boolean/order categories; candidate game units are not
physical XYZ. No Dolphin, controller, second reader, writes, network or model.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import math
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

SELECTED = (1, 2, 5, 6, 7)
WEDGE = (5, 6, 7)
MAX_ABS_FLOAT = 100000.0
REL_TOL = 1e-6
ABS_TOL = 1e-5

def _decode_float(word):
    if type(word) is not int or not 0 <= word <= 0xffffffff:
        raise ValueError("Invalid private coordinate word")
    value = struct.unpack(">f", struct.pack(">I", word))[0]
    if not math.isfinite(value) or abs(value) > MAX_ABS_FLOAT:
        raise ValueError("Nonfinite/unbounded candidate coordinate")
    return value

def _vec(triplet):
    if len(triplet) != 3:
        raise ValueError("Invalid private vector width")
    return tuple(_decode_float(w) for w in triplet)

def _dist(a,b):
    return math.dist(_vec(a),_vec(b))

def _relation(a,b):
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError("Nonfinite private distance")
    if math.isclose(a,b,rel_tol=REL_TOL,abs_tol=ABS_TOL):
        return "equal_within_numeric_tolerance"
    return "decreased" if b<a else "increased"

def _enriched(rd):
    # Canonical source-backed Rev1 selected scene/record/ball/pin/start gate.
    s=seven._get(rd)
    u=rd.u32
    pm=u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec=pm+4+roster.ROSTER_STRIDE*s["selected_index"]
    ball=u(rec+0x88)
    field=u(roster.GOLF_FIELD_STATIC)
    pin=u(field+0x44)
    start=u(field+0x50)
    config=u(roster.GOLF_CONFIG_STATIC)
    if (roster._bank(ball,0x108)!="MEM2"
            or roster._bank(pin,0x50)!="MEM2"
            or roster._bank(start,0x50)!="MEM2"
            or u(ball+0x4c)!=ball+0x30
            or u(pin+0x48)!=pin+0x0c
            or u(pin+0x4c)!=pin+0x30
            or u(start+0x48)!=start+0x0c
            or u(start+0x4c)!=start+0x30):
        raise ValueError("Source selected object selfref/region gate failed")
    s["owner_ids"]=(pm,rec,ball,field,pin,start,config)
    return s

def _ball(s):
    return s["triplets"]["ball_object_0x030"]

def _cache(s):
    return s["triplets"]["ball_cache_0x0cc"]

def _start(s):
    return s["triplets"]["source_current_start"]

def _same_gate(a,b):
    return (
        a["selected_index"]==b["selected_index"]
        and a["hole"]==b["hole"]
        and a["owner_ids"]==b["owner_ids"]
        and all(a[k]==b[k] for k in ("cfg_bc","cfg_c0","cfg_c4","pin"))
        and _start(a)==_start(b)
    )

def summarize(samples):
    if set(samples)!=set(SELECTED):
        raise ValueError("Exactly D1,D2,W5,W6,W7 sources required")
    for i in SELECTED:
        s=samples[i]
        if len(s["owner_ids"])!=7 or type(s["selected_index"]) is not int:
            raise ValueError("Incomplete private source owner identity")
        for v in (_ball(s),_cache(s),s["triplets"]["ball_cache_0x0f0"],
                  s["triplets"]["ball_cache_0x0fc"],_start(s),s["pin"]):
            _vec(v)
    wedge_gate=all(_same_gate(samples[5],samples[n]) for n in (6,7))
    wedge_cache_stable=all(_cache(samples[5])==_cache(samples[n]) for n in (6,7))
    # Does NOT classify a confounded phase as a zero-change comparison.
    if not wedge_gate or not wedge_cache_stable:
        raise ValueError("Wedge owner, selector, target, tee or fixed cache changed")
    wedge=[samples[n] for n in WEDGE]
    if any(_ball(wedge[i])==_ball(wedge[i+1]) for i in (0,1)):
        raise ValueError("One wedge transition has no candidate motion")
    cache_dist=[_dist(_ball(s),_cache(s)) for s in wedge]
    pin_dist=[_dist(_ball(s),s["pin"]) for s in wedge]
    tee_dist=[_dist(_ball(s),_start(s)) for s in wedge]
    cache_to_pin=[_dist(_cache(s),s["pin"]) for s in wedge]
    driver_gate=_same_gate(samples[1],samples[2])
    driver_cache_stable=_cache(samples[1])==_cache(samples[2])
    return {
        "kind":"P0-SEVEN-PHASE-CANDIDATE-ENDPOINT-ORDER-CHECK",
        "schema_version":1,
        "all_source_guards_pass":True,
        "preserved_seven_pair_archive_sha_verified":True,
        "wedge_stable_selected_owner_and_geometry":True,
        "wedge_cache_CC_bitwise_constant":True,
        "wedge_current_ball_changes_at_both_transitions":True,
        "wedge_current_ball_equal_cache_CC_components":[sum(
            x==y for x,y in zip(_ball(s),_cache(s))) for s in wedge],
        "wedge_cache_CC_to_pin_candidate_distance_constant":all(
            _relation(cache_to_pin[0],d)=="equal_within_numeric_tolerance"
            for d in cache_to_pin[1:]),
        "wedge_ball_to_cache_CC_candidate_distance_step_relation":[
            _relation(cache_dist[0],cache_dist[1]),
            _relation(cache_dist[1],cache_dist[2])],
        "wedge_ball_to_pin_candidate_distance_step_relation":[
            _relation(pin_dist[0],pin_dist[1]),
            _relation(pin_dist[1],pin_dist[2])],
        "wedge_ball_to_start_candidate_distance_step_relation":[
            _relation(tee_dist[0],tee_dist[1]),
            _relation(tee_dist[1],tee_dist[2])],
        "wedge_ball_reaches_unchanged_cache_CC_at_W7":_ball(samples[7])==_cache(samples[5]),
        "wedge_ball_equals_pin_at_W7":_ball(samples[7])==samples[7]["pin"],
        "wedge_cache_CC_equals_pin":_cache(samples[5])==samples[5]["pin"],
        "driver_D1_to_D2_same_source_owner_and_geometry":driver_gate,
        "driver_D1_to_D2_cache_CC_stable":driver_cache_stable if driver_gate else None,
        "driver_D2_ball_equals_own_cache_CC":_ball(samples[2])==_cache(samples[2]) if driver_gate else None,
        "endpoint_cache_semantics_verified":False,
        "physical_ball_xyz_verified":False,
        "physical_axes_or_units_verified":False,
        "ball_velocity_verified":False,
        "shot_power_verified":False,
        "same_boot_across_phases_machine_verified":False,
        "same_guest_frame_per_snapshot_machine_verified":False,
        "capture_phase_mapping_machine_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
        "interpretation_limit":(
            "Ordinal distances of source-relative f32 candidates only; "
            "no physical axes, units, shot timing, velocity or endpoint meaning proven. "
            "W7 human label may indicate flag/green contact, not settled physics."
        )
    }

def analyze(archive):
    # All fourteen 24+64MiB files and original PRIVATE hashes verified by #231.
    dirs=seven._check_archive(archive)
    with ExitStack() as stack:
        states={}
        for n in SELECTED:
            banks=[]
            for k,size in enumerate(seven.SIZE):
                fp=stack.enter_context(seven.src._file(
                    dirs[n], f"{n}.{k+1}.raw", size).open("rb"))
                banks.append(stack.enter_context(mmap.mmap(
                    fp.fileno(),0,access=mmap.ACCESS_READ)))
            states[n]=_enriched(roster.TwoBankReader(*banks))
        return summarize(states)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    a=p.parse_args(argv)
    try:
        result=analyze(a.archive)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,struct.error):
        print("P0 ordinal endpoint study ABSTAIN: private manifest/source/geometry/float gate failed.",file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
