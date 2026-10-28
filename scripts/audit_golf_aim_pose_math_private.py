"""PRIVATE source-gated selected-player pose/aim math: B0 idle, B1 idle, B2 aim, B3 idle.

Checks whether five 2D rotation-shaped floats and twelve vector/quaternion-
shaped floats keep their mathematical constraints during the operator's
visible WASD movement. Real decoded field meanings remain UNVERIFIED.
Reuses #163 source reader and preserved local B0–B3 manifest. No Dolphin,
controller, RAM modification, game bytes, float values, private paths or
runtime heap pointers in stdout.
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

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_four_phase_private as phases

FIELD_OFFSETS = (
    0x03C, 0x040, 0x044, 0x048, 0x04C,
    0x090, 0x094, 0x098, 0x09C, 0x0A0, 0x0A4, 0x0A8,
    0x0AC, 0x0B0, 0x0B4, 0x0B8, 0x0BC, 0x0C0,
)
PHASES = ("B0", "B1", "B2", "B3")
REQUIRED_KEYS = ("angle", "rot2", "location_like", "quaternion_a",
                 "quaternion_b", "scalar", "idle_confound", "selected_index",
                 "hole", "other_slot_words")


def _read_f32(read, addr):
    word = read(addr)
    val = struct.unpack(">f",struct.pack(">I",word))[0]
    if not math.isfinite(val) or abs(val)>1e10:
        raise ValueError("Invalid or unbounded candidate float")
    return val


def _one(reader):
    safe, private = selected.analyze_one(reader.u32, reader.header())
    if not (
        safe["selected_record_pointer_matches_code_defined_stride"]
        and safe["selected_ball_translation_pointer_is_mem2"]
        and safe["source_current_start_translation_pointer_is_mem2"]
        and safe["record_candidate_triplet_finite_bounded"]
        and safe["nested_ball_candidate_triplet_finite_bounded"]
    ):
        raise ValueError("Source-anchored selected player/ball gate failed")
    u=reader.u32
    pm=u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    idx=private["selected_index"]
    rec=pm+4+idx*roster.ROSTER_STRIDE
    if idx not in range(4) or u(pm+0x334)!=rec or roster._bank(rec,0xCC)!="MEM2":
        raise ValueError("Source-indexed selected record invalid")
    f=lambda offset:_read_f32(u,rec+offset)
    peers=[]
    for slot in range(4):
        if slot==idx:
            continue
        record=pm+4+slot*roster.ROSTER_STRIDE
        if roster._bank(record,0xCC)!="MEM2":
            raise ValueError("Unselected slot not mapped")
        peers.append(tuple(u(record+off) for off in FIELD_OFFSETS))
    return {
        "angle":f(0x3c),
        "rot2":tuple(f(o) for o in (0x40,0x44,0x48,0x4c)),
        "idle_confound":u(rec+0x90),
        "location_like":tuple(f(o) for o in (0x94,0x98,0x9c)),
        "quaternion_a":tuple(f(o) for o in (0xa0,0xa4,0xa8,0xac)),
        "quaternion_b":tuple(f(o) for o in (0xb0,0xb4,0xb8,0xbc)),
        "scalar":u(rec+0xc0),
        "selected_index":idx,
        "hole":private["hole"],
        "other_slot_words":tuple(peers),
    }


def _metrics(s):
    a,b,c,d=s["rot2"]
    ang=s["angle"]
    expected=(math.sin(ang),math.cos(ang),
              -math.cos(ang),math.sin(ang))
    residual=max(abs(x-y) for x,y in zip((a,b,c,d),expected))
    det=a*d-b*c
    q1_norm=math.sqrt(sum(x*x for x in s["quaternion_a"]))
    q2_norm=math.sqrt(sum(x*x for x in s["quaternion_b"]))
    return {
        "sincos_matrix_max_absolute_residual":round(residual,8),
        "rotation_determinant_abs_error_from_one":round(abs(det-1),8),
        "first_quaternion_norm_abs_error_from_one":round(abs(q1_norm-1),8),
        "second_quaternion_norm_abs_error_from_one":round(abs(q2_norm-1),8),
        "two_dimensional_angle_matrix_consistent_with_sincos": residual<=0.002,
        "two_dimensional_matrix_determinant_near_one":abs(det-1)<=0.002,
        "both_quaternion_like_groups_near_unit_norm":
            abs(q1_norm-1)<=0.002 and abs(q2_norm-1)<=0.002,
    }


def _changed_components(a,b):
    return sum(x!=y for x,y in zip(a,b))


def summarize(samples, *,
              visible_aim=False, operator_same_session=False,
              bank_pairs_distinct=False):
    if (len(samples)!=4
            or any(not all(k in s for k in REQUIRED_KEYS) for s in samples)
            or any(type(v) is not bool for v in (
                visible_aim,operator_same_session,bank_pairs_distinct))):
        raise ValueError("Four gated paired samples and typed provenance required")
    if len({s["selected_index"] for s in samples})!=1 or len(
            {s["hole"] for s in samples})!=1:
        raise ValueError("Source-selected slot or hole changed")
    if any(len(s["rot2"])!=4 or len(s["location_like"])!=3
           or len(s["quaternion_a"])!=4 or len(s["quaternion_b"])!=4
           or len(s["other_slot_words"])!=3 for s in samples):
        raise ValueError("Candidate field width mismatch")
    if any(not all(math.isfinite(v) for v in (
            s["angle"],*s["rot2"],*s["location_like"],
            *s["quaternion_a"],*s["quaternion_b"])) for s in samples):
        raise ValueError("Nonfinite mathematical operand")
    metrics=[_metrics(s) for s in samples]
    changes=[]
    for i in range(3):
        a,b=samples[i:i+2]
        changes.append({
            "transition":f"{PHASES[i]}_to_{PHASES[i+1]}",
            "angle_word_changed":a["angle"]!=b["angle"],
            "rotation2_component_change_count":
                _changed_components(a["rot2"],b["rot2"]),
            "location_like_vec3_component_change_count":
                _changed_components(a["location_like"],b["location_like"]),
            "first_quaternion_component_change_count":
                _changed_components(a["quaternion_a"],b["quaternion_a"]),
            "second_quaternion_component_change_count":
                _changed_components(a["quaternion_b"],b["quaternion_b"]),
            "unknown_scalar_changed":a["scalar"]!=b["scalar"],
            "idle_confound_word_changed":
                a["idle_confound"]!=b["idle_confound"],
            "unselected_slot_words_changed_count":sum(
                _changed_components(p,q)
                for p,q in zip(a["other_slot_words"],b["other_slot_words"])),
        })
    basis=["angle_word_changed","rotation2_component_change_count",
           "location_like_vec3_component_change_count",
           "first_quaternion_component_change_count",
           "second_quaternion_component_change_count",
           "unknown_scalar_changed"]
    no_idle=all(not changes[0][k] and not changes[2][k] for k in basis)
    aim_change=all(changes[1][k] for k in basis)
    quats_ok=all(x["both_quaternion_like_groups_near_unit_norm"] for x in metrics)
    rot_ok=all(x["two_dimensional_angle_matrix_consistent_with_sincos"]
               and x["two_dimensional_matrix_determinant_near_one"]
               for x in metrics)
    nonselected_static=all(
        x["unselected_slot_words_changed_count"]==0 for x in changes)
    return {
        "schema_version":1,
        "kind":"local-private-selected-player-aim-pose-math-four-phase",
        "game_id":"RSPE01","revision":1,"mode":4,
        "source_selected_record_and_nested_ball_validated_each_phase":True,
        "observed_phases":list(PHASES),
        "selected_index_unchanged":True,"hole_unchanged":True,
        "all_native_bank_pairs_changed":bank_pairs_distinct,
        "operator_reports_aim_visibly_moved":visible_aim,
        "operator_reports_same_session":operator_same_session,
        "selected_phase_math":metrics,
        "phase_changes":changes,
        "rotation2_matrix_consistent_all_phases":rot_ok,
        "two_quaternion_like_groups_near_unit_norm_all_phases":quats_ok,
        "unselected_slots_static_in_target_offsets":nonselected_static,
        "selected_pose_fields_stable_in_idle_controls":no_idle,
        "selected_pose_fields_changed_during_visible_aim":aim_change,
        "pose_like_structure_supported_by_no_shot_evidence":
            bool(no_idle and aim_change and rot_ok and quats_ok
                 and nonselected_static and visible_aim
                 and operator_same_session and bank_pairs_distinct),
        "typed_actual_aim_angle_verified":False,
        "typed_quaternion_or_position_semantics_verified":False,
        "club_head_pose_verified":False,
        "ball_motion_or_world_xyz_verified":False,
        "real_swing_power_verified":False,
        "approved_for_training":False,
        "allowed_to_publish":False,
        "next_action":"Source-trace writes to selected record +0x03C..+0x04C "
            "and +0x094..+0x0C0 and test independent opposite WASD aim "
            "directions before typed angle/quaternion semantics. "
            "Do not infer shot power or ball XYZ."
    }


def run_local(folder,*,visible_aim=False,operator_same_session=False):
    folder=Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing private B0-B3 session folder")
    root=selected.DATA_ROOT.resolve(strict=True)
    actual=folder.resolve(strict=True)
    if actual==root or not actual.is_relative_to(root):
        raise ValueError("Study must remain inside ignored private Data root")
    meta=phases._validate_manifest(actual)
    snapshots=[]
    hashes=[]
    with ExitStack() as stack:
        for phase in PHASES:
            files=[phases._approved_bank(
                    actual,f"{phase}-MEM{j}.bin",
                    roster.MEM1_SIZE if j==1 else roster.MEM2_SIZE)
                   for j in (1,2)]
            digest={key:phases._hash(f) for key,f in
                    zip(("MEM1","MEM2"),files)}
            if digest!=meta[phase]["sha256"]:
                raise ValueError("Private snapshot differs from manifest")
            hashes.append(digest)
            images=[]
            for f in files:
                fp=stack.enter_context(f.open("rb"))
                images.append(stack.enter_context(mmap.mmap(
                    fp.fileno(),0,access=mmap.ACCESS_READ)))
            reader=roster.TwoBankReader(*images)
            snapshots.append(_one(reader))
    differ=all(hashes[i][bank]!=hashes[i+1][bank]
               for i in range(3) for bank in ("MEM1","MEM2"))
    return summarize(
        snapshots,visible_aim=visible_aim,
        operator_same_session=operator_same_session,
        bank_pairs_distinct=differ)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",type=Path,required=True)
    p.add_argument("--aim-visibly-moved",action="store_true")
    p.add_argument("--operator-same-session",action="store_true")
    args=p.parse_args(argv)
    try:
        report=run_local(args.private_root,
                         visible_aim=args.aim_visibly_moved,
                         operator_same_session=args.operator_same_session)
    except (OSError,ValueError,TypeError,OverflowError,KeyError,struct.error):
        print("Private aim-math study refused unsafe source identity "
              "or checkpoint pair; no raw memory or path disclosed.",
              file=sys.stderr)
        return 1
    print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
