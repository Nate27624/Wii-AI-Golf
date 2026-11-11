"""Analyze an EXISTING private MEM1 dump for cached Rev1 PPC field accesses.

Offline only. NO Dolphin boot, main.dol, ROM extraction, controller, or network.
Detailed relative code-site report stays in ignored Wii-AI-Golf-Data, NOT GitHub.
Terminal prints counts only to prevent unreviewed field address publication.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.audit.golf_cached_ppc_access import audit_local_cached_mem1

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",required=True,type=Path)
    p.add_argument("--mem1",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--max-rows",type=int,default=72)
    args=p.parse_args(argv)
    try:
        if "Wii-AI-Golf-Data" not in args.private_root.resolve(strict=True).parts:
            raise ValueError("Expected ignored Wii-AI-Golf-Data")
        report=audit_local_cached_mem1(
            args.mem1,private_root=args.private_root,output=args.output,
            max_rows=args.max_rows)
    except (OSError,ValueError,TypeError,KeyError):
        print("Private cached PPC audit stopped: check source, native "
              "MEM1 size and private output (no code data uploaded)",
              file=sys.stderr)
        return 1
    safe={
        "kind":report["kind"],"source_units":report["source_units"],
        "all_candidate_operand_rows":report["all_candidate_operand_rows"],
        "operand_rows_omitted":report["operand_rows_omitted"],
        "store_counts_by_source_unit":report["store_counts_by_source_unit"],
        "allowed_to_publish":False,"actual_field_semantics_verified":False,
        "swing_power_verified":False}
    print(json.dumps(safe,indent=2,sort_keys=True))
    print("Full RELATIVE CODE-SITE atlas created locally only; no upload.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
