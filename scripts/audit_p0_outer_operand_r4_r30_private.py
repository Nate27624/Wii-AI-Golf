"""Read-only original 14-bank source-gated r4/r30 upstream hint classification.

Exactly #231 original SHA-verified native seven-pair source reader; checks
source code identical across all captures; no raw source words or pointers
on output.  Static hints only: no runtime receiver or rendered ball identity.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import hashlib
import json
import mmap
from pathlib import Path
import sys

_HERE = str(Path(__file__).resolve().parent)
if _HERE in sys.path: sys.path.remove(_HERE)
sys.path.insert(0, _HERE)
import review_p0_outer_operand_r4_r30_source as hints
import audit_p0_authenticated_receiver_chain_private as receiver


def analyze(archive, canonical_source_scripts):
    source=Path(canonical_source_scripts).resolve(strict=True)
    if not source.is_dir():
        raise ValueError("invalid canonical reader directory")
    sys.path.insert(0,str(source))
    seven=receiver._import_from_path(
        "seven_exact_reviewed_for_operand",source /
        "audit_p0_seven_numbered_source_pairs_private.py")
    folders=seven._check_archive(Path(archive))
    first_digest=None
    first_hint=None
    for n in range(1,8):
        with ExitStack() as stack:
            mm=[]
            for i,size in enumerate(seven.SIZE):
                path=seven.src._file(folders[n],f"{n}.{i+1}.raw",size)
                fh=stack.enter_context(path.open("rb"))
                mm.append(stack.enter_context(mmap.mmap(
                    fh.fileno(),0,access=mmap.ACCESS_READ)))
            rd=seven.roster.TwoBankReader(*mm)
            seven._get(rd)  # exact RSPE01 Rev1 scene/player/ball/pin/start gate
            sha=hashlib.sha256()
            for _,entry,_,_ in hints.SOURCES:
                for pc in range(entry,entry+hints.SOURCE_WINDOW,4):
                    word=rd.u32(pc)
                    if type(word) is not int or not 0<=word<=0xFFFFFFFF:
                        raise ValueError("untrusted PPC source word")
                    sha.update(word.to_bytes(4,"big"))
            digest=sha.digest()
            if first_digest is None:
                first_digest=digest
            elif digest!=first_digest:
                raise ValueError("source code varies across original captures")
            result=hints.analyze(rd.u32)
            if first_hint is None:
                first_hint=result
            elif first_hint!=result:
                raise ValueError("static source analysis changed across captures")
    seven._check_archive(Path(archive))
    if not first_hint or first_hint["training_approved"] is not False:
        raise ValueError("source qualification incomplete")
    return {
        "kind":"P0-SANITIZED-SEVEN-CAPTURE-R4-R30-ORIGIN-TRIAGE",
        "original_fourteen_native_banks_sha_verified_before_and_after":True,
        "source_selected_scene_gated_for_all_seven":True,
        "two_source_code_windows_identical_all_seven":True,
        "human_phase_order_ignored":True,
        "source_operand_hints":first_hint["outer_operand_source_rows"],
        "all_path_reaching_definition_verified":False,
        "runtime_receiver_is_global_or_player_ball_verified":False,
        "ball_xyz_velocity_power_contact_score_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--canonical-source-scripts",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        result=analyze(args.archive,args.canonical_source_scripts)
    except (OSError,ValueError,KeyError,TypeError,OverflowError,
            AttributeError,ImportError,RuntimeError,IndexError):
        print(json.dumps({
            "kind":"P0-SANITIZED-SEVEN-CAPTURE-R4-R30-ORIGIN-TRIAGE",
            "status":"ABSTAIN_ORIGINAL_SOURCE_OR_SCRIPT_UNTRUSTED",
            "training_approved":False,
            "allowed_to_publish":False,
        },sort_keys=True))
        return 2
    print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
