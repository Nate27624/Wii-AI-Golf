"""Offline P0: does the selected ball approach stable cache CC within wedge 5/6/7?

Uses inherited validated 7-pair private SHA manifest and Rev1 source-selected
object checker. Prints ONLY comparisons, counts and Boolean rankings; never
floats, native words, object pointers, file paths or archive hashes.
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
import audit_p0_seven_numbered_source_pairs_private as cohort
import audit_golf_two_bank_roster_private as roster

PHASES = (1, 2, 5, 6, 7)
WEDGE = (5, 6, 7)
CACHES = ("ball_cache_0x0cc", "ball_cache_0x0f0", "ball_cache_0x0fc")
MAX_COMPONENT = 1000000.0


def float3(words):
    if len(words) != 3:
        raise ValueError("Expected 3 source words")
    vals = []
    for word in words:
        if type(word) is not int or word < 0 or word > 0xffffffff:
            raise ValueError("Invalid private word")
        x = struct.unpack(">f", struct.pack(">I", word))[0]
        if not math.isfinite(x) or abs(x) > MAX_COMPONENT:
            raise ValueError("Unbounded source f32 vector")
        vals.append(float(x))
    return tuple(vals)


def squared(a, b):
    return sum((x-y)**2 for x, y in zip(float3(a), float3(b)))


def components(a, b):
    return sum(x != y for x, y in zip(a, b))


def directions(a, b):
    a, b = float3(a), float3(b)
    return tuple(1 if y > x else -1 if y < x else 0 for x,y in zip(a,b))


def analyze_samples(samples):
    if set(samples) != set(PHASES):
        raise ValueError("Exactly source-qualified driver and wedge snapshots needed")
    for n in PHASES:
        t = samples[n]
        required = ("selected_index","hole","ball_obj","field",
                    "pin_obj","start_obj","cfg_bc","cfg_c0","cfg_c4",
                    "pin","triplets")
        if any(k not in t for k in required):
            raise ValueError("Missing gated selected owner/source controls")
        for key in ("ball_object_0x030","source_current_start",*CACHES):
            float3(t["triplets"][key])
        float3(t["pin"])

    def stable(a,b):
        x,y=samples[a],samples[b]
        return (x["selected_index"]==y["selected_index"]
                and x["hole"]==y["hole"]
                and all(x[key]==y[key] for key in (
                    "ball_obj","field","pin_obj","start_obj",
                    "cfg_bc","cfg_c0","cfg_c4"))
                and x["pin"]==y["pin"]
                and x["triplets"]["source_current_start"]==y["triplets"]["source_current_start"])

    wedge_geometry_stable = stable(5,6) and stable(6,7)
    driver_geometry_stable = stable(1,2)
    if not wedge_geometry_stable:
        raise ValueError("Wedge source-selected owner, tee, pin or Config change: ABSTAIN")
    if not driver_geometry_stable:
        raise ValueError("Driver source-selected owner, tee, pin or Config change: ABSTAIN")

    def get(n,name):
        return samples[n]["triplets"][name]
    def cur(n):
        return get(n,"ball_object_0x030")

    cc_stable = get(5,CACHES[0])==get(6,CACHES[0])==get(7,CACHES[0])
    cache_flags = {
        "+0xCC": cc_stable,
        "+0xF0": get(5,CACHES[1])==get(6,CACHES[1])==get(7,CACHES[1]),
        "+0xFC": get(5,CACHES[2])==get(6,CACHES[2])==get(7,CACHES[2]),
    }
    # All arithmetic happens locally on source-gated f32 candidates. Never print distances.
    to_cc = [squared(cur(n),get(n,CACHES[0])) for n in WEDGE]
    to_pin = [squared(cur(n),samples[n]["pin"]) for n in WEDGE]
    to_start = [squared(cur(n),get(n,"source_current_start")) for n in WEDGE]
    to_f0 = [squared(cur(n),get(n,CACHES[1])) for n in WEDGE]
    to_fc = [squared(cur(n),get(n,CACHES[2])) for n in WEDGE]
    d56 = directions(cur(5),cur(6))
    d67 = directions(cur(6),cur(7))

    def decreasing(values):
        return values[0]>values[1]>values[2]
    def nonincreasing(values):
        return values[0]>=values[1]>=values[2]

    rows = []
    for idx,n in enumerate(WEDGE):
        words = cur(n)
        c = get(n,CACHES[0])
        rows.append({
            "phase_number":n,
            "ball_matches_cache_CC_bits":components(words,c)==0,
            "ball_matches_cache_F0_bits":components(words,get(n,CACHES[1]))==0,
            "ball_matches_cache_FC_bits":components(words,get(n,CACHES[2]))==0,
            "ball_matches_pin_bits":components(words,samples[n]["pin"])==0,
            "ball_matches_start_bits":components(words,get(n,"source_current_start"))==0,
            "CC_closer_to_current_than_pin":to_cc[idx]<to_pin[idx],
            "CC_closer_to_current_than_start":to_cc[idx]<to_start[idx],
            "CC_closer_to_current_than_F0":to_cc[idx]<to_f0[idx],
            "CC_closer_to_current_than_FC":to_cc[idx]<to_fc[idx],
            "distance_to_CC_less_than_prior_phase":None if idx==0 else to_cc[idx]<to_cc[idx-1],
            "distance_to_PIN_less_than_prior_phase":None if idx==0 else to_pin[idx]<to_pin[idx-1],
        })
    landing_c = cur(7)
    return {
        "kind":"P0-OFFLINE-WEDGE-STABLE-CACHE-ENDPOINT-ORDER-01",
        "source_gates_pass_5_of_5":True,
        "private_bank_SHA_all_seven_pairs_pass":True,
        "wedge_source_geometry_and_owner_stable":True,
        "driver_source_geometry_and_owner_stable":True,
        "cache_stable_within_wedge":cache_flags,
        "CC_candidate_distance_strictly_decreases_5_to_6_to_7":decreasing(to_cc),
        "CC_candidate_distance_nonincreasing_5_to_6_to_7":nonincreasing(to_cc),
        "PIN_candidate_distance_strictly_decreases_5_to_6_to_7":decreasing(to_pin),
        "START_candidate_distance_strictly_decreases_5_to_6_to_7":decreasing(to_start),
        "F0_candidate_distance_strictly_decreases_5_to_6_to_7":decreasing(to_f0),
        "FC_candidate_distance_strictly_decreases_5_to_6_to_7":decreasing(to_fc),
        "CC_equals_current_exactly_in_phase_7":landing_c==get(7,CACHES[0]),
        "CC_equals_PIN_exactly_in_phase_7":get(7,CACHES[0])==samples[7]["pin"],
        "CC_equals_START_exactly_in_phase_7":get(7,CACHES[0])==get(7,"source_current_start"),
        "CC_equals_F0_exactly_in_phase_7":get(7,CACHES[0])==get(7,CACHES[1]),
        "CC_equals_FC_exactly_in_phase_7":get(7,CACHES[0])==get(7,CACHES[2]),
        "selected_ball_component_directions_consistent_5_6_and_6_7":[
            (a==b and a!=0) for a,b in zip(d56,d67)
        ],
        "driver_1_to_2_current_changed_components":components(cur(1),cur(2)),
        "driver_1_to_2_CC_changed_components":components(get(1,CACHES[0]),get(2,CACHES[0])),
        "driver_first_ball_equals_first_CC":cur(1)==get(1,CACHES[0]),
        "driver_second_ball_equals_second_CC":cur(2)==get(2,CACHES[0]),
        "wedge_phase_rows":rows,
        "source_f32_interpretation_is_candidate_only":True,
        "cache_endpoint_semantics_verified":False,
        "physical_world_XYZ_verified":False,
        "ball_velocity_verified":False,
        "game_power_verified":False,
        "score_verified":False,
        "same_guest_frame_machine_verified":False,
        "phase_order_machine_verified":False,
        "approved_for_training":False,
        "allowed_to_publish_raw":False
    }


def read_private(archive):
    folders=cohort._check_archive(archive)
    samples={}
    with ExitStack() as stack:
        for n in PHASES:
            mm=[]
            for i,size in enumerate(cohort.SIZE):
                p=cohort.src._file(folders[n],f"{n}.{i+1}.raw",size)
                f=stack.enter_context(p.open("rb"))
                mm.append(stack.enter_context(mmap.mmap(
                    f.fileno(),0,access=mmap.ACCESS_READ)))
            rd=roster.TwoBankReader(*mm)
            s=cohort._get(rd) # #231 exact source Rev1 / scene / owner/pin/source-chain
            u=rd.u32
            pm=u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
            record=pm+4+s["selected_index"]*roster.ROSTER_STRIDE
            ball=u(record+0x88)
            if roster._bank(ball,0x108)!="MEM2" or u(ball+0x4C)!=ball+0x30:
                raise ValueError("Selected ball object/source translation chain invalid")
            s["ball_obj"]=ball
            samples[n]=s
        return analyze_samples(samples)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        result=read_private(args.archive)
    except (OSError,TypeError,KeyError,ValueError,OverflowError,ZeroDivisionError):
        print("P0 endpoint order ABSTAIN: private SHA/source owner/geometry/f32 validity; no guest action or physical claim",file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
