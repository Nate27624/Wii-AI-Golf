#!/usr/bin/env python3
"""P0 Golf-specific sequence-manager phase POINTER RELATIONSHIPS (offline).

Do not conflate RPGolSequenceManager with RPSportsSequenceMgr score-table
instance. Public Kokeshi *provisional* type layout: Golf singleton static
0x804BF920, Training1/2/3 fields +0x0C/10/14, active phase +0x18.
Actual RSPE01 Rev1 field types, training-number mapping and displayed result
are not verified here. Reads ONLY fixed documented offsets after source
selected mode4 and entire original seven-pair archive SHA gates from #231.
No raw pointers, RAM, hashes, phase notes, scores or code words emitted.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as source
import audit_golf_two_bank_roster_private as roster

GOLF_SEQUENCE_SINGLETON_STATIC = 0x804BF920
MANAGER_MIN_SIZE = 0x1C
TRAINING_FIELDS = (0x0C, 0x10, 0x14)
PHASE_FIELD = 0x18
EDGES = ((1, 2), (3, 4), (5, 6), (6, 7), (5, 7))

def _resolved_pointer(p: int):
    """Return categorical pointer class. NO pointer dereference/print."""
    if type(p) is not int or not 0 <= p <= 0xFFFFFFFF:
        raise ValueError("unqualified pointer word")
    return "NULL" if p == 0 else (
        "IN_NATIVE_RAM" if roster._bank(p) in ("MEM1","MEM2")
        else "OUTSIDE_CAPTURED_RAM_OR_UNALIGNED")

def _observation(read_u32, source_ctx):
    if type(source_ctx) is not dict:
        raise ValueError("source context missing")
    slot = source_ctx["selected_index"]
    hole = source_ctx["hole"]
    if type(slot) is not int or not 0 <= slot <= 3 or type(hole) is not int or not 0 <= hole <= 8:
        raise ValueError("Golf mode4 source-selection context invalid")
    # seven._get has already source-gated mode4, scene 5, selected ball,
    # pin/start and Config selectors, but does not type sequence fields.
    seq = read_u32(GOLF_SEQUENCE_SINGLETON_STATIC)
    owner_class = _resolved_pointer(seq)
    if seq == 0:
        return {"slot":slot,"hole":hole,"owner":None,"pointers":None,
                "owner_class":owner_class,
                "pointer_classes":None}
    if roster._bank(seq, MANAGER_MIN_SIZE) not in ("MEM1","MEM2"):
        raise ValueError("Golf sequence singleton object out of bounded native RAM")
    # Typed member aliases NOT proven; only fixed header-proposed offsets.
    values = tuple(read_u32(seq+off) for off in (*TRAINING_FIELDS, PHASE_FIELD))
    classes = tuple(_resolved_pointer(value) for value in values)
    return {"slot":slot,"hole":hole,"owner":seq,"pointers":values,
            "owner_class":owner_class,"pointer_classes":classes}

def summarize(samples: dict):
    if type(samples) is not dict or set(samples) != set(range(1,8)):
        raise ValueError("exactly seven canonical numbered captures required")
    records=[]
    for n in range(1,8):
        s=samples[n]
        if type(s) is not dict or s.get("owner_class") not in ("NULL","IN_NATIVE_RAM"):
            raise ValueError("malformed sequence sample owner")
        values=s.get("pointers")
        if values is not None:
            if (type(values) is not tuple or len(values) != 4
                    or type(s["pointer_classes"]) is not tuple
                    or len(s["pointer_classes"]) != 4):
                raise ValueError("malformed source offset classes")
            eq_indices = tuple(i for i in range(3) if values[3] == values[i]
                               and values[3] != 0)
            training_distinct = len(set(x for x in values[:3] if x)) == sum(bool(x) for x in values[:3])
            phase_is_owning_manager = values[3] == s["owner"]
        else:
            if s.get("owner") is not None or s.get("pointer_classes") is not None:
                raise ValueError("manager absent but member fields present")
            eq_indices=tuple()
            training_distinct=None
            phase_is_owning_manager=None
        records.append({
            "numbered_capture":n,
            "GolfSequenceManager_singleton":s["owner_class"],
            "training_1_2_3_pointer_classes":list(s["pointer_classes"][:3]) if values is not None else None,
            "active_phase_pointer_class":s["pointer_classes"][3] if values is not None else None,
            "active_phase_equals_training_root_indices":list(eq_indices),
            "non_null_training_roots_pairwise_distinct":training_distinct,
            "active_phase_equals_manager_pointer":phase_is_owning_manager,
            "active_phase_can_be_nested_subobject_not_direct_root_alias":True,
        })
    edges=[]
    for a,b in EDGES:
        x,y=samples[a],samples[b]
        both = x["owner"] is not None and y["owner"] is not None
        owner_equal = x["owner"] == y["owner"] if both else None
        entries = (
            [x["pointers"][j] == y["pointers"][j] for j in range(4)]
            if both and owner_equal else None
        )
        edges.append({
            "numbered_edge":f"{a}_to_{b}",
            "source_selected_slot_and_hole_equal":(
                x["slot"] == y["slot"] and x["hole"] == y["hole"]),
            "GolfSequenceManager_present_both":both,
            "GolfSequenceManager_singleton_pointer_equal":owner_equal,
            "training_1_2_3_and_active_phase_pointer_equal_by_field":entries,
            "active_phase_pointer_changed_when_same_owner":(
                not entries[3] if entries is not None else None),
            "human_phase_file_labels_machine_verified":False,
        })
    return {
        "kind":"P0-GOLF-NEARPIN-SEQUENCE-POINTER-COHORT-V1",
        "game_id":"RSPE01","disc_revision":1,"mode4_source_selected_gated":True,
        "original_14_bank_archive_sha_pre_and_post_verified":True,
        "public_struct_source":"Kokeshi RPGolSequenceManager provisional header",
        "GolfSequenceManager_static_is_distinct_from_RPSportsSequenceMgr":True,
        "training_member_offsets_source_native_rev1_proven":False,
        "nearpin_sequence_training_number_verified":False,
        "active_phase_cpp_type_or_nested_alias_verified":False,
        "same_boot_or_guest_frame_verified":False,
        "on_screen_result_or_backing_state_verified":False,
        "ball_world_xyz_velocity_power_contact_verified":False,
        "training_approved":False,"allowed_to_publish":False,
        "records":records,"numbered_edges":edges,
    }

def audit(archive: Path):
    original = source._check_archive(archive)
    with ExitStack() as stack:
        observations={}
        for n in range(1,8):
            maps=[]
            for i,size in enumerate(source.SIZE):
                path=source.src._file(original[n],f"{n}.{i+1}.raw",size)
                f=stack.enter_context(path.open("rb"))
                maps.append(stack.enter_context(
                    mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)))
            rd=roster.TwoBankReader(*maps)
            # Inherited _get is the original bytecode/scene/mode source gate.
            base=source._get(rd)
            observations[n]=_observation(rd.u32,base)
        result=summarize(observations)
    # Catch original native archive changes during inspection.
    source._check_archive(archive)
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        result=audit(args.archive)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,AttributeError):
        print("P0_GOLF_SEQUENCE_POINTER_ABSTAIN: original 14-bank SHA, scene/mode or bounded sequence structure invalid",
              file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
