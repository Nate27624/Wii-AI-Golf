"""Read-only minimap ball visual-effect control alongside world landmarks."""
from __future__ import annotations
import argparse,json,sys,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from session_bootstrap import add_boot_options,ensure_intro
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.minimap_effect_control import observe_effect,summarize_effect
from wii_ai_golf.golf_collection import make_run_id,publish_sanitized

def main():
    p=argparse.ArgumentParser(description=__doc__)
    add_boot_options(p)
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--seconds",type=float,default=20)
    p.add_argument("--ready-timeout",type=float,default=180)
    p.add_argument("--phase",choices=("idle","aim_only","swing"),required=True)
    p.add_argument("--data-dir",type=Path,default=ROOT/"captures")
    p.add_argument("--no-upload",action="store_true")
    a=p.parse_args()
    if not 5<=a.seconds<=180 or not 1<=a.ready_timeout<=600:p.error("invalid capture window")
    ensure_intro(a)
    a.data_dir.mkdir(parents=True,exist_ok=True)
    run=make_run_id();samples=[];errors=[]
    try:
        with FelkRPC(port=a.port,timeout_s=15) as rpc:
            end=time.monotonic()+a.ready_timeout
            while True:
                try:observe_effect(rpc);break
                except (RuntimeError,KeyError,ValueError):
                    if time.monotonic()>end:raise RuntimeError("Hitting the Green mode not ready")
                    time.sleep(1)
            print("Finish tee navigation. Press ENTER in PowerShell only when golfer is ready.")
            input("Ready to begin "+a.phase+" capture? ENTER: ")
            observe_effect(rpc)
            print("CAPTURE STARTING NOW:",a.seconds,"seconds; phase:",a.phase,flush=True)
            print("For aim_only, rotate camera WITHOUT swing; for swing, perform one shot.",flush=True)
            start=time.monotonic()
            raw=a.data_dir/f"minimap-effect-{run}.jsonl"
            with raw.open("x",encoding="utf-8") as output:
                while time.monotonic()-start<a.seconds:
                    tick=time.monotonic()
                    try:
                        row=observe_effect(rpc)
                        row["elapsed_s"]=round(tick-start,3)
                        samples.append(row)
                        output.write(json.dumps(row)+"\n");output.flush()
                        if len(samples)==1 or len(samples)%10==0:
                            print("RECORDING",len(samples),"samples; elapsed",round(time.monotonic()-start,1),"s",flush=True)
                    except (ValueError,RuntimeError,OSError) as exc:
                        errors.append(type(exc).__name__)
                        if len(errors)>=3:break
                    time.sleep(max(0,.05-(time.monotonic()-tick)))
    except (ValueError,RuntimeError,OSError,EOFError,KeyboardInterrupt) as exc:
        print("Capture aborted:",exc,file=sys.stderr);return 1
    report={"schema_version":1,"run_id":run,"study_id":"S002-MINIMAP-EFFECT-DIFFERENTIAL",
            "captured_utc":datetime.now(timezone.utc).isoformat(),
            "observed_phase":a.phase,"samples":len(samples),"errors":errors,
            "results":summarize_effect(samples),
            "warning":"Minimap ball visual effect is NOT the ball physics state"}
    summary=a.data_dir/f"minimap-effect-{run}-summary.json"
    summary.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    print("Local raw:",raw,"summary:",summary)
    if samples and not a.no_upload:
        try:print("GitHub:",publish_sanitized(report,ROOT))
        except (ValueError,RuntimeError,OSError) as exc:print("Upload failed; local copy saved:",exc)
    return 0 if samples else 1
if __name__=="__main__":raise SystemExit(main())
