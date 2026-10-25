"""Run approved offline, zero-input Golf Lab experiments sequentially.

No Dolphin startup, RAM writes, network changes or live experiments.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
SRC=str(ROOT/"src")
if SRC in sys.path:sys.path.remove(SRC)
sys.path.insert(0,SRC)
from wii_ai_golf.lab.core import execute,load_catalog,plan

AUTO_KINDS=frozenset({"tests_all","tests_integration","tests_evaluation",
                       "tests_learning","bridge_inspect","demo"})

def eligible(catalog):
    return [x["id"] for x in catalog if x["mode"]=="offline"
            and x["kind"] in AUTO_KINDS]

def main():
    catalog=load_catalog(ROOT/"research"/"experiments.json")
    studies=eligible(catalog)
    if not studies:
        print("No approved zero-input offline studies.");return 0
    failures=0
    for identifier in studies:
        print("OFFLINE:",identifier,flush=True)
        try:
            result=execute(plan(identifier,root=ROOT,catalog=catalog),root=ROOT)
            print(json.dumps({"experiment_id":identifier,"status":result["execution_status"],
                              "exit_code":result["exit_code"]}),flush=True)
            if result["exit_code"]!=0:failures+=1
        except (OSError,ValueError,RuntimeError) as exc:
            failures+=1;print("FAILED:",identifier,type(exc).__name__,str(exc),flush=True)
    print("Offline batch finished:",len(studies),"studies,",failures,"failures",flush=True)
    return 1 if failures else 0
if __name__=="__main__":raise SystemExit(main())
