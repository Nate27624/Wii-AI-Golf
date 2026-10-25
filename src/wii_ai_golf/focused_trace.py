"""Offline segmentation of locally recorded focused object XYZ.

Outputs metrics, never raw coordinates/addresses or unverified ball labels.
This tool deliberately treats discontinuities as scene transitions, not velocity.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def analyze_trace(path: str | Path, *, motion_threshold: float = .1,
                  reset_threshold: float = 25., max_lines: int = 250000) -> dict:
    if motion_threshold <= 0 or reset_threshold <= motion_threshold:
        raise ValueError("thresholds must satisfy 0 < motion < reset")
    samples = 0
    missing = 0
    malformed = 0
    changes = 0
    jumps = []
    episodes = []
    episode = None
    previous = None
    first_time = None
    last_time = None
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line_number > max_lines:
                raise ValueError("input exceeds line budget")
            try:
                row = json.loads(line)
                seconds = float(row["elapsed_s"])
                xyz = row.get("xyz")
                frame = int(row["frame_start"])
                base = row.get("object_base")
                if not math.isfinite(seconds) or seconds < 0 or frame < 0:
                    raise ValueError("invalid time/frame")
                if xyz is not None and (not isinstance(xyz,list) or len(xyz)!=3
                      or not all(type(v) in (int,float) and math.isfinite(v) for v in xyz)):
                    raise ValueError("invalid xyz")
            except (ValueError,TypeError,KeyError,json.JSONDecodeError,AttributeError):
                malformed+=1
                previous=None
                episode=None
                continue
            samples+=1
            first_time=seconds if first_time is None else first_time
            last_time=seconds
            if xyz is None or not base:
                missing+=1
                previous=None
                episode=None
                continue
            if previous is not None and (previous["base"] != base
                  or frame < previous["frame"] or seconds < previous["time"]):
                previous=None
                episode=None
            if previous is not None:
                dist=math.dist(xyz,previous["xyz"])
                if dist >= reset_threshold:
                    jumps.append({"elapsed_s":round(seconds,3),
                                  "frame":frame,"sample_step_units":round(dist,4),
                                  "classification":"discontinuity_not_velocity"})
                    episode=None
                elif dist >= motion_threshold:
                    changes+=1
                    if episode is None:
                        episode={"start_s":round(previous["time"],3),
                                 "end_s":round(seconds,3),
                                 "steps":0, "max_step_units":0}
                        episodes.append(episode)
                    episode["end_s"]=round(seconds,3)
                    episode["steps"]+=1
                    episode["max_step_units"]=round(max(episode["max_step_units"],dist),4)
                else:
                    episode=None
            previous={"base":base,"xyz":xyz,"time":seconds,"frame":frame}
    return {"schema_version":1,"source_kind":"local_focused_xyz_jsonl",
            "claim":"UNVERIFIED_candidate_motion_not_ball_trajectory",
            "samples_parsed":samples,"malformed_rows":malformed,
            "null_or_invalid_pointer_samples":missing,
            "duration_s":round(max(0,(last_time or 0)-(first_time or 0)),3),
            "motion_threshold_units":motion_threshold,
            "discontinuity_threshold_units":reset_threshold,
            "moving_steps_below_reset":changes,
            "discontinuities":jumps,
            "motion_episodes":episodes,
            "caveat":"Shot count, contact and ball identity cannot be verified from XYZ alone" }
