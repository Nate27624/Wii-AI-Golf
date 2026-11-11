#!/usr/bin/env python3
"""Original 3 live tree trials: deeper OFFLINE memory-only response triage.

Preserves original local source-owned Ball and 94-tree candidate captures.
Reads only prior SHA-qualified trial JSONL via the existing private
recovery verifier. No Dolphin/Felk connection, game changes, new swings,
video access or native RAM/code/pointers/XYZ in emitted report.

Targets 3 confounders left by earlier aggregates:
(1) candidate turning "max/min" displacement ratios are unsigned: this
    ranks *signed* AFTER/BEFORE displacement and timing-adjusted ratios;
(2) whole-trial alias percentages may be dominated by stationary shots:
    exact Ball+0x30/+0xCC/nested comparisons are stratified by actual
    candidate movement and tested at consecutive-sample lags;
(3) Tree+0x24/+0x2C changes could represent integer/pointer fields
    updated when the ball moves, rather than impact latches: test
    bounded word categories and movement-onset co-updates in all 3.

All reported source-index/angles are candidate semantics only: no
independent rendered-ball translation, synchronized impact frame,
wood/foliage native branch, restitution or actual collision shape.
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
import p0_tree_contact_source_phase_triage_private as prior
import analyze_p0_tree_contact_memory_private as base

TREE_STRIDE=base.TREE_STRIDE
TREE_COUNT=base.TREE_COUNT
TREE_BYTES=base.TREE_BYTES
CANDIDATES={"+0x030":0x30,"+0x0CC":0xCC,
            "+0x0F0":0xF0,"+0x0FC":0xFC,"+0x0AC":0xAC}
TREE_FIELDS=(0x24,0x2C,0x48,0x4C,0x50)
MAX_BENDS=8
MAX_INTERVALS=6
MAX_DELTA=1e8


def original_streams(rows):
    ball=base.decode_window(rows,*base.STREAMS["ball_candidate"])
    nested=base.decode_window(rows,*base.STREAMS["nested_translation_candidate"])
    tree=[]
    for row in rows:
        raw=row.get("all_94_tree_records_be_hex_PRIVATE")
        if raw is None:
            continue
        if not isinstance(raw,str) or len(raw)!=TREE_BYTES*2:
            raise ValueError("Original tree record snapshot changed")
        data=bytes.fromhex(raw)
        if len(data)!=TREE_BYTES:
            raise ValueError("Original 94-tree array truncated")
        table=data[:4]
        if any(data[i*TREE_STRIDE:i*TREE_STRIDE+4]!=table
               for i in range(TREE_COUNT)):
            raise ValueError("Original 94 tree source firstword mismatch")
        tree.append((row["sample_index"],data))
    if len(ball)!=len(nested) or len(ball)<2 or not tree:
        raise ValueError("Original source sample count mismatch")
    return ball,nested,tree


def phases(ball):
    source=[data[0x30:0x3C] for data in ball]
    run=prior.change_runs(source)
    moving={i for i in range(1,len(source)) if source[i]!=source[i-1]}
    # Classify each sample by an actual observed candidate-word
    # transition, not merely "recording started" or intended ball impact.
    return {
        "moving":moving,
        "stationary":set(range(len(source)))-moving,
        "run":run,
    }


def source_aliases(ball,nested,stage):
    if len(ball)!=len(nested) or len(ball)<2:
        raise ValueError("Mixed candidate sources")
    total=len(ball)
    data={label:[b[off:off+12] for b in ball]
          for label,off in CANDIDATES.items()}
    names=("+0x030", "+0x0CC", "+0x0F0", "+0x0FC","+0x0AC")
    spans={}
    for name in names:
        seq=data[name]
        counts={}
        for phase in ("stationary","moving"):
            indices=stage[phase]
            counts[phase]={
                "samples":len(indices),
                "exact_same_packet_nested_matches":sum(
                    seq[i]==nested[i] for i in indices),
                "exact_nested_previous_packet_matches":sum(
                    i>=1 and seq[i]==nested[i-1] for i in indices),
                "exact_nested_next_packet_matches":sum(
                    i+1<total and seq[i]==nested[i+1] for i in indices),
            }
        spans[name]=counts
    alias_pairs={}
    for first,second in (
            ("+0x030","+0x0CC"),
            ("+0x030","+0x0F0"),
            ("+0x030","+0x0FC"),
            ("+0x030","+0x0AC"),
            ("+0x0CC","+0x0F0")):
        alias_pairs[first+"_versus_"+second]={
            phase:{
                "sample_count":len(stage[phase]),
                "exact_same_packet_triplet_matches":sum(
                    data[first][i]==data[second][i]
                    for i in stage[phase])
            } for phase in ("stationary","moving")}
    return {
        "source_ball_sample_count":total,
        "source_ball_plus_0x30_transition_sample_count":len(stage["moving"]),
        "stationary_candidate_sample_count":len(stage["stationary"]),
        "nested_exact_matches_by_ball_offset_and_phase":spans,
        "ball_candidate_exact_interfield_matches_by_phase":alias_pairs,
        "cross_packet_aliases_may_be_non_atomic_copy_or_interpolation":True,
        "native_rendered_translation_or_velocity_verified":False,
    }


def triple(data,off):
    xyz=struct.unpack_from(">fff",data,off)
    if any(not math.isfinite(v) or abs(v)>prior.MAX_FLOAT_MAGNITUDE
           for v in xyz):
        return None
    return xyz


def speed_proxy(ball,rows,stage):
    # HOST timestamps, not guest physics time or frame clock.
    run=stage["run"]["longest_contiguous_change_run_after_sample_indices"]
    if run is None:
        return {"available":False,"reason":"no_sustained_candidate_run",
                "native_velocity_or_collision_verified":False}
    start,end=run
    points=[triple(x,0x30) for x in ball]
    if any(x is None for x in points):
        return {"available":False,"reason":"nonfinite_candidate_triplet",
                "native_velocity_or_collision_verified":False}
    timestamp=[r.get("host_monotonic_start_ns") for r in rows]
    if any(type(t) is not int or t<0 for t in timestamp) or any(
            b<=a for a,b in zip(timestamp,timestamp[1:])):
        raise ValueError("Original host time order changed")
    def dvec(a,b):
        return [b[k]-a[k] for k in range(3)]
    def length(v):
        return math.sqrt(sum(x*x for x in v))
    entries=[]
    # Minimum three consecutively changing candidate points.
    for i in range(max(2,start+1),end+1):
        prev=dvec(points[i-2],points[i-1])
        after=dvec(points[i-1],points[i])
        a,b=length(prev),length(after)
        if min(a,b)<1e-9 or max(a,b)>MAX_DELTA:
            continue
        before_dt=(timestamp[i-1]-timestamp[i-2])*1e-9
        after_dt=(timestamp[i]-timestamp[i-1])*1e-9
        if min(before_dt,after_dt)<=0:
            continue
        cos=max(-1.0,min(1.0,
            sum(prev[k]*after[k] for k in range(3))/(a*b)))
        angle=math.degrees(math.acos(cos))
        raw_ratio=b/a
        host_ratio=(b/after_dt)/(a/before_dt)
        if not all(math.isfinite(n) and n>0
                   for n in (raw_ratio,host_ratio)):
            continue
        flag=("decreasing_displacement_per_host_second"
              if host_ratio<0.85 else
              "increasing_displacement_per_host_second"
              if host_ratio>1.15 else
              "roughly_similar_displacement_per_host_second")
        entries.append({
            "original_sample_index":i,
            "candidate_angle_degrees":round(angle,2),
            "after_over_before_displacement_ratio":round(raw_ratio,4),
            "after_over_before_host_second_normalized_ratio":round(host_ratio,4),
            "host_timing_ratio_quality":round(after_dt/before_dt,3),
            "candidate_displacement_per_host_second_class":flag,
            "actual_collision_or_impulse_at_sample_proven":False,
        })
    entries.sort(key=lambda item:(-item["candidate_angle_degrees"],
                                  item["original_sample_index"]))
    return {
        "available":True,
        "moving_candidate_run_after_sample_indices":[start,end],
        "source_candidate_displacement_pairs_inspected":len(entries),
        "largest_candidate_turns_signed_ratio":entries[:MAX_BENDS],
        "same_host_second_does_not_prove_same_guest_physics_time":True,
        "native_velocity_or_collision_verified":False,
    }


def type_category(u):
    if type(u) is not int or not 0<=u<=0xFFFFFFFF:
        raise ValueError("Unbounded original tree record native word")
    if u==0:
        return "zero_word"
    if (u%4)==0 and 0x80000000<=u<0x81800000:
        return "aligned_mem1_range"
    if (u%4)==0 and 0x90000000<=u<0x94000000:
        return "aligned_mem2_range"
    # These are *bit-pattern categories*, not validated pointer types.
    if u<0x10000:
        return "small_positive_integer_bits"
    f=struct.unpack(">f",u.to_bytes(4,"big"))[0]
    if math.isfinite(f) and 1e-5<=abs(f)<=1e6:
        return "bounded_f32_bit_pattern"
    return "other_bits"


def tree_fields(tree):
    dist={off:Counter() for off in TREE_FIELDS}
    equal_24_2c=0
    snaps=len(tree)
    for index,raw in tree:
        if type(index) is not int or len(raw)!=TREE_BYTES:
            raise ValueError("Original tree snapshot size/source invalid")
        for t in range(TREE_COUNT):
            b=t*TREE_STRIDE
            for off in TREE_FIELDS:
                word=int.from_bytes(raw[b+off:b+off+4],"big")
                dist[off][type_category(word)]+=1
            equal_24_2c+=int(raw[b+0x24:b+0x28]==raw[b+0x2C:b+0x30])
    return {
        "sampled_source_tree_record_count":TREE_COUNT,
        "full_tree_snapshot_count":snaps,
        "source_tree_native_field_bit_pattern_categories":{
            base.rel(off):{name:count for name,count in sorted(dist[off].items())}
            for off in TREE_FIELDS},
        "source_tree_24_2c_exact_same_bits_across_all_tree_snapshots":equal_24_2c,
        "native_pointer_or_integer_type_proven":False,
        "actual_source_tree_0x24_0x2c_contact_role_proven":False,
    }


def active_interval_tree_changes(tree,stage):
    run=stage["run"]["longest_contiguous_change_run_after_sample_indices"]
    if run is None:
        return {
            "available":False,"source_tree_field_is_collision_event_proven":False}
    first=run[0]
    first_after=None
    for (a,x),(b,y) in zip(tree,tree[1:]):
        if a<first<=b:
            first_after=(a,b,x,y)
            break
    if first_after is None:
        return {
            "available":False,
            "reason":"candidate_run_not_bracketed_by_tree_snapshots",
            "source_tree_field_is_collision_event_proven":False}
    a,b,x,y=first_after
    changing={}
    for off in (0x24,0x2C,0x48,0x4C,0x50):
        indices=tuple(
            t for t in range(TREE_COUNT) if
            x[t*TREE_STRIDE+off:t*TREE_STRIDE+off+4]!=
            y[t*TREE_STRIDE+off:t*TREE_STRIDE+off+4])
        changing[off]=indices
    both=set(changing[0x24])&set(changing[0x2C])
    return {
        "available":True,
        "first_sustained_movement_original_sample":first,
        "coarse_tree_snapshots_bracketing_movement_start":[a,b],
        "source_tree_count_changed_plus_0x24":len(changing[0x24]),
        "source_tree_count_changed_plus_0x2C":len(changing[0x2C]),
        "source_tree_count_changed_in_both_0x24_0x2C":len(both),
        "source_tree_count_changed_plus_0x48":len(changing[0x48]),
        "source_tree_count_changed_plus_0x4C":len(changing[0x4C]),
        "source_tree_count_changed_plus_0x50":len(changing[0x50]),
        "source_tree_11_38_40_membership_in_24_2c_cochange":{
            str(i):i in both for i in (11,38,40)},
        "_indices_internal":both,
        "source_tree_field_is_collision_event_proven":False,
    }


def summarize(recovered,data):
    if set(recovered["trial_intents"])!=set(data) or not data:
        raise ValueError("Original source trial manifests inconsistent")
    trials={}
    actives={}
    for name in recovered["trial_intents"]:
        item=data[name]
        ball,nested,tree=original_streams(item["rows"])
        stage=phases(ball)
        interval=active_interval_tree_changes(tree,stage)
        actives[name]=interval.pop("_indices_internal",set())
        trials[name]={
            "operator_observed_contact_not_native":
                item["manifest"]["operator_observed_contact_region"],
            "source_ball_plus_0x30_candidate_movement_run":
                stage["run"],
            "candidate_displacement_response_with_signed_ratio":
                speed_proxy(ball,item["rows"],stage),
            "phase_conditioned_copy_and_lag_audit":source_aliases(
                ball,nested,stage),
            "tree_record_word_type_categories":tree_fields(tree),
            "tree_change_at_candidate_movement_start":interval,
        }
    intersection={
        "available":False,
        "native_tree_contact_marker_proven":False,
    }
    if set(data)==set(prior.TRIAL_ORDER) and all(
            trials[k]["tree_change_at_candidate_movement_start"]["available"]
            for k in prior.TRIAL_ORDER):
        a,b,c=(actives[k] for k in prior.TRIAL_ORDER)
        intersection={
            "available":True,
            "source_tree_24_2c_update_overlap_at_movement_start":{
                "both_contact_intents":len(a&b),
                "both_contact_intents_and_near_miss":len(a&b&c),
                "wood_intent_and_near_miss":len(a&c),
                "leaves_intent_and_near_miss":len(b&c),
                "all_distinct_source_tree_updates_in_three_trials":len(a|b|c),
            },
            "native_tree_contact_marker_proven":False,
        }
    return {
        "kind":"P0_TREE_CAPTURED_SOURCE_MEMORY_ONLY_CAUSAL_TRIAGE_V1",
        "status":"ORIGINAL_THREE_TRIAL_SHA_QUALIFIED_PHASE_CONDITIONAL_ANALYSIS",
        "original_capture_raw_sha_verified":
            recovered["original_private_raw_sha_and_sample_counts_verified"],
        "original_source_ball_packets":recovered["total_source_packets"],
        "original_full_tree_record_snapshots":
            recovered["total_94_tree_snapshots"],
        "per_trial":trials,
        "cross_trial_launch_aligned_tree_update_overlap":intersection,
        "source_selected_ball_is_rendered_ball_position_proven":False,
        "signed_displacement_ratio_is_true_physics_velocity_proven":False,
        "wood_versus_foliage_rest_coefficient_proven":False,
        "actual_collision_frame_verified":False,
        "native_colliding_tree_identity_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        recovered,data=base.read_trials(args.session)
        report=summarize(recovered,data)
        directory=base.integrity.qualified_session(args.session)
        target=directory/"tree-contact-memory-response-SAFE.json"
        with target.open("x",encoding="utf-8") as f:
            json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
            f.write("\n")
        print(json.dumps(report,sort_keys=True,separators=(",",":"),
                         allow_nan=False))
        print("MEMORY_RESPONSE_ANALYSIS_COMPLETE:",target.name)
        return 0
    except (OSError,ValueError,IndexError,OverflowError,TypeError,
            KeyError,struct.error,json.JSONDecodeError) as exc:
        print("ABSTAIN_MEMORY_RESPONSE_ANALYSIS:",type(exc).__name__,
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
