"""Offline P0 source-selected player record +0x30/+0x90 role discriminator.

Uses existing PR #235 original SHA-gated source samples; 2 words only.
Compares candidate pointer shape, finite f32 shape, and exact aliases to
source-selected ball components; returns booleans and comparison categories.
NEVER outputs numeric game memory, private addresses, bytes, hashes or paths.
No Dolphin / controller / new RAM scan / source write / approved training.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_record_phase_masks_private as base
import audit_golf_two_bank_roster_private as roster

KEYS=(0x30,0x90)
PHASES=(1,2,5,6,7)
WEDGE=(5,6,7)
FLOAT_MAX=1e5
def finite_float(word):
    if type(word) is not int or not 0 <= word <= 0xffffffff:
        raise ValueError("invalid source-backed u32")
    v=struct.unpack(">f",struct.pack(">I",word))[0]
    return v if math.isfinite(v) and abs(v)<=FLOAT_MAX else None

def sign(a,b):
    if a is None or b is None:
        return "unclassified"
    if a==b:return "same"
    return "up" if b>a else "down"

def _word(sample,offset):
    values=sample["whole_record"]
    if len(values)!=51:
        raise ValueError("source record not 51 aligned words")
    return values[offset//4]

def _trip(sample,name):
    a=sample["triplets"][name]
    if len(a)!=3 or any(type(w)is not int for w in a):
        raise ValueError("source vector not three u32 words")
    return tuple(a)

def _equality_mask(word,values):
    return [word==v for v in values]

def _approx_equal(a,b):
    return math.isclose(a,b,rel_tol=1e-5,abs_tol=1e-6)

def _three_point_affine(x,y):
    """Boolean only; three-point co-linearity is NOT a physical model."""
    if len(x)!=3 or len(y)!=3:
        raise ValueError("exact three phase vectors required")
    if any(v is None or not math.isfinite(v) for v in (*x,*y)):
        return None
    dx1=x[1]-x[0]
    dx2=x[2]-x[1]
    if abs(dx1)<=1e-8 or abs(dx2)<=1e-8:
        return None
    slope1=(y[1]-y[0])/dx1
    slope2=(y[2]-y[1])/dx2
    if not (math.isfinite(slope1) and math.isfinite(slope2)):
        return None
    return _approx_equal(slope1,slope2)

def report(samples):
    # A strict owner+pin/tee+config+source-check must pass before any
    # candidate data are inspected as potential float or pointer.
    prior=base.summarize(samples)
    if (prior["source_rev1_all_selected_owner_and_geometry_gates_passed"] is not True):
        raise ValueError("base owner gate failed")
    for n in PHASES:
        sample=samples[n]
        _trip(sample,"ball_object_0x030")
        _trip(sample,"ball_cache_0x0cc")
        _trip(sample,"source_current_start")
        if len(sample["pin"])!=3:
            raise ValueError("pin vector not three words")
    summaries=[]
    for off in KEYS:
        wedge_values=[_word(samples[n],off) for n in WEDGE]
        driver_values=[_word(samples[n],off) for n in (1,2)]
        wedge_floats=[finite_float(v) for v in wedge_values]
        pointer_shapes=[
            roster._bank(_word(samples[n],off),4) in ("MEM1","MEM2")
            for n in PHASES
        ]
        ball_xyz=[_trip(samples[n],"ball_object_0x030") for n in WEDGE]
        cache_cc=[_trip(samples[n],"ball_cache_0x0cc") for n in WEDGE]
        wedge_equal_ball=[_equality_mask(w,b) for w,b in zip(wedge_values,ball_xyz)]
        wedge_equal_cache=[_equality_mask(w,c) for w,c in zip(wedge_values,cache_cc)]
        wedge_equal_tee=[_equality_mask(w,_trip(samples[n],"source_current_start"))
                         for w,n in zip(wedge_values,WEDGE)]
        wedge_equal_pin=[_equality_mask(w,samples[n]["pin"])
                         for w,n in zip(wedge_values,WEDGE)]
        dirs=[sign(wedge_floats[i],wedge_floats[i+1]) for i in (0,1)]
        ball_floats=[[finite_float(x) for x in v] for v in ball_xyz]
        matched_signs=[]
        for i in range(3):
            changes=[sign(ball_floats[j][i],ball_floats[j+1][i]) for j in (0,1)]
            matched_signs.append(
                all(x==y and x not in ("same","unclassified")
                    for x,y in zip(dirs,changes))
            )
        # source-relative field +0x30 is not nested ball object +0x30.
        summaries.append({
            "record_relative_offset":f"+0x{off:03X}",
            "changed_wedge_5_to_6":wedge_values[0]!=wedge_values[1],
            "changed_wedge_6_to_7":wedge_values[1]!=wedge_values[2],
            "changed_driver_D1_to_D2":driver_values[0]!=driver_values[1],
            "wedge_distinct_u32_bitpatterns":len(set(wedge_values)),
            "native_mem1_or_mem2_pointer_shaped_in_phase_order_D1_D2_W5_W6_W7":pointer_shapes,
            "bounded_f32_candidate_in_wedge_5_6_7":[x is not None for x in wedge_floats],
            "wedge_f32_direction_steps":dirs,
            "same_direction_as_ball_f32_component_across_both_wedge_edges":matched_signs,
            "exact_word_equal_ball_xyz_component_mask_W5_W6_W7":wedge_equal_ball,
            "exact_word_equal_cache_CC_component_mask_W5_W6_W7":wedge_equal_cache,
            "exact_word_equal_start_component_mask_W5_W6_W7":wedge_equal_tee,
            "exact_word_equal_pin_component_mask_W5_W6_W7":wedge_equal_pin,
            "same_one_ball_component_alias_all_three_wedge_phases":[
                all(mask[i] for mask in wedge_equal_ball) for i in range(3)],
            "physical_interpretation_verified":False,
        })
    # Relationship between the two *selected-player* scalar candidates.
    # This does not read any new RAM beyond the already-qualified source
    # snapshots. No float, ratio or absolute coordinate escapes the process.
    left_words=[_word(samples[n],KEYS[0]) for n in WEDGE]
    right_words=[_word(samples[n],KEYS[1]) for n in WEDGE]
    left=[finite_float(w) for w in left_words]
    right=[finite_float(w) for w in right_words]
    ball0=[finite_float(_trip(samples[n],"ball_object_0x030")[0])
           for n in WEDGE]
    float_pair_qualified=all(x is not None for x in (*left,*right))
    diff_constant=(all(_approx_equal(left[i]-right[i],
                                     left[0]-right[0]) for i in (1,2))
                   if float_pair_qualified else None)
    rel={
        "wedge_player_030_equals_player_090_word_by_phase_W5_W6_W7":[
            a==b for a,b in zip(left_words,right_words)],
        "wedge_player_030_vs_090_float_order_by_phase_W5_W6_W7":[
            ("unclassified" if a is None or b is None else
             "equal_within_numeric_tolerance" if _approx_equal(a,b) else
             "record_030_less_than_090" if a<b else
             "record_030_greater_than_090")
            for a,b in zip(left,right)],
        "wedge_player_030_minus_090_is_numeric_constant":diff_constant,
        "wedge_player_090_affine_to_player_030_three_points_candidate":
            _three_point_affine(left,right),
        "wedge_player_030_affine_to_ball_component_0_three_points_candidate":
            _three_point_affine(ball0,left),
        "wedge_player_090_affine_to_ball_component_0_three_points_candidate":
            _three_point_affine(ball0,right),
        "three_point_affinity_proves_physical_mapping":False,
        "relation_uses_only_three_human_labeled_wedge_phases":True,
    }
    return {
        "kind":"P0-SELECTED-RECORD-TWO-WORD-SOURCE-ROLE-CROSSWALK",
        "schema_version":1,
        "all_seven_archived_bank_SHA_verified":True,
        "all_selected_source_and_within_shot_geometry_gates_passed":True,
        "distinct_fields_compared":len(KEYS),
        "fields":summaries,
        "relationship":rel,
        "record_plus_030_is_distinct_from_ball_object_plus_030":True,
        "float_shape_or_direction_proves_numeric_semantics":False,
        "pointer_shape_proves_live_pointer":False,
        "actual_ball_world_xyz_verified":False,
        "ball_velocity_verified":False,
        "swing_power_verified":False,
        "impact_or_contact_state_verified":False,
        "score_or_outcome_verified":False,
        "same_boot_or_frames_machine_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
        "note":"Only source-relative u32 bitwise equivalence and bounded float/pointer-shape hypotheses. No semantic type, coordinate axis, numeric values or timing proven.",
    }

def analyze(archive:Path):
    return report(base.read_samples(archive))

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        result=analyze(a.archive)
    except (ValueError,OSError,TypeError,KeyError,OverflowError,struct.error):
        print("P0 two-word role audit ABSTAIN: SHA/source/selected owner or object gate failed.",file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
