"""Private P0: compare selected-player 51-word record in one driver and wedge shot.

The existing #231 reader owns all seven-bank SHA/Rev1 scene/selected-source checks.
This module adds ONLY owner-stable selected-record masks, NOT a memory scanner.
Outputs relative offsets and booleans; no raw u32, pointers, vectors or hashes.
Human-labeled phases, no machine frame/time link. No Dolphin, writes or training.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

PHASES=(1,2,5,6,7)
RECORD_BYTES=roster.ROSTER_STRIDE
OFFSETS=tuple(range(0,RECORD_BYTES,4))

def capture(rd):
    src=seven._get(rd)
    u=rd.u32
    pm=u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec=pm+4+RECORD_BYTES*src["selected_index"]
    ball=u(rec+0x88)
    field=u(roster.GOLF_FIELD_STATIC)
    start=u(field+0x50)
    pin=u(field+0x44)
    config=u(roster.GOLF_CONFIG_STATIC)
    # Inherit seven._get()'s Rev1 pin/start/selected scene checks and add
    # owner identity checks required for interpreting 51 selected words.
    if (u(pm+0x334)!=rec or roster._bank(rec,RECORD_BYTES)!="MEM2"
            or roster._bank(ball,0x108)!="MEM2"
            or u(ball+0x4C)!=ball+0x30
            or roster._bank(start,0x50)!="MEM2"
            or u(start+0x4C)!=start+0x30
            or roster._bank(pin,0x50)!="MEM2"
            or u(pin+0x4C)!=pin+0x30):
        raise ValueError("selected record/ball/geometry source owner chain incomplete")
    src["owners"]=(pm,rec,ball,field,pin,start,config)
    return src

def changed(a,b):
    if len(a)!=len(OFFSETS) or len(b)!=len(OFFSETS):
        raise ValueError("required 51 word source record")
    return {offset for offset,(left,right) in zip(OFFSETS,zip(a,b)) if left!=right}

def fmt(offsets):
    return [f"+0x{x:03X}" for x in sorted(offsets)]

def controlled_pair(a,b):
    return (a["selected_index"]==b["selected_index"]
            and a["hole"]==b["hole"]
            and a["owners"]==b["owners"]
            and a["triplets"]["source_current_start"]==b["triplets"]["source_current_start"]
            and a["pin"]==b["pin"]
            and all(a[k]==b[k] for k in ("cfg_bc","cfg_c0","cfg_c4")))

def summarize(samples):
    if set(samples)!=set(PHASES):
        raise ValueError("expected exactly driver 1,2 and wedge 5,6,7")
    for n in PHASES:
        s=samples[n]
        if len(s["owners"])!=7 or len(s["whole_record"])!=51:
            raise ValueError("incomplete selected record")
        if type(s["selected_index"]) is not int or type(s["hole"]) is not int:
            raise ValueError("invalid scene/selected owner")
    for a,b in ((1,2),(5,6),(6,7),(5,7)):
        if not controlled_pair(samples[a],samples[b]):
            raise ValueError("shot owner/target/selector changed, cannot compare")

    dr=changed(samples[1]["whole_record"],samples[2]["whole_record"])
    early=changed(samples[5]["whole_record"],samples[6]["whole_record"])
    late=changed(samples[6]["whole_record"],samples[7]["whole_record"])
    net=changed(samples[5]["whole_record"],samples[7]["whole_record"])
    if not net.issubset(early|late):
        raise ValueError("record change-mask transitivity violation")
    returned=(early&late)-net
    # These are phase-correlated masks, NOT actual first-write timing.
    return {
        "kind":"P0-SEVEN-SELECTED-RECORD-51WORD-PHASE-MASK",
        "schema_version":1,
        "source_selected_record_words":51,
        "original_seven_bank_manifest_sha_gate_passed":True,
        "source_rev1_all_selected_owner_and_geometry_gates_passed":True,
        "human_shot_cohorts":[
            "D1_airborne_to_D2_stopped",
            "W5_near_apex_to_W6_descending_to_W7_flag_result",
        ],
        "driver_D1_to_D2_changed_word_count":len(dr),
        "driver_D1_to_D2_changed_relative_offsets":fmt(dr),
        "wedge_5_to_6_changed_word_count":len(early),
        "wedge_5_to_6_changed_relative_offsets":fmt(early),
        "wedge_6_to_7_changed_word_count":len(late),
        "wedge_6_to_7_changed_relative_offsets":fmt(late),
        "wedge_5_to_7_changed_word_count":len(net),
        "wedge_5_to_7_changed_relative_offsets":fmt(net),
        "wedge_changed_only_in_5_to_6_relative_offsets":fmt(early-late),
        "wedge_changed_only_in_6_to_7_relative_offsets":fmt(late-early),
        "wedge_changed_in_both_intervals_relative_offsets":fmt(early&late),
        "wedge_changed_then_returned_to_W5_relative_offsets":fmt(returned),
        "wedge_net_changes_overlap_driver_relative_offsets":fmt(net&dr),
        "wedge_net_changes_not_seen_in_driver_relative_offsets":fmt(net-dr),
        "driver_changes_not_seen_in_wedge_relative_offsets":fmt(dr-net),
        "wedge_phase_only_relative_offsets_are_causal_contact_flags":False,
        "selected_record_34_38_74_physical_semantics_verified":False,
        "physical_ball_xyz_verified":False,
        "shot_power_verified":False,
        "impact_state_verified":False,
        "ball_velocity_verified":False,
        "score_or_outcome_verified":False,
        "exact_frame_alignment_machine_verified":False,
        "same_boot_across_phase_machine_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
        "note":("Bitwise changed source-relative player-record offsets are only phase "
                "candidates; no numeric values, field types, physics or causation inferred. "
                "P3/D4 omitted: different club, input and pose."),
    }

def analyze(archive:Path):
    dirs=seven._check_archive(archive)  # ALL 14 original private SHA gates
    with ExitStack() as stack:
        samples={}
        for n in PHASES:
            banks=[]
            for j,size in enumerate(seven.SIZE):
                path=seven.src._file(dirs[n],f"{n}.{j+1}.raw",size)
                fp=stack.enter_context(path.open("rb"))
                banks.append(stack.enter_context(mmap.mmap(fp.fileno(),0,access=mmap.ACCESS_READ)))
            samples[n]=capture(roster.TwoBankReader(*banks))
        return summarize(samples)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=analyze(args.archive)
    except (ValueError,OSError,TypeError,KeyError,OverflowError):
        print("P0 source/record phase study ABSTAIN: private SHA, Rev1 or phase-control gate failed.",
              file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
