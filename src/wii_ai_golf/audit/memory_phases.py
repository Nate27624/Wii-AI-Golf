"""Pure offline differential summary for phase-labelled Wii Sports Golf RAM captures.

Only publishes relative offsets, change counts and observation labels; never raw
RAM, runtime pointers, disc images, local file paths or inferred game power.
"""
from __future__ import annotations
from collections import defaultdict
import math
import re
import struct

ALLOWED_PHASES=frozenset({"idle","aim_only","a_hold","club_motion","shot_attempt","settled","pre","post"})
ALLOWED_OBSERVATIONS=frozenset({"unchanged","camera_moved","club_moved","ball_hit","no_contact","unknown"})
WINDOW_LENGTHS={
    "focused":{"golf_config":0xA0,"golf_field":0xA8,"sports_sequence":0xD0},
    "broad":{"golf_config":0x1C74,"golf_field":0xA8,"sports_sequence":0xD0},
}
OPTIONAL_EFFECTS=frozenset({"minimap_ball_effect","minimap_player_effect","minimap_shot_line_effect"})
MAX_CAPTURE_SAMPLES=240

def normalize_legacy_outcome_rows(rows):
    """Preserve old pre/post/settled labels with NO inferred contact/power."""
    if not isinstance(rows,list) or not 2<=len(rows)<=MAX_CAPTURE_SAMPLES:
        raise ValueError("require 2..240 source observations")
    stages={"pre":0,"post":1,"settled":2}
    result=[]
    for row in rows:
        if not isinstance(row,dict) or row.get("source")!="Felk-read-only-US-Rev1-unverified-golf-windows":
            raise ValueError("not a legacy S002 outcome memory record")
        phase=row.get("phase")
        if phase not in stages:raise ValueError("invalid legacy phase")
        result.append({**row,"stage":stages[phase]})
    return result


def documented_role(name,offset):
    """Source labels are structural facts, not a club/power decoder."""
    if name=="golf_config":
        if 0x04<=offset<0x94:return "hole_score_storage"
        return {0x94:"game_mode",0x98:"current_hole"}.get(offset,"unknown")
    if name=="sports_sequence":
        if 0x14<=offset<0xA4:return "golf_score_storage"
        return {0x04:"sport",0x08:"sequence",0x0C:"training_game",
                0x10:"golf_final_hole",0xAC:"golf_mode"}.get(offset,"unknown")
    if name=="golf_field":
        return {0x04:"shadow_pointer",0x10:"tree_shadow_timer",
                0x44:"current_pin_pointer",0x50:"current_start_pointer",
                0x54:"cup_pointer",0x80:"green_slope_opacity",
                0x94:"minimap_player_effect_pointer",
                0x98:"minimap_shot_line_effect_pointer",
                0x9C:"minimap_ball_effect_pointer"}.get(offset,"unknown")
    if name in OPTIONAL_EFFECTS:return "minimap_rendering_unknown"
    return "unknown"

def _pointer_like(value):
    return value%4==0 and (0x80000000<=value<0x81800000 or
                           0x90000000<=value<0x94000000)

def _float_like(value):
    f=struct.unpack(">f",struct.pack(">I",value))[0]
    return math.isfinite(f) and 1e-4<=abs(f)<=500

def _windows(row,scope):
    result={}
    for name,data in row["windows"].items():
        if name not in WINDOW_LENGTHS[scope] and name not in OPTIONAL_EFFECTS:
            raise ValueError("unknown memory window")
        raw=bytes.fromhex(data["bytes_hex"])
        expected=WINDOW_LENGTHS[scope].get(name,0x200)
        if len(raw)!=expected:raise ValueError("wrong window length")
        if not isinstance(data["address"],str) or not data["address"].startswith("0x"):
            raise ValueError("invalid window origin")
        address=int(data["address"],16)
        if address%4:raise ValueError("unaligned window origin")
        result[name]=(address,raw)
    if not all(name in result for name in WINDOW_LENGTHS[scope]):
        raise ValueError("missing required golf structures")
    return result

