"""Offline cohort audit of PRIVATE Wii Sports golf outcome RAM captures.

Ranks repeatable RELATIVE changes across independent runs without publishing
raw memory, absolute addresses, paths, hashes of private dumps, or values.
No Dolphin, no motion, no gameplay assumptions.
"""
from __future__ import annotations
import argparse,json,sys,uuid
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))
from analyze_existing_golf_capture import load_existing_capture
from wii_ai_golf.audit.memory_phases import summarize_phase_memory

MAX_FILES=25
MAX_REPORT_ROWS=250

def summarize_cohort(reports,run_id):
    if not 2<=len(reports)<=MAX_FILES:
        raise ValueError("Need two or more independently captured valid outcome runs")
    seen=defaultdict(lambda:{"runs_changed":0,"runs_within_phase":0,
                             "runs_at_phase_boundary":0,
                             "within_phase_events":0,"boundary_events":0})
    regions=defaultdict(int)
    for report in reports:
        if report.get("kind")!="golf-memory-phase-differential" or report.get("scope")!="broad":
            raise ValueError("Expected broad S002 phase differential")
        keys=set()
        for row in report["top_changed_relative_words"]:
            key=(row["region"],row["relative_offset"])
            if key in keys:raise ValueError("Duplicate word within a run")
            keys.add(key)
            d=seen[key]
            d["runs_changed"]+=1
            if row["within_phase_changes"]:d["runs_within_phase"]+=1
            if row["at_phase_boundary_changes"]:d["runs_at_phase_boundary"]+=1
            d["within_phase_events"]+=row["within_phase_changes"]
            d["boundary_events"]+=row["at_phase_boundary_changes"]
        for region in set(row["region"] for row in report["top_changed_relative_words"]):
            regions[region]+=1
    ranked=[{"region":name,"relative_offset":offset,**d}
            for (name,offset),d in seen.items()]
    ranked.sort(key=lambda x:(-x["runs_changed"],-x["runs_within_phase"],
                              x["region"],int(x["relative_offset"][3:],16)))
    return {"schema_version":1,"kind":"golf-memory-cohort-relative-words",
            "study_id":"S002-GOLF-MEMORY-COHORT","id":run_id,
            "valid_independent_runs":len(reports),
            "shared_changed_words_all_runs":sum(x["runs_changed"]==len(reports) for x in ranked),
            "recurrent_changed_words_2plus_runs":sum(x["runs_changed"]>=2 for x in ranked),
            "distinct_changed_words":len(ranked),
            "regions_with_changes_by_run_count":dict(sorted(regions.items())),
            "recurrent_words":[x for x in ranked if x["runs_changed"]>=2][:MAX_REPORT_ROWS],
            "no_gameplay_variable_verified":True,
            "warning":"Repeated changes are not identified golf power, club pose, flight or score. Only already-recorded phase-aligned statistics are compared; frame timing and human labels may differ."}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory",type=Path,default=ROOT.parent/"Wii-AI-Golf-Data"/"captures")
    publish=p.add_mutually_exclusive_group()
    publish.add_argument("--publish",action="store_true",
                         help="Opt in only after S000 accepts the cohort public schema")
    publish.add_argument("--no-upload",action="store_true",help="Explicit offline-only mode (default)")
    a=p.parse_args(argv)
    try:
        if not a.directory.is_dir():raise ValueError("Capture directory missing")
        candidates=sorted(a.directory.glob("outcome-*-RAW-PRIVATE.jsonl"))
        if not 2<=len(candidates)<=MAX_FILES:
            raise ValueError(f"Need 2..{MAX_FILES} outcome raw capture files; found {len(candidates)}")
        report_list=[];invalid=0
        for path in candidates:
            try:
                rows=load_existing_capture(path)
                rpt=summarize_phase_memory(rows,[],scope="broad",
                                           run_id="offline-cohort-intermediate",top=300)
                if rpt["changed_word_count"]>300:
                    raise ValueError("Truncated changed-word list: cannot aggregate accurately")
                report_list.append(rpt)
            except (OSError,TypeError,ValueError,KeyError) as exc:
                invalid+=1
                print("Skipped invalid/incomplete PRIVATE run:",path.name,":",exc,file=sys.stderr)
        if len(report_list)<2:
            raise ValueError("Fewer than two valid source-gated independent runs")
        run="cohort-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:8]
        report=summarize_cohort(report_list,run)
        report["excluded_invalid_or_incomplete_runs"]=invalid
        output=a.directory/("golf-memory-cohort-"+run+"-summary.json")
        with output.open("x",encoding="utf-8") as fp:
            json.dump(report,fp,sort_keys=True,indent=2,allow_nan=False)
            fp.write("\n")
        print("Sanitized local cohort:",output)
        print("Valid runs:",report["valid_independent_runs"],
              "recurring offsets:",report["recurrent_changed_words_2plus_runs"],
              "excluded:",invalid,flush=True)
        if a.publish:
            try:
                from research_cli import publish_summary
                publish_summary(report)
                print("GitHub JSON: https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/"+run+".json",flush=True)
            except (OSError,ValueError,RuntimeError) as exc:
                print("GitHub upload unavailable; sanitized local file preserved:",exc,file=sys.stderr)
        else:
            print("Local-only cohort: S000 public-schema approval pending. No GitHub upload attempted.",flush=True)
        return 0
    except (OSError,TypeError,ValueError,KeyError) as exc:
        print("Golf memory cohort audit failed:",exc,file=sys.stderr)
        return 1

if __name__=="__main__":raise SystemExit(main())
