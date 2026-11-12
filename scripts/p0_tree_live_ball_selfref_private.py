#!/usr/bin/env python3
"""Offline P0 Golf active Ball pointer self-reference / cached-triplet audit.

The original, SHA-verified source ownership chain checked that the
selected Ball+0x4C points back to Ball+0x30. The NOV11 live recorder
instead checked that this nested pointer was bounded MEM2 but did not
recheck pointer equality. It reads the Ball blob first, then selected
record, then "nested" triplet in separate RPC operations.

This script re-verifies ALL original captured raw packets and SHA
through the existing recovery reader, then tests the actual native
record+0x88 Ball pointer and Ball+0x4C nested pointer against the
same Ball+0x30 address in every saved packet. No pointer/address values,
native bytes, game coordinates, ROM or source instructions are emitted.

If the pointer identity is verified, a Ball+0x30 / "nested" mismatch
does NOT establish an independent position object: it shows that two
separately timed reads of the SAME source address disagree, with
possible non-atomic guest updates (or weaker data-quality causes).
Dynamic Ball+0xCC/+0xF0/+0xFC byte aliases are investigated separately,
including one-sample lead/lag. This does not prove physics fields,
impact events or which state drives visuals.

No Dolphin, emulator connection, inputs, RAM reads/writes or video.
One exclusive new sanitized private SAFE report, original files unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import p0_tree_contact_memory_response_private as current
import analyze_p0_tree_contact_memory_private as base

BALL_PTR_OFFSET=0x88
SELF_PTR_OFFSET=0x4C
SELF_TRIPLET_OFFSET=0x30
WATCH=(0x30,0xCC,0xF0,0xFC,0xAC)


def word_at(b,off):
    if off%4 or len(b)<off+4:
        raise ValueError("Bounded private member missing")
    return int.from_bytes(b[off:off+4],"big")


def pointer_gate(ball_ptr,nested_ptr):
    if (not base.capture.in_bank(ball_ptr,base.capture.BALL_BYTES,"MEM2")
        or not base.capture.in_bank(nested_ptr,12,"MEM2")):
        raise ValueError("Saved source pointers not qualified in MEM2")
    return nested_ptr==ball_ptr+SELF_TRIPLET_OFFSET


def consecutive_lag_stats(seq,truth,moving):
    if len(seq)!=len(truth) or not len(seq):
        raise ValueError("Different source packet counts")
    return {
        "active_sample_count":len(moving),
        "active_exact_same_packet_matches":sum(
            seq[i]==truth[i] for i in moving),
        "active_exact_matches_to_prior_ball_sample":sum(
            i>0 and seq[i]==truth[i-1] for i in moving),
        "active_exact_matches_to_next_ball_sample":sum(
            i+1<len(seq) and seq[i]==truth[i+1] for i in moving),
    }


def audit_trial(rows):
    if len(rows)<2:
        raise ValueError("Insufficient original source packets")
    balls=base.decode_window(rows,*base.STREAMS["ball_candidate"])
    selected=base.decode_window(rows,*base.STREAMS["selected_record"])
    nested=base.decode_window(rows,*base.STREAMS["nested_translation_candidate"])
    ball_ptrs=[word_at(s,BALL_PTR_OFFSET) for s in selected]
    nested_ptrs=[word_at(b,SELF_PTR_OFFSET) for b in balls]
    comparisons=[pointer_gate(a,b) for a,b in zip(ball_ptrs,nested_ptrs)]
    moving=current.phases(balls)["moving"]
    truth=[b[SELF_TRIPLET_OFFSET:SELF_TRIPLET_OFFSET+12] for b in balls]
    byte_aliases={
        f"Ball+0x{off:03X}":consecutive_lag_stats(
            [b[off:off+12] for b in balls],truth,moving)
        for off in WATCH
    }
    nested_stats=consecutive_lag_stats(nested,truth,moving)
    idle=set(range(len(rows)))-moving
    nested_idle=sum(nested[i]==truth[i] for i in idle)
    return {
        "original_packet_count":len(rows),
        "source_selected_ball_ptr_stable_in_trial":len(set(ball_ptrs))==1,
        "source_ball_0x4C_nested_ptr_stable_in_trial":len(set(nested_ptrs))==1,
        "source_ball_0x4C_selfref_0x30_packet_count":sum(comparisons),
        "source_ball_0x4C_points_exactly_to_ball_0x30_all_original_packets":
            all(comparisons),
        "source_ball_pointer_or_nested_pointer_value_exposed":False,
        "moving_ball_candidate_sample_count":len(moving),
        "stationary_ball_candidate_sample_count":len(idle),
        "same_address_separate_rpc_nested_equals_ball_0x30_when_stationary":
            {"matches":nested_idle,"samples":len(idle)},
        "same_address_separate_rpc_nested_vs_ball_0x30_while_moving":
            nested_stats,
        "source_selected_ball_12_byte_cache_vs_ball_0x30_while_moving":
            byte_aliases,
        "the_recorder_read_ball_before_nested_rpc":True,
        "one_packet_lag_does_not_prove_one_guest_frame_lag":True,
        "guest_memory_atomicity_verified":False,
        "ball_world_position_or_velocity_verified":False,
    }


def analyze(recovered,trials):
    if set(trials)!=set(recovered["trial_intents"]):
        raise ValueError("Original private selected trial set changed")
    report={}
    ptrs=set()
    for name in recovered["trial_intents"]:
        rows=trials[name]["rows"]
        item=audit_trial(rows)
        report[name]=item
        selected=base.decode_window(rows,*base.STREAMS["selected_record"])
        ptrs.add(word_at(selected[0],BALL_PTR_OFFSET))
    all_selfref=all(x[
        "source_ball_0x4C_points_exactly_to_ball_0x30_all_original_packets"]
        for x in report.values())
    return {
        "kind":"P0_OPERATOR_TREE_SOURCE_SELECTED_BALL_SELFREF_AND_CACHE_COPY_AUDIT",
        "original_sha_verified":recovered[
            "original_private_raw_sha_and_sample_counts_verified"],
        "source_selected_ball_identity_equal_across_trials":len(ptrs)==1,
        "all_three_trials_ball_0x4C_exact_selfref_to_0x30":all_selfref,
        "nested_triplet_source_address_is_same_as_ball_0x30_verified":all_selfref,
        "nested_is_a_distinct_allocated_position_object_proven":False,
        "source_ball_0xCC_same_physics_frame_cache_semantics_proven":False,
        "per_trial":report,
        "original_source_ball_packets":recovered["total_source_packets"],
        "source_world_xyz_verified":False,
        "native_tree_wood_or_foliage_contact_verified":False,
        "contact_timing_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        recovered,data=base.read_trials(args.session)
        report=analyze(recovered,data)
        session=base.integrity.qualified_session(args.session)
        target=session/"tree-contact-ball-selfref-SAFE.json"
        with target.open("x",encoding="utf-8") as stream:
            json.dump(report,stream,indent=2,sort_keys=True,allow_nan=False)
            stream.write("\n")
        print(json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False))
        print("BALL_SELFREF_SOURCE_AUDIT_COMPLETE:",target.name)
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,
            OverflowError,json.JSONDecodeError) as exc:
        print("ABSTAIN_TREE_BALL_SELFREF_AUDIT:",type(exc).__name__,
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
