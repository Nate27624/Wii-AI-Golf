#!/usr/bin/env python3
"""Original live WOOD/LEAVES/NEAR_MISS source-only motion/scene triage.

Go DEEPER than changes-per-word, but preserve evidence boundaries.
- Revalidate all original private SHA256 manifests and raw stream sequences
  via the existing recovery reader. No Dolphin connection, new capture,
  code injection, input, save state or game-memory writes.
- Compare source-selected Ball 12-byte triplets bit-for-bit to nested
  translation-candidate streams and to every candidate Ball 12-byte window.
- Locate sustained *candidate* movement per trial; compare source-f32
  triplet turning angles/step-length ratios, NOT velocity or impacts.
- Inspect original tree indices 11,38,40 offsets +0x24/+0x2C with exact
  sample-bracket transitions, alongside ordinary changes at +0x4C/+0x50.
- Separate first-source-sample mismatches into per-word offset counts;
  do not call different bytes different savestates or different collisions.

PRIVATE in-memory numeric values are NEVER emitted. Output uses only
source-relative offsets, tree source indices, dimensionless angles/ratios,
frame-sample indices, byte-equality booleans and counts. A tree-near-Ball
world-coordinate transform and physical impact are NOT established.
Runs on existing original session only; saves new safe report exclusively.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import statistics
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import analyze_p0_tree_contact_memory_private as base

TRIAL_ORDER=("wood","leaves","near_miss")
TREE_INDICES=(11,38,40)
TREE_OFFSETS=(0x24,0x2C,0x48,0x4C,0x50)
BALL_TRIPLE_OFFSETS=(0x30,0xAC)
MAX_CANDIDATES=12
MAX_DERIVED_ANGLE=12
MAX_FLOAT_MAGNITUDE=1e7


def words_equal(a,b):
    if len(a)!=len(b) or not a:
        raise ValueError("Original source trial packet streams not comparable")
    return sum(x==y for x,y in zip(a,b))


def triplet_sequence(buffers,off):
    if off%4 or not buffers or any(len(b)<off+12 for b in buffers):
        raise ValueError("Source triplet window not bounded")
    out=[]
    for data in buffers:
        xyz=struct.unpack_from(">fff",data,off)
        if any(not math.isfinite(x) or abs(x)>MAX_FLOAT_MAGNITUDE for x in xyz):
            return None
        out.append(xyz)
    return out


def change_runs(blobs):
    if len(blobs)<2:
        raise ValueError("Original source triplets too short")
    changes=[i for i in range(1,len(blobs)) if blobs[i]!=blobs[i-1]]
    runs=[]
    if changes:
        start=prev=changes[0]
        for i in changes[1:]:
            if i!=prev+1:
                runs.append((start,prev))
                start=i
            prev=i
        runs.append((start,prev))
    ordered=sorted(runs,key=lambda x:(-(x[1]-x[0]+1),x[0]))
    leading=ordered[0] if ordered else None
    return {
        "original_packet_count":len(blobs),
        "observed_triplet_change_count":len(changes),
        "first_change_after_sample":changes[0] if changes else None,
        "longest_contiguous_change_run_after_sample_indices":
            list(leading) if leading else None,
        "longest_run_transition_count":
            leading[1]-leading[0]+1 if leading else 0,
        "multiple_disjoint_motion_runs_exist":len(runs)>1,
        "sustained_run_min_four_changes":bool(
            leading and leading[1]-leading[0]+1>=4),
        "source_triplet_changes_are_physics_motion_verified":False,
    }


def vecdelta(a,b):
    return tuple(b[j]-a[j] for j in range(3))


def magnitude(v):
    return math.sqrt(sum(x*x for x in v))


def motion_bends(points,run):
    if points is None:
        return {"finite_source_triplet_decode":False,
                "source_candidate_turning_points":[],
                "native_impact_frame_proven":False}
    if run["longest_contiguous_change_run_after_sample_indices"] is None:
        return {"finite_source_triplet_decode":True,
                "source_candidate_turning_points":[],
                "native_impact_frame_proven":False}
    first,last=run["longest_contiguous_change_run_after_sample_indices"]
    # A bend needs two adjacent displacement vectors, all three source
    # samples in the longest active contiguous run.
    bends=[]
    for i in range(max(2,first+1),last+1):
        a=vecdelta(points[i-2],points[i-1])
        b=vecdelta(points[i-1],points[i])
        da=magnitude(a)
        db=magnitude(b)
        if not all(math.isfinite(x) for x in (da,db)) or min(da,db)<1e-8:
            continue
        ratio=max(da,db)/min(da,db)
        if not math.isfinite(ratio):
            continue
        cos=max(-1.0,min(1.0,sum(a[j]*b[j] for j in range(3))/(da*db)))
        angle=math.degrees(math.acos(cos))
        bends.append((i,angle,ratio))
    ordered=sorted(bends,key=lambda x:(-x[1],-x[2],x[0]))
    return {
        "finite_source_triplet_decode":True,
        "analyzable_adjacent_displacement_pairs":len(bends),
        "largest_candidate_turns":[
            {"source_sample_index":i,
             "after_sustained_start_change_count":i-first,
             "direction_change_angle_degrees":round(angle,2),
             "adjacent_displacement_length_ratio":round(ratio,3),
             "observed_visual_tree_contact_at_this_sample_proven":False}
            for i,angle,ratio in ordered[:MAX_DERIVED_ANGLE]],
        "host_timing_not_physics_frame_aligned":True,
        "native_impact_frame_proven":False,
        "candidate_triplet_coordinate_frame_proven":False,
    }


def ball_nested_alias(ball, nested):
    if len(ball)!=len(nested) or not ball:
        raise ValueError("Source selected Ball and nested streams missing")
    if any(len(b)!=base.capture.BALL_BYTES or len(n)!=12
           for b,n in zip(ball,nested)):
        raise ValueError("Source selected Ball/nested byte span changed")
    positions=[]
    for offset in range(0,base.capture.BALL_BYTES-11,4):
        exact=sum(b[offset:offset+12]==n for b,n in zip(ball,nested))
        if exact:
            positions.append((offset,exact))
    positions.sort(key=lambda x:(-x[1],x[0]))
    return {
        "all_sample_exact_nested_triplet_alias_ball_word_offsets":[
            base.rel(o) for o,n in positions if n==len(ball)],
        "top_partial_exact_aliases":[
            {"source_ball_relative_offset":base.rel(o),
             "matching_sample_count":n,
             "sample_count":len(ball)}
            for o,n in positions if n<len(ball)][:MAX_CANDIDATES],
        "source_nested_triplet_distinct_pattern_count":len(set(nested)),
        "ball_plus_0x30_exact_nested_match_samples":sum(
            b[0x30:0x3C]==n for b,n in zip(ball,nested)),
        "ball_plus_0xAC_exact_nested_match_samples":sum(
            b[0xAC:0xB8]==n for b,n in zip(ball,nested)),
        "nested_and_ball_field_same_rendered_position_proven":False,
        "nested_triplet_is_physics_velocity_proven":False,
    }


def tree_timeline(rows,indices=TREE_INDICES):
    shots=[]
    for row in rows:
        data=row.get("all_94_tree_records_be_hex_PRIVATE")
        if data is None:
            continue
        if not isinstance(data,str) or len(data)!=2*base.TREE_BYTES:
            raise ValueError("Original tree snapshot malformed")
        binary=bytes.fromhex(data)
        if any(binary[0:4]!=binary[i*base.TREE_STRIDE:i*base.TREE_STRIDE+4]
               for i in range(base.TREE_COUNT)):
            raise ValueError("Original source firstword mismatch")
        shots.append((row["sample_index"],binary))
    if not shots:
        raise ValueError("Missing source 94-tree snapshots")
    changes={}
    for tree in indices:
        if type(tree) is not int or not 0<=tree<base.TREE_COUNT:
            raise ValueError("Source tree index invalid")
        offsets={}
        for off in TREE_OFFSETS:
            intervals=[]
            for (i,a),(j,b) in zip(shots,shots[1:]):
                pos=tree*base.TREE_STRIDE+off
                if a[pos:pos+4]!=b[pos:pos+4]:
                    intervals.append([i,j])
            offsets[base.rel(off)]={
                "changed_snapshot_intervals":intervals,
                "snapshot_pair_transition_count":len(intervals)}
        changes[str(tree)]=offsets
    global_pair=[]
    for (i,a),(j,b) in zip(shots,shots[1:]):
        pair_4c=pair_50=pair_24=pair_2c=0
        both_4c_50=both_24_2c=0
        for tree in range(base.TREE_COUNT):
            loc=tree*base.TREE_STRIDE
            flags={off:a[loc+off:loc+off+4]!=b[loc+off:loc+off+4]
                   for off in (0x24,0x2C,0x4C,0x50)}
            pair_24+=flags[0x24]
            pair_2c+=flags[0x2C]
            pair_4c+=flags[0x4C]
            pair_50+=flags[0x50]
            both_24_2c+=flags[0x24] and flags[0x2C]
            both_4c_50+=flags[0x4C] and flags[0x50]
        global_pair.append({
            "earlier_sample_index":i,
            "later_sample_index":j,
            "source_tree_count_both_plus_0x24_and_plus_0x2C_changed":
                both_24_2c,
            "source_tree_count_plus_0x24_changed":pair_24,
            "source_tree_count_plus_0x2C_changed":pair_2c,
            "source_tree_count_both_plus_0x4C_and_plus_0x50_changed":
                both_4c_50,
            "source_tree_count_plus_0x4C_changed":pair_4c,
            "source_tree_count_plus_0x50_changed":pair_50,
            "not_proven_tree_collision_response":True,
        })
    return {
        "snapshot_count":len(shots),
        "tree_candidate_change_timeline":changes,
        "all_94_tree_animation_or_runtime_common_update_intervals":global_pair,
        "source_tree_0x48_proven_collision_flag":False,
        "tree_0x24_or_0x2C_proven_impact_fields":False,
    }


def first_snapshot_mismatches(trials):
    firsts={}
    for kind,t in trials.items():
        if not t["rows"]:
            raise ValueError("Empty original trial")
        row=t["rows"][0]
        firsts[kind]={
            fam:bytes.fromhex(row[key])
            for fam,(key,length) in base.STREAMS.items()}
        tree=row.get("all_94_tree_records_be_hex_PRIVATE")
        if not isinstance(tree,str) or len(tree)!=2*base.TREE_BYTES:
            raise ValueError("Initial original 94-tree snapshot unavailable")
        firsts[kind]["source_trees"]=bytes.fromhex(tree)
    ref="wood" if "wood" in firsts else next(iter(firsts))
    comparisons=[]
    for kind in firsts:
        if kind==ref:
            continue
        candidate={}
        for fam in (*base.STREAMS,"source_trees"):
            a,b=firsts[ref][fam],firsts[kind][fam]
            if len(a)!=len(b) or len(a)%4:
                raise ValueError("Inconsistent first original sample spans")
            mismatches=[off for off in range(0,len(a),4) if
                        a[off:off+4]!=b[off:off+4]]
            if fam=="source_trees":
                count=Counter(off%base.TREE_STRIDE for off in mismatches)
                candidate[fam]={
                    "source_tree_objects_with_initial_difference":len(
                        {off//base.TREE_STRIDE for off in mismatches}),
                    "initial_different_word_offsets_per_tree":[
                        {"tree_record_relative_word_offset":base.rel(off),
                         "source_tree_objects_with_different_initial_words":n}
                        for off,n in sorted(count.items())],
                    "raw_tree_xyz_exposed":False}
            else:
                candidate[fam]={
                    "initial_different_object_word_offsets":[
                        base.rel(off) for off in mismatches],
                    "raw_source_words_exposed":False}
        comparisons.append({"trial_intent":kind,
                            "source_byte_baseline_differences":candidate})
    return {
        "reference_trial_intent":ref,
        "comparisons":comparisons,
        "same_pre_shot_savestate_proven":False,
        "different_initial_bytes_prove_different_power":False,
    }


def inspect(recovered,trials):
    if not set(trials).issubset(set(TRIAL_ORDER)) or len(trials)<1:
        raise ValueError("Original operator trial intentions malformed")
    if set(recovered["trial_intents"])!=set(trials):
        raise ValueError("Trial manifest mismatch")
    reports={}
    for kind in recovered["trial_intents"]:
        rows=trials[kind]["rows"]
        ball=base.decode_window(rows,*base.STREAMS["ball_candidate"])
        nested=base.decode_window(rows,*base.STREAMS["nested_translation_candidate"])
        blobs=[b[0x30:0x3C] for b in ball]
        phases=change_runs(blobs)
        points=triplet_sequence(ball,0x30)
        other=triplet_sequence(ball,0xAC)
        nested_points=triplet_sequence(nested,0)
        reports[kind]={
            "operator_contact_classification_from_manifest_not_native":
                trials[kind]["manifest"].get("operator_observed_contact_region"),
            "ball_plus_0x30_movement_run":phases,
            "ball_plus_0x30_candidate_direction_discontinuities":
                motion_bends(points,phases),
            "ball_plus_0xAC_finite_f32_possible":other is not None,
            "nested_candidate_finite_f32_possible":nested_points is not None,
            "ball_to_nested_raw_triplet_identity":ball_nested_alias(ball,nested),
            "source_tree_11_38_40_timelines":tree_timeline(rows),
            "motion_aligned_to_visual_contact_frame":False,
            "wood_or_foliage_material_response_verified":False,
        }
    return {
        "kind":"P0_TREE_CONTACT_SOURCE_MOTION_AND_TREE_TIMELINE_V1",
        "status":"ORIGINAL_SHA_QUALIFIED_DEEP_SOURCE_PHASE_TRIAGE",
        "original_raw_integrity_sha_and_packet_counts_verified":
            recovered["original_private_raw_sha_and_sample_counts_verified"],
        "original_ball_sample_count":recovered["total_source_packets"],
        "original_tree_snapshot_count":recovered["total_94_tree_snapshots"],
        "per_trial":reports,
        "original_first_packet_baseline_difference_audit":
            first_snapshot_mismatches(trials),
        "ball_relative_triplet_is_verified_world_xyz":False,
        "guest_physics_frame_verified":False,
        "visual_impact_frame_synchronized_with_ram":False,
        "native_wood_collision_proven":False,
        "native_foliage_collision_proven":False,
        "native_ball_velocity_or_impulse_proven":False,
        "training_approved":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        recovered,trials=base.read_trials(args.session)
        result=inspect(recovered,trials)
        session=base.integrity.qualified_session(args.session)
        out=session/"tree-contact-source-phase-triage-SAFE.json"
        with out.open("x",encoding="utf-8") as fh:
            json.dump(result,fh,indent=2,sort_keys=True,allow_nan=False)
            fh.write("\n")
        print(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False))
        print("SOURCE_PHASE_TRIAGE_COMPLETE:",out.name)
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,OverflowError,
            struct.error,json.JSONDecodeError) as exc:
        print("ABSTAIN_SOURCE_PHASE_TRIAGE:",type(exc).__name__,
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
