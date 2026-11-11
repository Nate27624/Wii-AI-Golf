#!/usr/bin/env python3
"""Operator-initiated Wii Sports Golf WOOD / LEAVES / NEAR-MISS capture.

Press ENTER to start each trial. Swing MANUALLY in the already running
Dolphin. Press ENTER to stop, or let the bounded recording auto-stop.
No controller/swing/game-memory writes, no savestate modifications.
Requires localhost Felk bridge's read-only memory.read_u32/read_bytes
and frame.get_count methods. Private raw memory stays outside Git.

Captures bounded source-owned candidate ball, selected record, nested
translation and the 94 source-owned 84-byte tree records. Each sample
has a non-atomic frame-count bracket; NOT a physics frame/contact proof.
Optional FFmpeg window-only video, or Pillow screenshots, never desktop
screen recording. A trial name WOOD/LEAVES is an INTENT, not evidence
of contact; operator separately annotates the observed result.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SRC=ROOT/"src"
sys.path.insert(0,str(SRC))
sys.path.insert(0,str(HERE))

from wii_ai_golf.integration.rpc import FelkRPC
import p0_live_no_contact_compare as source

TYPES=("wood","leaves","near_miss")
OBSERVED=("wood","leaves","none","uncertain")
MEMBER_STRIDE=0xCC
BALL_BYTES=0x1C0
RECORD_BYTES=0xCC
TREES=94
TREE_STRIDE=84
TREE_BYTES=TREES*TREE_STRIDE
CHUNK=512
MAX_TRIAL_SECONDS=180
MAX_RUNS=3


def utc():
    return datetime.now(timezone.utc).isoformat()


def safe_private_root(path:Path):
    path=path.resolve(strict=True)
    if not path.is_dir() or path.is_symlink():
        raise ValueError("Private recording directory unavailable")
    if path==ROOT.resolve() or ROOT.resolve() in path.parents:
        raise ValueError("Private captures cannot be inside the Git checkout")
    if any(x in str(path).lower() for x in
           ("onedrive","dropbox","google drive","icloud","syncthing")):
        raise ValueError("Synced data directory not allowed")
    return path


def in_bank(addr,size=4,bank=None):
    return source.in_bank(addr,size,bank)


def word(rpc,addr):
    if not in_bank(addr,4):
        raise ValueError("Source pointer outside captured Wii RAM")
    value=rpc.call("memory.read_u32",[addr])
    if type(value) is not int or not 0<=value<=0xFFFFFFFF:
        raise ValueError("Invalid bounded u32 bridge response")
    return value


def bytes_read(rpc,addr,n):
    if not in_bank(addr,n):
        raise ValueError("Source window outside Wii RAM bank")
    out=bytearray()
    for i in range(0,n,CHUNK):
        amount=min(CHUNK,n-i)
        raw=rpc.call("memory.read_bytes",[addr+i,amount])
        if not isinstance(raw,str) or len(raw)!=amount*2:
            raise ValueError("Unexpected read-only bytes response length")
        data=bytes.fromhex(raw)
        if len(data)!=amount:
            raise ValueError("Incomplete native source bytes")
        out.extend(data)
    return bytes(out)


def preflight(rpc):
    head=bytes_read(rpc,0x80000000,8)
    if head[:6]!=b"RSPE01" or head[7]!=1:
        raise ValueError("Requires Wii Sports USA Rev1 RSPE01")
    mgr=word(rpc,source.SCENE_STATIC)
    if not in_bank(mgr,0x20,"MEM1") or word(rpc,source.SCENE_STATIC+4)!=0:
        raise ValueError("SceneManager source gate failed")
    if word(rpc,mgr+0x18)!=5:
        raise ValueError("Game is not in Golf scene")
    scene=word(rpc,mgr+0xC)
    if not in_bank(scene,0xA0,"MEM2") or (
            word(rpc,scene+0x1C)!=5 or word(rpc,scene+0x20)!=mgr
            or word(rpc,scene+0x54)!=2):
        raise ValueError("Golf scene native owner mismatch")
    config=word(rpc,source.CONFIG_STATIC)
    field=word(rpc,source.FIELD_STATIC)
    pm=word(rpc,source.PLAYER_MANAGER_STATIC)
    if (not in_bank(config,0xA0,"MEM2") or
        not in_bank(field,0xA8,"MEM2") or
        not in_bank(pm,0x33C,"MEM2")):
        raise ValueError("Original native Golf globals absent")
    if not 0x803C7DD0<=word(rpc,pm)<0x803C7DE0:
        raise ValueError("PlayerManager source type changed")
    selector=word(rpc,pm+0x334)
    indices=[i for i in range(4) if selector==pm+4+i*MEMBER_STRIDE]
    if len(indices)!=1 or not in_bank(selector,RECORD_BYTES,"MEM2"):
        raise ValueError("Selected record source identity ambiguous")
    ball=word(rpc,selector+0x88)
    if not in_bank(ball,BALL_BYTES,"MEM2") or not (
            0x803C7918<=word(rpc,ball)<0x803C7A50):
        raise ValueError("Selected Ball candidate source identity failed")
    nested=word(rpc,ball+0x4C)
    if not in_bank(nested,12,"MEM2"):
        raise ValueError("Source Ball nested triplet not mapped")
    tree_count=word(rpc,field+0x1C)
    tree_base=word(rpc,field+0x20)
    if tree_count!=TREES or not in_bank(tree_base,TREE_BYTES,"MEM2"):
        raise ValueError("Requires this source-owned 94-tree course; other hole not validated")
    tree_prefix=bytes_read(rpc,tree_base,TREE_BYTES)
    first=tree_prefix[:4]
    if any(tree_prefix[i*TREE_STRIDE:i*TREE_STRIDE+4]!=first
           for i in range(TREES)):
        raise ValueError("Source 94-tree shared firstword changed")
    mode=word(rpc,config+0x94)
    hole=word(rpc,config+0x98)
    if mode>32 or hole>32:
        raise ValueError("Golf mode/hole source values invalid")
    return {
        "roots":{"mgr":mgr,"scene":scene,"config":config,"field":field,
                 "pm":pm,"record":selector,"ball":ball,"nested":nested,
                 "tree":tree_base},
        "selected_index":indices[0],"mode_raw":mode,"hole_raw":hole,
        "shared_tree_firstword_94":True,
        "source_identity_digest":hashlib.sha256(
            json.dumps([mgr,scene,config,field,pm,selector,ball,nested,
                        tree_base,mode,hole],separators=(",",":")).encode()).hexdigest(),
        "initial_tree_bytes":tree_prefix,
    }


def sample(rpc,identity,sample_index,tree_every):
    roots=identity["roots"]
    start_ns=time.monotonic_ns()
    frame_a=rpc.call("frame.get_count",[])
    if type(frame_a) is not int or frame_a<0:
        raise ValueError("Invalid bridge frame count")
    ball=bytes_read(rpc,roots["ball"],BALL_BYTES)
    record=bytes_read(rpc,roots["record"],RECORD_BYTES)
    nested=bytes_read(rpc,roots["nested"],12)
    tree=(bytes_read(rpc,roots["tree"],TREE_BYTES)
          if sample_index%tree_every==0 else None)
    if sample_index%8==0:
        if (word(rpc,roots["record"]+0x88)!=roots["ball"]
            or word(rpc,roots["field"]+0x20)!=roots["tree"]
            or word(rpc,roots["config"]+0x98)!=identity["hole_raw"]):
            raise ValueError("Shot/scene/ball identity changed during recording")
    frame_b=rpc.call("frame.get_count",[])
    if type(frame_b) is not int or frame_b<frame_a:
        raise ValueError("Invalid sampled frame bracket")
    return {
        "schema_version":1,
        "sample_index":sample_index,
        "utc":utc(),
        "host_monotonic_start_ns":start_ns,
        "host_monotonic_end_ns":time.monotonic_ns(),
        "bridge_frame_count_start":frame_a,
        "bridge_frame_count_end":frame_b,
        "not_same_physics_frame_verified":True,
        "source_identity_digest":identity["source_identity_digest"],
        "ball_object_candidate_be_hex_PRIVATE":ball.hex(),
        "selected_record_be_hex_PRIVATE":record.hex(),
        "nested_translation_candidate_be_hex_PRIVATE":nested.hex(),
        "all_94_tree_records_be_hex_PRIVATE":tree.hex() if tree is not None else None,
        "contact_detected_by_memory":False,
        "training_approved":False,
    }


def capture_loop(rpc,identity,raw_file,stop,hz,duration,tree_every,errors,counts):
    target_period=1.0/hz
    started=time.monotonic()
    try:
        with raw_file.open("x",encoding="utf-8") as fh:
            index=0
            while not stop.is_set() and time.monotonic()-started<duration:
                tick=time.monotonic()
                try:
                    row=sample(rpc,identity,index,tree_every)
                except Exception as exc:
                    errors.append(type(exc).__name__+": "+str(exc))
                    break
                fh.write(json.dumps(row,separators=(",",":"),allow_nan=False)+"\n")
                fh.flush()
                index+=1
                counts["samples"]=index
                counts["tree_snapshots"]+=int(row["all_94_tree_records_be_hex_PRIVATE"] is not None)
                sleep_s=target_period-(time.monotonic()-tick)
                if sleep_s>0:
                    stop.wait(sleep_s)
    finally:
        stop.set()


def dolphin_window():
    if sys.platform!="win32":
        return None
    import ctypes
    from ctypes import wintypes
    user32=ctypes.windll.user32
    matches=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def cb(hwnd,lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length=user32.GetWindowTextLengthW(hwnd)
        if length<7 or length>255:
            return True
        title=ctypes.create_unicode_buffer(length+1)
        user32.GetWindowTextW(hwnd,title,length+1)
        text=title.value
        if "Dolphin" in text and "Wii" in text or text.startswith("Dolphin "):
            matches.append((hwnd,text))
        return True
    callback=callback_type(cb)
    user32.EnumWindows(callback,0)
    return matches[0] if len(matches)==1 else None


def start_visual_capture(folder,duration):
    """Window-only; no whole-desktop capture. Video is optional."""
    target=dolphin_window()
    if target is None:
        return None,None,"Dolphin display window not uniquely identified"
    hwnd,title=target
    exe=shutil.which("ffmpeg")
    if exe:
        video=folder/"dolphin-window-PRIVATE.mp4"
        log=folder/"video-ffmpeg-PRIVATE.log"
        fh=log.open("x",encoding="utf-8")
        cmd=[exe,"-hide_banner","-loglevel","error",
             "-f","gdigrab","-framerate","12","-draw_mouse","0",
             "-i","title="+title,"-t",str(duration+5),
             "-c:v","libx264","-preset","ultrafast","-crf","24",
             "-pix_fmt","yuv420p",str(video)]
        try:
            process=subprocess.Popen(cmd,stdin=subprocess.PIPE,
                                     stdout=subprocess.DEVNULL,stderr=fh)
        except OSError:
            fh.close()
            return None,None,"FFmpeg present but could not start"
        return process,fh,"FFmpeg Dolphin-window video attempted; check output file"
    try:
        from PIL import ImageGrab
    except ImportError:
        return None,None,"No FFmpeg or Pillow found; RAM evidence only (use OBS/video manually)"
    return ("pillow",hwnd,ImageGrab),None,"Pillow sampled screenshots attempted"


def stop_visual_capture(capture,handle):
    if isinstance(capture,subprocess.Popen):
        try:
            if capture.poll() is None and capture.stdin:
                capture.stdin.write(b"q\n")
                capture.stdin.flush()
                capture.wait(timeout=8)
        except (OSError,subprocess.TimeoutExpired):
            capture.terminate()
            try: capture.wait(timeout=4)
            except subprocess.TimeoutExpired: capture.kill()
        finally:
            if capture.stdin: capture.stdin.close()
            if handle:handle.close()


def screen_worker(capture,folder,stop,counts):
    if not isinstance(capture,tuple) or capture[0]!="pillow":
        return
    _,hwnd,grab=capture
    import ctypes
    from ctypes import wintypes
    user=ctypes.windll.user32
    class RECT(ctypes.Structure):
        _fields_=[("left",wintypes.LONG),("top",wintypes.LONG),
                  ("right",wintypes.LONG),("bottom",wintypes.LONG)]
    pictures=folder/"screens-PRIVATE"
    pictures.mkdir()
    while not stop.is_set():
        # Only capture the game's visible foreground window; never save
        # console, other windows or entire desktop.
        rect=RECT()
        if user.GetForegroundWindow()==hwnd and user.GetWindowRect(hwnd,ctypes.byref(rect)):
            if rect.right>rect.left and rect.bottom>rect.top:
                try:
                    picture=grab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom))
                    picture.save(pictures/f"frame-{counts['screenshots']:04d}.png")
                    counts["screenshots"]+=1
                except Exception:
                    pass
        stop.wait(0.8)


def file_sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def save_manifest(folder,data):
    f=folder/"trial-summary-PRIVATE.json"
    with f.open("x",encoding="utf-8") as stream:
        json.dump(data,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write("\n")
    return f


def capture_trial(root,kind,args):
    folder=root/(kind+"-"+uuid.uuid4().hex[:8]+"-PRIVATE")
    folder.mkdir(mode=0o700)
    raw=folder/"candidate-stream-RAW-PRIVATE.jsonl"
    with FelkRPC(port=args.port,timeout_s=10) as rpc:
        identity=preflight(rpc)
        print(f"Verified US Rev1 Golf source gates, source 94 trees, hole raw={identity['hole_raw']}, mode raw={identity['mode_raw']}.")
        print("Enter STARTS the next trial; then switch to Dolphin and swing MANUALLY.")
        print("The name "+kind.upper()+" is your INTENDED target, NOT a confirmed hit.")
        answer=input(f"[{kind.upper()}] Press ENTER to START (q skips): ").strip().lower()
        if answer=="q":
            return {"kind":kind,"status":"skipped"}
        if answer:
            raise ValueError("Only ENTER or q accepted")
        # Give the operator time to refocus Dolphin after pressing Enter.
        print("Recording begins in 3 seconds; move focus to Dolphin now.")
        for remaining in (3,2,1):
            print(str(remaining)+"...",flush=True)
            time.sleep(1.0)
        stop=threading.Event()
        errors=[]
        counts={"samples":0,"tree_snapshots":0,"screenshots":0}
        visual,handle,mode=start_visual_capture(folder,args.seconds)
        print("RECORDING "+kind.upper()+". Return here and press ENTER to stop, or it auto-stops after "+str(args.seconds)+"s.",flush=True)
        worker=threading.Thread(target=capture_loop,
            args=(rpc,identity,raw,stop,args.hz,args.seconds,args.tree_every,errors,counts),
            daemon=True)
        screenshots=threading.Thread(target=screen_worker,
            args=(visual,folder,stop,counts),daemon=True)
        worker.start()
        screenshots.start()
        # Poll keyboard only on Windows; the terminal must have focus
        # when user presses ENTER. Auto-timeout works without terminal focus.
        if sys.platform=="win32":
            import msvcrt
            while worker.is_alive():
                if msvcrt.kbhit():
                    key=msvcrt.getwch()
                    if key=="\r":
                        stop.set()
                        break
                time.sleep(0.08)
        worker.join(timeout=args.seconds+20)
        stop.set()
        screenshots.join(timeout=4)
        stop_visual_capture(visual,handle)
        if worker.is_alive():
            errors.append("memory worker did not stop promptly")
        print(f"Stopped {kind}: {counts['samples']} candidate packets, {counts['tree_snapshots']} tree snapshots.",flush=True)
    print("What did you ACTUALLY SEE? This is a human annotation, not a native contact detector.")
    observed=input("Visible region touched [wood/leaves/none/uncertain]: ").strip().lower()
    if observed not in OBSERVED:
        observed="uncertain"
    changed=input("Did trajectory visibly change near the tree [yes/no/unknown]: ").strip().lower()
    if changed not in ("yes","no","unknown"):
        changed="unknown"
    note=input("Optional club/power/wind/aim note (no private secrets): ").strip()[:300]
    video=folder/"dolphin-window-PRIVATE.mp4"
    items=[p for p in [raw,video] if p.is_file()]
    payload={
        "schema_version":1,"status":"recorded" if counts["samples"]>=2 and not errors else "partial_or_abstained",
        "trial_intent":kind,"operator_observed_contact_region":observed,
        "operator_observed_trajectory_changed":changed,
        "operator_note":note,
        "operator_video_checked":False,
        "trial_has_native_collision_contact_proof":False,
        "tree_hitbox_geometry_verified":False,
        "ball_velocity_field_verified":False,
        "guest_physics_frame_atomicity_verified":False,
        "training_approved":False,
        "source_owner_identity_checked":True,
        "all_94_tree_firstwords_same":True,
        "source_selected_index":identity["selected_index"],
        "source_mode_raw":identity["mode_raw"],
        "source_hole_raw":identity["hole_raw"],
        "source_identity_digest_PRIVATE":identity["source_identity_digest"],
        "recorded_utc":utc(),
        "sample_count":counts["samples"],
        "tree_snapshot_count":counts["tree_snapshots"],
        "screenshot_count":counts["screenshots"],
        "visual_capture_mode_note":mode,
        "video_created":video.is_file() and video.stat().st_size>0,
        "capture_errors":errors,
        "files_private":[{"name":p.name,"bytes":p.stat().st_size,
                           "sha256":file_sha(p)} for p in items],
    }
    result=save_manifest(folder,payload)
    print("Private files:",folder)
    print("Trial summary:",result.name)
    return payload


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",required=True,type=Path)
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--seconds",type=int,default=50)
    p.add_argument("--hz",type=float,default=4.0)
    p.add_argument("--tree-every",type=int,default=8)
    p.add_argument("--kinds",nargs="+",choices=TYPES,default=list(TYPES))
    p.add_argument("--selftest",action="store_true")
    args=p.parse_args(argv)
    if args.selftest:
        print(json.dumps({"status":"SELFTEST_PASS","kinds":TYPES,
                          "bridge_contacted":False,"training_approved":False}))
        return 0
    if not 1<=args.port<=65535 or not 5<=args.seconds<=MAX_TRIAL_SECONDS:
        p.error("port/seconds out of allowed bounds")
    if not 1<=args.hz<=10 or not 1<=args.tree_every<=50:
        p.error("hz/tree sampling out of allowed bounds")
    if len(args.kinds)>MAX_RUNS or len(set(args.kinds))!=len(args.kinds):
        p.error("At most one each of wood, leaves, near_miss allowed per session")
    root=safe_private_root(args.private_root)
    folder=root/("tree-contact-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]+"-PRIVATE")
    folder.mkdir(mode=0o700)
    summaries=[]
    print("Read-only Felk source recorder. Does not move controller, load savestates or alter Dolphin.",flush=True)
    print("Use the SAME pre-shot checkpoint for comparable WOOD / LEAVES / NEAR_MISS trials.")
    try:
        for kind in args.kinds:
            print("\nNEXT TRIAL: "+kind.upper())
            summaries.append(capture_trial(folder,kind,args))
    except (OSError,ValueError,RuntimeError,TimeoutError,EOFError,KeyboardInterrupt) as exc:
        print("Stopped: "+type(exc).__name__+": "+str(exc),file=sys.stderr)
        print("Any completed prior trials and partial raw stream stay in private folder.",file=sys.stderr)
        print("Private session: "+str(folder),file=sys.stderr)
        return 2
    compact={
        "kind":"P0_OPERATOR_TREE_CONTACT_CANDIDATES_V1",
        "recording_session_status":"complete",
        "trial_intents":[x["kind"] for x in summaries],
        "trials":[{"kind":x["kind"],"status":x["status"],
                   "sample_count":x.get("sample_count",0),
                   "observed_contact_region":x.get("operator_observed_contact_region","unknown"),
                   "observed_trajectory_changed":x.get("operator_observed_trajectory_changed","unknown"),
                   "video_created":x.get("video_created",False)}
                  for x in summaries],
        "contact_verified_by_native_code":False,
        "ball_velocity_verified":False,"training_approved":False,
    }
    f=folder/"operator-summary-SAFE.json"
    with f.open("x",encoding="utf-8") as stream:
        json.dump(compact,stream,indent=2)
        stream.write("\n")
    print("\nDONE. Private session: "+str(folder))
    print("Share operator-summary-SAFE.json first; keep raw candidate-stream files PRIVATE.")
    print(json.dumps(compact,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
