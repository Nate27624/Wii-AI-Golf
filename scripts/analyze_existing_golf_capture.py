"""Analyze existing PRIVATE S002 outcome memory snapshots without running Dolphin.

Accepts only the canonical outcome-*-RAW-PRIVATE.jsonl schema and publishes
an allowlisted structure-relative statistical report (never raw RAM).
"""
from __future__ import annotations
import argparse,json,sys,uuid
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.audit.memory_phases import (
    normalize_legacy_outcome_rows,summarize_phase_memory,MAX_CAPTURE_SAMPLES
)
MAX_INPUT_BYTES=48*1024*1024

def load_existing_capture(path):
    if not path.is_file() or not 0<path.stat().st_size<=MAX_INPUT_BYTES:
        raise ValueError("missing or oversized private source file")
    rows=[]
    with path.open("r",encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
                if len(rows)>MAX_CAPTURE_SAMPLES:raise ValueError("too many raw observations")
    return normalize_legacy_outcome_rows(rows)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--top",type=int,default=100)
    p.add_argument("--no-upload",action="store_true")
    a=p.parse_args(argv)
    try:
        rows=load_existing_capture(a.input)
        run="offline-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:8]
        report=summarize_phase_memory(rows,[],scope="broad",run_id=run,top=a.top)
        report["origin"]="existing_private_S002_outcome_capture"
        # This source has no event timestamps aligned to true physical impact.
        report["warning"]+=" Legacy pre/post labels cannot prove a hit or exact impact frame."
        dest=a.input.parent/("golf-memory-audit-"+run+"-summary.json")
        with dest.open("x",encoding="utf-8") as stream:
            json.dump(report,stream,indent=2,sort_keys=True,allow_nan=False)
            stream.write("\n")
        print("Sanitized local summary:",dest,flush=True)
        print("Candidate changed words:",report["changed_word_count"],flush=True)
        if not a.no_upload:
            try:
                from research_cli import publish_summary
                print("Published sanitized observations:",publish_summary(report),flush=True)
                print("Observation record ID:",run,flush=True)
            print("GitHub JSON: https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/"+run+".json",flush=True)
            except (OSError,RuntimeError,ValueError) as exc:
                print("Upload unavailable; local sanitized report retained:",exc,file=sys.stderr)
        return 0
    except (OSError,TypeError,ValueError,KeyError) as exc:
        print("Offline outcome reprocessing failed:",exc,file=sys.stderr)
        return 1

if __name__=="__main__":raise SystemExit(main())
