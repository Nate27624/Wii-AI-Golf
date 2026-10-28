"""PRIVATE GUI-export shot/result checkpoint keeper, never controls Dolphin.

Copies native paused MRAM+ExRAM to PRE, POST, and optional RESULT
without overwriting old B0-B3. POST must be a *visibly displaced* ball
before any reset. RESULT can be the score overlay/screen (even if scene
has changed) and may annotate the UI's displayed final distance.
The separate PRE/POST manifest is compatible with S002 PR #180.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import audit_selected_ball_prepost_shot_private as shot

PHASES=("PRE","POST","RESULT")
NAME="shot-distance-captures-PRIVATE.json"
MAX_TIME_NS=5*60*10**9


def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for blob in iter(lambda:f.read(1024*1024),b""):
            h.update(blob)
    return h.hexdigest()


def _checked_source(p,name,size):
    p=Path(p)
    if p.is_symlink() or not p.is_file() or p.name.lower()!=name:
        raise ValueError("Wrong native dump type or name")
    if p.stat().st_size!=size:
        raise ValueError("Wrong native dump byte count")
    return p


def _read_manifest(path):
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file() or path.stat().st_size>32*1024:
        raise ValueError("Unsafe existing shot study manifest")
    with path.open("r",encoding="utf-8") as f:
        m=json.load(f)
    if not isinstance(m,dict) or m.get("kind")!="local-private-golf-shot-cup-distance-checkpoints" or m.get("schema_version")!=1 or not isinstance(m.get("checkpoints"),dict):
        raise ValueError("Shot study manifest mismatch")
    return m


def _prepost_manifest(m):
    return {
        "kind": shot.MANIFEST_KIND, "schema_version":1,
        "operator_reports_same_dolphin_process":True,
        "operator_reports_exactly_one_shot":True,
        "operator_reports_visible_ball_displacement":True,
        "operator_reports_no_hole_reset_or_transition":True,
        "checkpoints":{
            "PRE":{
                "phase_operator_label":"pre_shot_still",
                "operator_reports_gui_paused":True,
                "operator_reports_mem1_mem2_export_same_pause":True,
                "sha256":m["checkpoints"]["PRE"]["sha256"]
            },
            "POST":{
                "phase_operator_label":"post_shot_visible_displacement",
                "operator_reports_gui_paused":True,
                "operator_reports_mem1_mem2_export_same_pause":True,
                "operator_reports_game_was_running_between_phases":True,
                "sha256":m["checkpoints"]["POST"]["sha256"]
            }
        }
    }


def preserve(*, private_root, mem1_source, mem2_source, checkpoint,
             paused_confirmed=False, shot_observed=False,
             same_process_confirmed=False, same_hole_confirmed=False,
             result_visible=False, displayed_distance=None, ui_unit=None,
             trusted_root=None):
    if checkpoint not in PHASES or paused_confirmed is not True:
        raise ValueError("Capture requires exact paused checkpoint")
    if shot_observed and checkpoint!="POST":
        raise ValueError("Shot observation only valid at POST")
    if checkpoint=="POST" and (not shot_observed or
                               not same_process_confirmed or
                               not same_hole_confirmed):
        raise ValueError("POST must be one observed displaced shot, same boot and hole")
    if checkpoint=="RESULT" and not result_visible:
        raise ValueError("RESULT requires visible score result")
    if checkpoint=="PRE" and (result_visible or displayed_distance is not None):
        raise ValueError("No result UI at PRE")
    if (displayed_distance is None)!=(ui_unit is None):
        raise ValueError("UI distance requires both value and unit")
    if displayed_distance is not None and (type(displayed_distance) not in (int,float)
            or not 0<=displayed_distance<100000 or ui_unit not in ("ft","yd","m")):
        raise ValueError("Invalid display distance or unit")
    session=Path(private_root)
    trusted=Path(trusted_root or (Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"))
    if (session.is_symlink() or not session.is_dir() or
            trusted.is_symlink() or not trusted.is_dir()):
        raise ValueError("Missing private ignored Data session")
    p=session.resolve(strict=True)
    root=trusted.resolve(strict=True)
    if p==root or not p.is_relative_to(root):
        raise ValueError("Session must be within ignored Data root")
    manifest_path=session/NAME
    prev=_read_manifest(manifest_path)
    keys=tuple(prev["checkpoints"]) if prev else ()
    if keys!=PHASES[:len(keys)] or len(keys)>=len(PHASES) or checkpoint!=PHASES[len(keys)]:
        raise ValueError("Only ordered fresh PRE -> POST -> optional RESULT accepted")
    source=[_checked_source(mem1_source,"mem1.raw",shot.roster.MEM1_SIZE),
            _checked_source(mem2_source,"mem2.raw",shot.roster.MEM2_SIZE)]
    stats=[x.stat() for x in source]
    if stats[1].st_mtime_ns<stats[0].st_mtime_ns or stats[1].st_mtime_ns-stats[0].st_mtime_ns>MAX_TIME_NS:
        raise ValueError("MRAM must be exported before ExRAM in SAME pause")
    if prev:
        last=prev["checkpoints"][keys[-1]]
        for i,bank in enumerate(("MEM1","MEM2")):
            if stats[i].st_mtime_ns<=last["source_mtime_ns"][bank]:
                raise ValueError("Stale dumps; export both banks AFTER latest pause")
    # Require real game header, but do not assume RESULT still uses Golf scene.
    with source[0].open("rb") as fh:
        if fh.read(8)!=b"RSPE01\x00\x01":
            raise ValueError("Not Wii Sports RSPE01 Rev1 native MRAM")
    target=[session/f"{checkpoint}-MEM1.bin",session/f"{checkpoint}-MEM2.bin"]
    if any(x.exists() or x.is_symlink() for x in target):
        raise ValueError("Never overwrite preserved shot checkpoints")
    compatibility=session/shot.MANIFEST_NAME
    if checkpoint=="POST" and (compatibility.exists() or compatibility.is_symlink()):
        raise ValueError("Previous pre/post manifest exists; use fresh session")
    temp=session/(NAME+".tmp")
    tempcompat=session/(shot.MANIFEST_NAME+".tmp")
    if any(x.exists() for x in (temp,tempcompat)):
        raise ValueError("Stale manifest transaction")
    copied=[]
    try:
        for x,y in zip(source,target):
            with x.open("rb") as i,y.open("xb") as o:
                copied.append(y)
                shutil.copyfileobj(i,o,1024*1024)
        for x,st,y in zip(source,stats,target):
            now=x.stat()
            if now.st_mtime_ns!=st.st_mtime_ns or now.st_size!=st.st_size or y.stat().st_size!=st.st_size:
                raise ValueError("Native export changed during copy")
        hashes={bank:digest(f) for bank,f in zip(("MEM1","MEM2"),target)}
        if prev and all(hashes[k]==prev["checkpoints"][keys[-1]]["sha256"][k]
                        for k in ("MEM1","MEM2")):
            raise ValueError("Both native banks unchanged; not a new checkpoint")
        m=prev or {
            "schema_version":1,
            "kind":"local-private-golf-shot-cup-distance-checkpoints",
            "created_at_utc":datetime.now(timezone.utc).isoformat(),
            "checkpoints":{},"allowed_to_publish":False,
            "same_guest_frame_verified":False,
            "same_boot_independently_verified":False,
            "training_allowed":False,
        }
        m["checkpoints"][checkpoint]={
            "operator_reports_gui_paused":True,
            "operator_reports_same_pause_mem1_mem2":True,
            "phase_label":checkpoint,
            "operator_observed_displaced_ball":bool(shot_observed),
            "operator_reports_same_process":bool(same_process_confirmed),
            "operator_reports_same_hole":bool(same_hole_confirmed),
            "operator_observed_result_visible":bool(result_visible),
            "ui_displayed_distance_value":displayed_distance,
            "ui_displayed_distance_unit":ui_unit,
            "source_mtime_ns":{k:s.st_mtime_ns for k,s in zip(("MEM1","MEM2"),stats)},
            "sha256":hashes,
        }
        with temp.open("x",encoding="utf-8") as f:
            json.dump(m,f,indent=2,sort_keys=True)
            f.write("\n")
        if checkpoint=="POST":
            with tempcompat.open("x",encoding="utf-8") as f:
                json.dump(_prepost_manifest(m),f,indent=2,sort_keys=True)
                f.write("\n")
            os.replace(tempcompat,compatibility)
        os.replace(temp,manifest_path)
        return {
            "kind":"local-private-shot-cup-checkpoint-ack",
            "checkpoint":checkpoint,"preserved_native_banks":2,
            "total_phases_preserved":len(m["checkpoints"]),
            "game_revision_header_verified":True,
            "operator_observed_displaced_ball":bool(shot_observed),
            "operator_observed_result_visible":bool(result_visible),
            "prepost_manifest_available":compatibility.is_file(),
            "gameplay_event_independently_verified":False,
            "allowed_to_publish":False,
        }
    except Exception:
        for x in (temp,tempcompat):
            if x.exists():x.unlink()
        for x in copied:
            if x.exists():x.unlink()
        raise


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",type=Path,required=True)
    p.add_argument("--mem1-source",type=Path,required=True)
    p.add_argument("--mem2-source",type=Path,required=True)
    p.add_argument("--checkpoint",choices=PHASES,required=True)
    p.add_argument("--paused-confirmed",action="store_true")
    p.add_argument("--shot-observed",action="store_true")
    p.add_argument("--same-process-confirmed",action="store_true")
    p.add_argument("--same-hole-confirmed",action="store_true")
    p.add_argument("--result-visible",action="store_true")
    p.add_argument("--displayed-distance",type=float)
    p.add_argument("--ui-unit",choices=("ft","yd","m"))
    a=p.parse_args(argv)
    try:
        report=preserve(
            private_root=a.private_root,
            mem1_source=a.mem1_source,mem2_source=a.mem2_source,
            checkpoint=a.checkpoint,paused_confirmed=a.paused_confirmed,
            shot_observed=a.shot_observed,
            same_process_confirmed=a.same_process_confirmed,
            same_hole_confirmed=a.same_hole_confirmed,
            result_visible=a.result_visible,
            displayed_distance=a.displayed_distance,
            ui_unit=a.ui_unit)
    except (OSError,ValueError,TypeError,KeyError,OverflowError):
        print("Shot/result checkpoint preservation REFUSED: verify private "
              "folder, exact native dumps, phase, observed shot and GUI pause. "
              "No private paths or RAM output.",file=sys.stderr)
        return 1
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
