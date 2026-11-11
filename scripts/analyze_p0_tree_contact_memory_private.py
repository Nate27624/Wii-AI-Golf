#!/usr/bin/env python3
"""Deep OFFLINE memory differential of recorded WOOD / LEAVES / NEAR_MISS.

Uses ONLY previously saved private, SHA-256 checked source-selected Ball,
player-record, nested triplet and 94 tree-record samples. It cannot know
the exact impact frame or whether a changing field belongs to the
rendered ball: source ownership, float interpretation and motion semantics
remain independent questions. No Dolphin connection or input; original
recordings never modified.

Outputs an allowlisted aggregate with counts, source RELATIVE field
offsets, relative sample indices, and candidate-only observations.
No raw words/bytes, heap addresses, native PPC code, tree coordinates,
screen content or private paths. Per-word transition detection uses exact
big-endian u32 bit patterns. It does NOT estimate physical velocities.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import statistics
import subprocess
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import recover_p0_tree_contact_record_private as integrity
import p0_tree_contact_record_private as capture

STREAMS={
    "ball_candidate":("ball_object_candidate_be_hex_PRIVATE",capture.BALL_BYTES),
    "selected_record":("selected_record_be_hex_PRIVATE",capture.RECORD_BYTES),
    "nested_translation_candidate":(
        "nested_translation_candidate_be_hex_PRIVATE",12),
}
SOURCE_WATCH={
    "ball_candidate":{
        "candidate_plus_0x30":(0x30,12),
        "candidate_plus_0xAC_structural_copy_NOT_velocity":(0xAC,12),
        "candidate_plus_0xCC_cache_UNVERIFIED":(0xCC,12),
        "candidate_plus_0xF0_cache_UNVERIFIED":(0xF0,12),
        "candidate_plus_0xFC_cache_UNVERIFIED":(0xFC,12),
    },
    "selected_record":{
        "record_plus_0x3C_aim_candidate":(0x3C,4),
        "record_plus_0x54_initial_candidate":(0x54,12),
        "record_plus_0x60_start_copy_candidate":(0x60,12),
        "record_plus_0x88_ball_ptr":(0x88,4),
    },
    "nested_translation_candidate":{
        "nested_triplet_unverified_rendered_xyz":(0,12),
    }
}
TREE_STRIDE=capture.TREE_STRIDE
TREE_COUNT=capture.TREES
TREE_BYTES=capture.TREE_BYTES
MAX_TOP=16
MAX_SAMPLES=integrity.MAX_PACKETS
OBSERVATIONS=("wood","leaves","none","uncertain")
INTENTS=("wood","leaves","near_miss")


def rel(off):
    return f"+0x{off:03X}"


def decode_window(rows,key,n):
    result=[]
    for r in rows:
        raw=r.get(key)
        if not isinstance(raw,str) or len(raw)!=2*n:
            raise ValueError("Original native window length changed")
        b=bytes.fromhex(raw)
        if len(b)!=n:
            raise ValueError("Original native window truncated")
        result.append(b)
    return result


def word_transitions(windows):
    if not windows or len(windows[0])%4:
        raise ValueError("Unaligned source candidate samples")
    if any(len(b)!=len(windows[0]) for b in windows):
        raise ValueError("Mixed native candidate sizes")
    result={}
    for offset in range(0,len(windows[0]),4):
        seq=[w[offset:offset+4] for w in windows]
        changes=sum(a!=b for a,b in zip(seq,seq[1:]))
        result[offset]={
            "changes":changes,
            "distinct_patterns":len(set(seq)),
            "first_last_different":seq[0]!=seq[-1],
            "first_changed_after_sample_indices":[i for i in range(1,len(seq))
                if seq[i]!=seq[i-1]][:8],
        }
    return result


def frame_and_host_timing(rows):
    if len(rows)<2 or len(rows)>MAX_SAMPLES:
        raise ValueError("Need >=2 original source packets per trial")
    starts=[]
    ends=[]
    frames=[]
    prior_end=None
    prior_frame=None
    for i,row in enumerate(rows):
        if row.get("sample_index")!=i:
            raise ValueError("Nonsequential source sample")
        a=row.get("host_monotonic_start_ns")
        b=row.get("host_monotonic_end_ns")
        fs=row.get("bridge_frame_count_start")
        fe=row.get("bridge_frame_count_end")
        if any(type(v) is not int for v in (a,b,fs,fe)):
            raise ValueError("Original timestamp/frame bracket absent")
        if (a<0 or b<a or fs<0 or fe<fs or
            (prior_end is not None and a<prior_end) or
            (prior_frame is not None and fs<prior_frame)):
            raise ValueError("Original monotonic time/frame ordering invalid")
        starts.append(a)
        ends.append(b)
        frames.append(fe-fs)
        prior_end=b
        prior_frame=fe
    gaps=[(starts[i]-starts[i-1])/1e9 for i in range(1,len(starts))]
    spans=[(b-a)/1e9 for a,b in zip(starts,ends)]
    return {
        "sample_count":len(rows),
        "elapsed_host_seconds":round((ends[-1]-starts[0])/1e9,3),
        "inter_sample_start_gap_seconds_min_median_max":[
            round(min(gaps),3),round(statistics.median(gaps),3),
            round(max(gaps),3)],
        "non_atomic_read_span_seconds_median_max":[
            round(statistics.median(spans),3),round(max(spans),3)],
        "bridge_frame_bracket_width_median_max":[
            round(statistics.median(frames),1),max(frames)],
        "host_monotonic_timestamp_order_verified":True,
        "bridge_frame_count_is_guest_physics_frame_proven":False,
        "atomic_frame_or_contact_time_verified":False,
        "uniform_shot_input_or_launch_time_proven":False,
    }


def rank_word_candidates(windows,top=MAX_TOP):
    stats=word_transitions(windows)
    ordered=sorted(((offset,item) for offset,item in stats.items()
                    if item["changes"]>0),
                   key=lambda x:(-x[1]["changes"],
                                 -int(x[1]["first_last_different"]),x[0]))
    return {
        "word_slots_in_bounded_object":len(stats),
        "dynamic_word_slot_count":len(ordered),
        "dynamic_word_transitions_total":sum(x["changes"] for x in stats.values()),
        "top_dynamic_word_offsets":[
            {"object_relative_offset":rel(off),
             "adjacent_sample_transition_count":v["changes"],
             "distinct_bit_patterns":v["distinct_patterns"],
             "first_and_last_unequal":v["first_last_different"],
             "transition_after_sample_indices":v["first_changed_after_sample_indices"],
             "semantic_state_verified":False}
            for off,v in ordered[:top]],
        "beyond_top_dynamic_slot_count":max(0,len(ordered)-top),
    },stats


def watched_fields(windows,source_key):
    out={}
    for name,(offset,size) in SOURCE_WATCH[source_key].items():
        if offset%4 or size%4 or offset+size>len(windows[0]):
            raise ValueError("Source watch outside captured object")
        seq=[w[offset:offset+size] for w in windows]
        changed=[i for i in range(1,len(seq)) if seq[i]!=seq[i-1]]
        out[name]={
            "relative_offset":rel(offset),
            "byte_length":size,
            "distinct_exact_byte_patterns":len(set(seq)),
            "adjacent_sample_transition_count":len(changed),
            "first_last_different":seq[0]!=seq[-1],
            "transition_after_sample_indices":changed[:12],
            "rendered_ball_position_or_velocity_verified":False,
            "tree_contact_or_impulse_verified":False,
        }
    return out


def tree_dynamics(rows):
    snapshots=[]
    for r in rows:
        value=r.get("all_94_tree_records_be_hex_PRIVATE")
        if value is None:
            continue
        if not isinstance(value,str) or len(value)!=2*TREE_BYTES:
            raise ValueError("Source 94-tree snapshot incomplete")
        data=bytes.fromhex(value)
        if len(data)!=TREE_BYTES:
            raise ValueError("Source 94-tree snapshot truncated")
        # Every tree has one shared firstword in the source-qualified array.
        root=data[:4]
        if any(data[i*TREE_STRIDE:i*TREE_STRIDE+4]!=root
               for i in range(TREE_COUNT)):
            raise ValueError("Source 94-tree shared firstwords changed")
        snapshots.append((r["sample_index"],data))
    if len(snapshots)<1:
        raise ValueError("Original source tree snapshots missing")
    per_tree=Counter()
    per_member=Counter()
    per_tree_member=Counter()
    changed_048=set()
    changed_coord=set()
    changed_firstword=set()
    between=[]
    for (previous_index,before),(index,after) in zip(snapshots,snapshots[1:]):
        changed=set()
        changed_words=0
        for tree in range(TREE_COUNT):
            base=tree*TREE_STRIDE
            if before[base:base+TREE_STRIDE]==after[base:base+TREE_STRIDE]:
                continue
            changed.add(tree)
            for off in range(0,TREE_STRIDE,4):
                if before[base+off:base+off+4]==after[base+off:base+off+4]:
                    continue
                changed_words+=1
                per_tree[tree]+=1
                per_member[off]+=1
                per_tree_member[(tree,off)]+=1
                if off==0:
                    changed_firstword.add(tree)
                if off==0x48:
                    changed_048.add(tree)
                if off in (0x30,0x34,0x38):
                    changed_coord.add(tree)
        between.append({
            "earlier_sample_index":previous_index,
            "later_sample_index":index,
            "source_tree_objects_with_any_change":len(changed),
            "changed_tree_word_slots":changed_words,
        })
    first=snapshots[0][1]
    last=snapshots[-1][1]
    final_changed=sum(first[i*TREE_STRIDE:(i+1)*TREE_STRIDE]!=
                      last[i*TREE_STRIDE:(i+1)*TREE_STRIDE]
                      for i in range(TREE_COUNT))
    return {
        "tree_snapshot_count":len(snapshots),
        "source_tree_count":TREE_COUNT,
        "source_tree_stride_bytes":TREE_STRIDE,
        "source_tree_snapshots_sample_indices":[i for i,_ in snapshots],
        "tree_objects_with_any_observed_word_changes":len(per_tree),
        "tree_objects_different_first_to_last":final_changed,
        "shared_firstword_changed_tree_count":len(changed_firstword),
        "tree_candidate_plus_0x48_word_changed_tree_count":len(changed_048),
        "tree_candidate_plus_0x30_triplet_changed_tree_count":len(changed_coord),
        "changed_tree_word_offset_counts":[
            {"tree_record_relative_word_offset":rel(off),"transition_count":count}
            for off,count in sorted(per_member.items(),key=lambda x:(-x[1],x[0]))[:16]],
        "top_dynamic_tree_array_indices":[
            {"tree_array_index":idx,"word_transition_count":count}
            for idx,count in sorted(per_tree.items(),key=lambda x:(-x[1],x[0]))[:16]],
        "tree_snapshot_pair_changes":between,
        "tree_candidate_plus_0x48_is_collision_event_proven":False,
        "tree_translation_field_is_impact_geometry_proven":False,
    },first,last,per_tree_member


def read_trials(session):
    recovered,folder=integrity.recover(session)
    if len(recovered["trials"])<1:
        raise ValueError("No original recorded trials")
    trial_dir={}
    for item in folder.iterdir():
        match=integrity.SUBDIR.fullmatch(item.name)
        if match and item.is_dir():
            trial_dir[match.group(1)]=item
    expected=set(recovered["trial_intents"])
    if set(trial_dir)!=expected:
        raise ValueError("Original candidate trial folders inconsistent")
    data={}
    for kind in recovered["trial_intents"]:
        trial=trial_dir[kind]
        manifest=json.loads((trial/"trial-summary-PRIVATE.json").read_text(
            encoding="utf-8"))
        with (trial/"candidate-stream-RAW-PRIVATE.jsonl").open(
                "r",encoding="utf-8") as f:
            rows=[json.loads(line) for line in f]
        if len(rows)!=manifest["sample_count"]:
            raise ValueError("Original source packet count changed")
        data[kind]={"rows":rows,"manifest":manifest,"directory":trial}
    return recovered,data


def compare_against_control(trials):
    if not all(x in trials for x in INTENTS):
        return {
            "available":False,
            "reason":"Require exactly one original wood leaves and near_miss trial",
            "native_collision_or_contact_verified":False,
        }
    source_results={}
    for family in STREAMS:
        w=trials["wood"]["word_stats"][family]
        l=trials["leaves"]["word_stats"][family]
        n=trials["near_miss"]["word_stats"][family]
        all_offsets=sorted(set(w)|set(l)|set(n))
        both=[]
        one=[]
        common=[]
        for off in all_offsets:
            a,b,c=w[off]["changes"],l[off]["changes"],n[off]["changes"]
            if a and b and not c:
                both.append((off,a,b,c))
            if (bool(a)^bool(b)) and not c:
                one.append((off,a,b,c))
            if a and b and c:
                common.append((off,a,b,c))
        def top(items):
            return [{
                "source_object_relative_word_offset":rel(off),
                "wood_intent_transition_count":a,
                "leaves_intent_transition_count":b,
                "near_miss_transition_count":c,
                "independently_verified_collision_state":False}
                for off,a,b,c in sorted(items,key=lambda x:(-(x[1]+x[2]),x[0]))[:MAX_TOP]]
        source_results[family]={
            "dynamic_in_both_contact_intents_but_static_in_near_miss_count":len(both),
            "dynamic_in_exactly_one_contact_intent_but_static_in_near_miss_count":len(one),
            "dynamic_in_all_three_trials_count":len(common),
            "top_both_vs_near_miss_candidates":top(both),
            "top_single_intent_only_vs_near_miss_candidates":top(one),
            "transition_patterns_are_not_impact_labels":True,
        }
    return {
        "available":True,
        "contact_comparison_family_results":source_results,
        "unequal_lengths_and_inputs_are_confounders":True,
        "native_collision_or_contact_verified":False,
        "independently_matched_launch_profile_verified":False,
    }


def video_meta(path):
    if not path.exists() or path.is_symlink() or path.stat().st_size==0:
        return {"source_video_exists":False,"visual_event_reviewed":False}
    result={"source_video_exists":True,
            "visual_event_reviewed":False,
            "contact_timestamp_aligned_to_ram":False}
    exe=shutil.which("ffprobe")
    if not exe:
        result["ffprobe_metadata_available"]=False
        return result
    try:
        p=subprocess.run([exe,"-v","error","-select_streams","v:0",
                "-show_entries","stream=width,height,nb_frames,avg_frame_rate,duration",
                "-of","json",str(path)],
            capture_output=True,text=True,timeout=8,check=True)
        metadata=json.loads(p.stdout)
        streams=metadata.get("streams",[])
        if not streams or not isinstance(streams[0],dict):
            raise ValueError("Video stream metadata absent")
        stream=streams[0]
        result["ffprobe_metadata_available"]=True
        result["video_width_px"]=stream.get("width")
        result["video_height_px"]=stream.get("height")
        result["video_frame_count_unverified"]=stream.get("nb_frames")
        # Without a common frame-clock anchor, video frame numbers cannot
        # be assigned to the asynchronously captured memory samples.
        rawdur=stream.get("duration")
        try:
            value=float(rawdur)
            result["video_duration_seconds"]=round(value,2) if math.isfinite(value) else None
        except (ValueError,TypeError):
            result["video_duration_seconds"]=None
    except (OSError,subprocess.SubprocessError,ValueError,json.JSONDecodeError):
        result["ffprobe_metadata_available"]=False
    return result


def analyze(recovered,trials):
    if len(recovered.get("trials",[]))!=len(trials) or set(
            recovered["trial_intents"])!=set(trials):
        raise ValueError("Original SHA-qualified trial manifest mismatch")
    per={}
    firsts={}
    tree_firsts={}
    for kind in recovered["trial_intents"]:
        rows=trials[kind]["rows"]
        manifest=trials[kind]["manifest"]
        timing=frame_and_host_timing(rows)
        sources={}
        stats={}
        for family,(key,size) in STREAMS.items():
            windows=decode_window(rows,key,size)
            overview,stat=rank_word_candidates(windows)
            overview["source_watched_fields_NOT_verified_physics"]=watched_fields(
                windows,family)
            sources[family]=overview
            stats[family]=stat
            firsts[(kind,family)]=windows[0]
        trees,first,last,tree_words=tree_dynamics(rows)
        tree_firsts[kind]=first
        if (timing["sample_count"]!=manifest.get("sample_count") or
                trees["tree_snapshot_count"]!=manifest.get("tree_snapshot_count")):
            raise ValueError("Source sample and tree counts inconsistent")
        per[kind]={
            "trial_intent":kind,
            "operator_observed_contact_region":manifest.get(
                "operator_observed_contact_region"),
            "operator_reported_trajectory_changed":manifest.get(
                "operator_observed_trajectory_changed"),
            "time_and_frame_brackets":timing,
            "candidate_object_word_dynamics":sources,
            "tree_record_dynamics":trees,
            "video_metadata":video_meta(
                trials[kind]["directory"]/"dolphin-window-PRIVATE.mp4"),
            "not_a_native_impact_detector":True,
        }
        trials[kind]["word_stats"]=stats
        trials[kind]["tree_transition_stats"]=tree_words
    ordered=recovered["trial_intents"]
    reference=ordered[0]
    baseline={
        "reference_trial_intent":reference,
        "other_trials":[{
            "trial_intent":kind,
            "first_packet_source_object_exact_byte_equality_to_reference":{
                family:firsts[(reference,family)]==firsts[(kind,family)]
                for family in STREAMS},
            "first_94_tree_snapshot_exact_byte_equality_to_reference":
                tree_firsts[reference]==tree_firsts[kind],
        } for kind in ordered[1:]],
        "pre_shot_savestate_equality_verified":False,
        "same_launch_power_verified":False,
    }
    # An index is simply the stable source tree-array element, not an
    # independently matched trunk or foliage collider.
    tree_contact_candidates={}
    if all(kind in trials for kind in INTENTS):
        t={kind:trials[kind]["tree_transition_stats"] for kind in INTENTS}
        both=[(i,off,t["wood"][(i,off)],t["leaves"][(i,off)])
              for i in range(TREE_COUNT) for off in range(0,TREE_STRIDE,4)
              if t["wood"][(i,off)]>0 and t["leaves"][(i,off)]>0
              and t["near_miss"][(i,off)]==0]
        tree_contact_candidates={
            "dynamic_same_tree_word_in_both_contact_intents_but_static_near_miss_count":len(both),
            "top_tree_word_candidates":[{
                "source_tree_array_index":i,"record_relative_word_offset":rel(off),
                "wood_trial_transitions":a,"leaves_trial_transitions":b,
                "near_miss_transitions":0,
                "source_tree_is_contacted_tree_proven":False}
                for i,off,a,b in sorted(both,key=lambda x:(-x[2]-x[3],x[0],x[1]))[:MAX_TOP]],
            "observed_tree_memory_change_is_collision_response_proven":False,
        }
    return {
        "kind":"P0_TREE_OPERATOR_TRIALS_DEEP_MEMORY_DIFFERENTIAL_V1",
        "status":"ORIGINAL_SHA_QUALIFIED_OFFLINE_CANDIDATE_DYNAMICS",
        "original_private_raw_sha_and_sample_counts_verified":
            recovered["original_private_raw_sha_and_sample_counts_verified"],
        "observed_wood_leaf_contact_labels_from_operator_not_code":True,
        "original_total_ball_samples":sum(
            x["time_and_frame_brackets"]["sample_count"] for x in per.values()),
        "original_total_tree_snapshots":sum(
            x["tree_record_dynamics"]["tree_snapshot_count"] for x in per.values()),
        "trial_intents_preserved_instead_of_assuming_contact":list(ordered),
        "per_trial":per,
        "cross_trial_original_start_state_bitwise_comparisons":baseline,
        "contact_vs_no_contact_candidate_word_differentials":
            compare_against_control(trials),
        "source_tree_word_differentials":tree_contact_candidates,
        "native_tree_impact_event_verified":False,
        "native_wood_vs_leaves_material_branch_verified":False,
        "rendered_ball_xyz_verified_by_this_capture":False,
        "ball_velocity_or_impulse_proven":False,
        "same_guest_physics_frame_verified":False,
        "tree_hitbox_dimensions_verified":False,
        "matched_power_pose_wind_and_savestate_verified":False,
        "training_approved":False,
        "caveat":"These are source-selected RAM bit-pattern transitions sampled nonatomically, not verified launch/impact frames, geometry, velocities, or independent wood/leaf collision labels."
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        recovered,trial_data=read_trials(args.session)
        report=analyze(recovered,trial_data)
        session=integrity.qualified_session(args.session)
        target=session/"tree-contact-deep-memory-SAFE.json"
        with target.open("x",encoding="utf-8") as fh:
            json.dump(report,fh,indent=2,sort_keys=True,allow_nan=False)
            fh.write("\n")
        print(json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False))
        print("OFFLINE_ANALYSIS_COMPLETE: created",target.name,
              "(no native bytes/addresses/coordinates in output)")
        return 0
    except (OSError,ValueError,TypeError,IndexError,KeyError,
            OverflowError,json.JSONDecodeError) as exc:
        print("ABSTAIN_DEEP_TREE_MEMORY_ANALYSIS: "+type(exc).__name__,
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
