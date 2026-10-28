"""One-command original bank SHA-gated P0 SimulateManager +0x6B4 source triage.

Reuses *immutable* #231 source pin, original 14-bank SHA before+after,
existing Omega secure subprocess and archive guards. No new game action,
pointer scan or data upload. Unresolved source paths explicitly abstain.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import uuid

_HERE = str(Path(__file__).resolve().parent)
if _HERE in sys.path: sys.path.remove(_HERE)
sys.path.insert(0,_HERE)
import omega_p0_offline_private as omega


def run(repo, archive=None):
    repo=Path(repo).resolve(strict=True)
    if not (repo/".git").exists():
        raise omega.Abstain("P0 source worktree not verified")
    location,manifest=omega._archive(repo,archive)
    old_manifest=omega._file_digest(manifest)
    canonical=None
    try:
        canonical=omega._worktree(repo,"canonical",uuid.uuid4().hex[:12])
        omega._run_test(repo,"base","test_p0_simulate_r3_6b4_source.py")
        omega._run_test(repo,"savegpr","test_p0_simulate_savegpr26_source.py")
        omega._run_test(canonical,"canonical",
                        "test_p0_seven_numbered_source_pairs_private.py")
        orig=canonical/"scripts"/"audit_p0_seven_numbered_source_pairs_private.py"
        omega._json_study(repo,[orig,"--archive",location],
            "P0-SANITIZED-SEVEN-NUMBERED-SOURCE-PAIR-AUDIT")
        analyzed=omega._json_study(repo,[
            repo/"scripts"/"audit_p0_simulate_r3_6b4_private.py",
            "--archive",location,
            "--canonical-source-scripts",canonical/"scripts"],
            "P0-SANITIZED-SEVEN-SIMULATE-6B4-R3-SOURCE")
        if (analyzed.get("original_fourteen_bank_sha_pre_and_post_verified") is not True
                or analyzed.get("rspe01_rev1_source_selected_scene_all_seven") is not True
                or analyzed.get("ppc_source_window_equal_all_seven") is not True):
            raise omega.Abstain("source-gated inner result missing")
        static = analyzed.get("static_register_save_helper_prologue")
        if (type(static) is not dict or
                static.get("kind") != "P0-PPC-STATIC-SIMULATE-ENTRY-R3-SAVEGPR26-PROLOGUE" or
                static.get("training_approved") is not False or
                static.get("allowed_to_publish") is not False or
                static.get("actual_r3_dynamic_object_type_verified") is not False or
                static.get("value_loaded_from_member_is_global_or_roster_ball_verified") is not False):
            raise omega.Abstain("unqualified source compiler-save helper report")
        omega._json_study(repo,[orig,"--archive",location],
            "P0-SANITIZED-SEVEN-NUMBERED-SOURCE-PAIR-AUDIT")
        if old_manifest!=omega._file_digest(manifest):
            raise omega.Abstain("manifest changed during study")
        return {
            "kind":"P0-SANITIZED-SIMULATE-R3-6B4-OMEGA-HANDOFF",
            "status":"PASS_SOURCE_QUALIFIED_STATIC_ONLY",
            "all_fourteen_original_bank_SHA_verified_before_and_after":True,
            "canonical_231_revision_pinned_not_moving_head":True,
            "seven_source_windows_consistent":True,
            "static_source":analyzed["source_load_base_r3_hint"],
            "static_compiler_savegpr26_prologue":static,
            "dynamic_receiver_object_identified":False,
            "physical_xyz_velocity_power_impact_score_verified":False,
            "training_approved":False,"allowed_to_publish":False,
        }
    finally:
        if canonical is not None:
            omega._remove_tree(repo,canonical)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",required=True,type=Path)
    p.add_argument("--archive",type=Path)
    args=p.parse_args(argv)
    try:
        output=run(args.repo,args.archive)
    except (omega.Abstain,OSError,ValueError,KeyError,TypeError,
            AttributeError,OverflowError,IndexError,RuntimeError):
        print(json.dumps({
            "kind":"P0-SANITIZED-SIMULATE-R3-6B4-OMEGA-HANDOFF",
            "status":"ABSTAIN_SOURCE_OR_PRIVATE_ARCHIVE_GATE",
            "training_approved":False,"allowed_to_publish":False,
        },sort_keys=True))
        return 2
    print(json.dumps(output,sort_keys=True,indent=2,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
