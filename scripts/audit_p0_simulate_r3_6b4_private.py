"""Source-qualified original seven-bank static SimulateManager +0x6B4 base study.

Reads only the preserved original private archive with canonical #231 helper;
validates all 14 immutable bank SHA entries before AND after, Rev1 source
selected scene in all seven, and identical bounded PPC code windows. Emits
categorical source-level hints only; never raw words/heap, private files or SHA.
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
if _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)
import audit_p0_authenticated_receiver_chain_private as existing
import review_p0_simulate_r3_6b4_source as probe


def analyze(archive, canonical_source_scripts):
    base = Path(canonical_source_scripts).resolve(strict=True)
    if not base.is_dir():
        raise ValueError("original source reader missing")
    sys.path.insert(0, str(base))
    seven = existing._import_from_path(
        "canonical_231_for_simulate_r3_6b4",
        base / "audit_p0_seven_numbered_source_pairs_private.py")
    original = Path(archive)
    folders = seven._check_archive(original)
    source_hash = None
    result = None
    for n in range(1, 8):
        with ExitStack() as stack:
            mm = []
            for i, size in enumerate(seven.SIZE):
                path = seven.src._file(folders[n], f"{n}.{i+1}.raw", size)
                f = stack.enter_context(path.open("rb"))
                mm.append(stack.enter_context(mmap.mmap(
                    f.fileno(), 0, access=mmap.ACCESS_READ)))
            rd = seven.roster.TwoBankReader(*mm)
            seven._get(rd)  # Canonical Rev1 scene, selected ball/pin/start.
            dig = hashlib.sha256()
            for pc in range(probe.ENTRY,probe.ENTRY+probe.upstream.SOURCE_WINDOW,4):
                w = rd.u32(pc)
                if type(w) is not int or not 0 <= w <= 0xFFFFFFFF:
                    raise ValueError("unqualified source PPC word")
                dig.update(w.to_bytes(4, "big"))
            digest = dig.digest()  # Never print or include digest in output.
            if source_hash is None:
                source_hash = digest
            elif source_hash != digest:
                raise ValueError("inconsistent original Rev1 source code")
            row = probe.analyze(rd.u32)
            if result is None:
                result = row
            elif row != result:
                raise ValueError("source triage differs across original samples")
    seven._check_archive(original)  # all 14 original bank SHAs again
    if result is None or result.get("training_approved") is not False:
        raise ValueError("source analysis did not complete safely")
    return {
        "kind": "P0-SANITIZED-SEVEN-SIMULATE-6B4-R3-SOURCE",
        "original_fourteen_bank_sha_pre_and_post_verified": True,
        "rspe01_rev1_source_selected_scene_all_seven": True,
        "ppc_source_window_equal_all_seven": True,
        "source_load_base_r3_hint": result,
        "same_guest_frame_or_shot_verified": False,
        "rendered_ball_global_or_roster_receiver_verified": False,
        "velocity_xyz_power_contact_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--canonical-source-scripts", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        r = analyze(args.archive,args.canonical_source_scripts)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,
            ImportError,OverflowError,IndexError,RuntimeError):
        print(json.dumps({
            "kind":"P0-SANITIZED-SEVEN-SIMULATE-6B4-R3-SOURCE",
            "status":"ABSTAIN_COHORT_OR_SOURCE_QUALIFICATION",
            "training_approved":False,"allowed_to_publish":False
        },sort_keys=True))
        return 2
    print(json.dumps(r,sort_keys=True,indent=2,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