def summarize_phase_memory(rows,observations,*,scope,run_id,top=100):
    if scope not in WINDOW_LENGTHS or not 2<=len(rows)<=MAX_CAPTURE_SAMPLES:
        raise ValueError("invalid scope or number of samples")
    if not 1<=top<=300:raise ValueError("invalid top count")
    if not isinstance(run_id,str) or re.fullmatch(r"[A-Za-z0-9_-]{1,90}",run_id) is None:
        raise ValueError("invalid run identifier")
    counts=defaultdict(int)
    changes=defaultdict(lambda:{"within_phase_changes":0,
                                 "at_phase_boundary_changes":0,
                                 "pointer_like_changes":0,
                                 "float_like_changes":0})
    phases=[]
    non_atomic=[]
    skipped_relocations=0
    previous=None
    for row in rows:
        if not isinstance(row,dict) or row.get("game_id")!="RSPE01" or row.get("disc_revision")!=1 or row.get("game_mode_raw")!=4:
            raise ValueError("wrong disc revision or training mode")
        phase=row.get("phase")
        stage=row.get("stage")
        if phase not in ALLOWED_PHASES or type(stage) is not int or stage<0 or stage>5:
            raise ValueError("invalid phase label")
        start,end=row.get("frame_start"),row.get("frame_end")
        if type(start) is not int or type(end) is not int or start<0 or end<start:
            raise ValueError("invalid frame bracket")
        counts[phase]+=1
        phases.append(phase)
        non_atomic.append(end-start)
        current=_windows(row,scope)
        if previous is not None:
            pstage,pwindows=previous
            for name in current.keys() & pwindows.keys():
                address,raw=current[name]
                prev_addr,old=pwindows[name]
                if prev_addr!=address:
                    skipped_relocations+=1
                    continue
                for offset in range(0,len(raw),4):
                    a=struct.unpack_from(">I",old,offset)[0]
                    b=struct.unpack_from(">I",raw,offset)[0]
                    if a==b:continue
                    entry=changes[(name,offset)]
                    key="within_phase_changes" if stage==pstage else "at_phase_boundary_changes"
                    entry[key]+=1
                    entry["pointer_like_changes"]+=int(_pointer_like(a) and _pointer_like(b))
                    entry["float_like_changes"]+=int(_float_like(a) and _float_like(b))
        previous=(stage,current)
    allowed_obs=[]
    for item in observations:
        if type(item) is not dict or type(item.get("stage")) is not int or item.get("phase") not in ALLOWED_PHASES or item.get("observation") not in ALLOWED_OBSERVATIONS:
            raise ValueError("invalid human observation")
        allowed_obs.append({k:item[k] for k in ("stage","phase","observation")})
    ranking=[]
    for (name,offset),stat in changes.items():
        ranking.append({"region":name,"relative_offset":f"+0x{offset:X}",
                        "documented_role":documented_role(name,offset),**stat})
    ranking.sort(key=lambda row:(-row["within_phase_changes"],
                                 -row["at_phase_boundary_changes"],
                                 row["region"],int(row["relative_offset"][3:],16)))
    return {
        "schema_version":1,
        "kind":"golf-memory-phase-differential",
        "study_id":"S002-GOLF-MEMORY-PHASES",
        "id":run_id,
        "scope":scope,
        "sample_count":len(rows),
        "phase_sample_counts":dict(sorted(counts.items())),
        "max_non_atomic_frame_span":max(non_atomic),
        "mean_non_atomic_frame_span":round(sum(non_atomic)/len(non_atomic),2),
        "skipped_relocated_windows":skipped_relocations,
        "changed_word_count":len(ranking),
        "top_changed_relative_words":ranking[:top],
        "human_observations":allowed_obs,
        "confirmed_power_address":False,
        "confirmed_club_pose_address":False,
        "confirmed_ball_position_address":False,
        "warning":"Exploratory non-atomic snapshots. Relative offsets are not identified gameplay fields; human observations are not verified by RAM."
    }
