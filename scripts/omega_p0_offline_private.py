"""One-command, fail-closed OFFLINE P0 study coordinator (RSPE01 Rev1).

Never launches Dolphin, drives inputs, writes game RAM, uploads dumps, or trains.
Downloads only pinned Git code into detached worktrees under the repo parent.
Uses original 14-bank SHA manifest and verified source readers unchanged.
Output is allowlisted categorical evidence, not raw ROM/RAM, paths, or hashes.

Design rule: moving PR heads must NOT invalidate previously reviewed commits.
Never silently update a source pin to the latest tip.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

PINS = {
    "canonical": (231, "89aa3a2bd3e82532c4051168a466498e7195f596"),
    "cfg": (254, "8696a46a315499f220ee7c87580a21dc99f21462"),
    "label_graph": (250, "2e02a779b3a4432ca6b6d8fc9bbf88234ef71c10"),
}
TESTS = {
    "omega": "test_p0_omega_offline_private.py",
    "operand": "test_p0_outer_operand_r4_r30_source.py",
    "receiver": "test_p0_authenticated_receiver_chain_private.py",
    "outer": "test_p0_outer_receiver_argument_source.py",
    "canonical": "test_p0_seven_numbered_source_pairs_private.py",
    "cfg": "test_p0_cache_receiver_cfg_mustdef.py",
    "label_graph": "test_p0_seven_label_free_graph_private.py",
}

class Abstain(Exception):
    """Expected safe failure, never forward underlying private paths/values."""


def _exec(args, *, cwd, timeout=600):
    try:
        result = subprocess.run(
            [str(x) for x in args], cwd=str(cwd), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Abstain("local subprocess unavailable or timed out") from exc
    if result.returncode:
        raise Abstain("pinned source check or offline study returned nonzero")
    return result.stdout


def _git(repo, *args):
    return _exec(["git", "-C", repo, *args], cwd=repo, timeout=240).strip()


def _exists_git_object(repo, sha):
    try:
        _git(repo, "cat-file", "-e", sha + "^{commit}")
        return True
    except Abstain:
        return False


def ensure_pinned_commit(repo, name, fetch=True):
    """Obtain immutable commit even if a PR head moved since source review."""
    number, sha = PINS[name]
    if not _exists_git_object(repo, sha) and fetch:
        try:
            _git(repo, "fetch", "--no-tags", "origin", f"refs/pull/{number}/head")
        except Abstain:
            pass
    if not _exists_git_object(repo, sha) and fetch:
        try:
            _git(repo, "fetch", "--no-tags", "origin", sha)
        except Abstain:
            pass
    if not _exists_git_object(repo, sha):
        raise Abstain("reviewed pinned commit not obtainable; source was not substituted")
    if _git(repo, "rev-parse", sha + "^{commit}").lower() != sha:
        raise Abstain("reviewed commit identity differs")
    return sha


def _worktree(repo, name, nonce):
    sha = ensure_pinned_commit(repo, name)
    # Must be a DIRECT SIBLING of the project repo for the #231 DATA_ROOT.
    path = repo.parent / (f"Wii-AI-Golf-P0-Omega-{name}-{nonce}")
    if path.exists() or path.is_symlink():
        raise Abstain("temporary study worktree path collision")
    _git(repo, "worktree", "add", "--detach", str(path), sha)
    return path


def _remove_tree(repo, path):
    try:
        _git(repo, "worktree", "remove", "--force", str(path))
    except Abstain:
        # Do not delete any unexpected user-owned paths.
        pass


def _archive(repo, specified):
    root = (repo.parent / "Wii-AI-Golf-Data" / "captures").resolve(strict=True)
    if specified:
        archive = Path(specified).resolve(strict=True)
    else:
        choices = sorted(p.resolve() for p in root.glob("p0-new-cohort-*-PRIVATE")
                         if p.is_dir() and (p / "manifest-PRIVATE.json").is_file())
        if len(choices) != 1:
            raise Abstain("no unique canonical seven-bank archive; specify --archive")
        archive = choices[0]
    if archive.parent != root or not archive.name.startswith("p0-new-cohort-"):
        raise Abstain("selected archive is outside canonical private captures")
    manifest = archive / "manifest-PRIVATE.json"
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 65536:
        raise Abstain("canonical private manifest invalid")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise Abstain("canonical manifest cannot be decoded") from exc
    if (type(data) is not dict or data.get("kind") != "p0-private-numbered-capture-inventory"
            or data.get("capture_count") != 7
            or data.get("capture_numbers") != list(range(1, 8))
            or data.get("human_phase_file_mapping_verified") is not False
            or data.get("training_approved") is not False):
        raise Abstain("canonical archive format/phase/training gate failed")
    return archive, manifest


def _file_digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.digest()   # PRIVATE: never return or print digest.


def _run_test(repo, name, filename):
    _exec([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p",
           filename, "-v"], cwd=repo, timeout=120)


def _json_study(repo, args, expected_kind):
    payload = _exec([sys.executable, "-I", *args], cwd=repo, timeout=600)
    if len(payload) > 150000:
        raise Abstain("study output exceeded bounded privacy contract")
    try:
        result = json.loads(payload)
    except (TypeError, ValueError) as exc:
        raise Abstain("study failed sanitized JSON contract") from exc
    if type(result) is not dict or result.get("kind") != expected_kind:
        raise Abstain("study output kind differs from exact approved schema")
    if result.get("training_approved") is not False or result.get("allowed_to_publish") is not False:
        raise Abstain("study attempted to promote training/publication")
    return result


def _graph_extract(graph):
    pairs = graph.get("pairs")
    nodes = graph.get("nodes")
    if (graph.get("capture_count") != 7 or graph.get("unordered_pairs_exhaustively_compared") != 21
            or graph.get("original_archive_SHA_checked_before_and_after") is not True
            or graph.get("human_phase_to_file_mapping_machine_verified") is not False
            or type(pairs) is not list or len(pairs) != 21
            or type(nodes) is not list or len(nodes) != 7):
        raise Abstain("label-free source graph evidence contract failed")
    matches = [p for p in pairs if p.get("same_source_owner_hole_pin_tee_and_config") is True]
    unknown = [p for p in pairs if p.get("same_source_owner_hole_pin_tee_and_config") is False]
    if len(matches) + len(unknown) != 21:
        raise Abstain("unclassified graph comparison")
    focal = []
    for ids in ([1,2], [3,4], [5,6], [5,7], [6,7]):
        found = [p for p in pairs if p.get("capture_pair_unordered") == ids]
        if len(found) != 1:
            raise Abstain("missing or duplicated graph pair")
        pair = found[0]
        focal.append({
            "capture_ids_unordered": ids,
            "source_context_equivalent": pair.get("same_source_owner_hole_pin_tee_and_config"),
            "selected_current_changed_components": pair.get("current_changed_components"),
            "cache_CC_changed_components": pair.get("cache_CC_changed_components"),
            "cache_F0_changed_components": pair.get("cache_F0_changed_components"),
            "cache_FC_changed_components": pair.get("cache_FC_changed_components"),
        })
    return {
        "context_group_count": graph.get("source_context_group_count"),
        "context_qualified_unordered_pairs": len(matches),
        "context_incompatible_abstained_pairs": len(unknown),
        "pairs_of_interest": focal,
    }


def _receiver_extract(recv):
    chains = recv.get("receiver_chains")
    if (recv.get("seven_original_sha_verified_before_and_after") is not True
            or recv.get("source_global_outside_four_roster_in_all_captures") not in (True, False)
            or type(chains) is not list or len(chains) != 2):
        raise Abstain("receiver chain source qualification failed")
    expected = ("SimulateManager_outer_to_ball_local", "MapObjBall_outer_to_ball_local")
    if tuple(r.get("outer_source_function") for r in chains) != expected:
        raise Abstain("receiver chain ordering not approved")
    return {
        "outside_four_player_ball_roster_7_of_7":
            recv.get("source_global_outside_four_roster_in_all_captures"),
        "both_inner_cfg_static_must_flow": recv.get("both_inner_static_cfg_must_flow"),
        "any_direct_global_source_r3_load_syntax_candidate":
            recv.get("any_static_source_global_load_candidate"),
        "source_to_inner_call_chains": [
            {
                "outer_source_function":r.get("outer_source_function"),
                "outer_bounded_call_count":r.get("outer_direct_call_count_bounded"),
                "outer_status":r.get("outer_source_status"),
                "near_call_r3_source":r.get("near_call_r3_class"),
                "global_or_roster_hint":r.get("near_call_r3_provenance_hint"),
                "inner_source_function":r.get("inner_source_function"),
                "inner_cfg_status":r.get("inner_cfg_status"),
            } for r in chains
        ],
    }


def _operand_extract(report):
    rows=report.get("source_operand_hints")
    if (report.get("original_fourteen_native_banks_sha_verified_before_and_after") is not True
            or report.get("two_source_code_windows_identical_all_seven") is not True
            or report.get("source_selected_scene_gated_for_all_seven") is not True
            or type(rows) is not list or len(rows)!=2):
        raise Abstain("upstream operand original source qualification missing")
    expected=(("SimulateManager_outer_to_ball_local","r4"),
              ("MapObjBall_outer_to_ball_local","r30"))
    if tuple((x.get("outer_source_function"),x.get("tracked_source_operand"))
             for x in rows)!=expected:
        raise Abstain("upstream operand source case changed")
    return [{
        "outer_source_function":x["outer_source_function"],
        "tracked_operand":x["tracked_source_operand"],
        "nearest_write_class":x.get("nearest_pre_mr_operand_write_class"),
        "source_status":x.get("status"),
        "control_flow_hazard":x.get("control_transfer_after_candidate_write"),
        "all_path_source_verified":False,
    } for x in rows]


def study(repo, archive=None, *, tests=True):
    repo = Path(repo).resolve(strict=True)
    if not (repo / ".git").exists():
        raise Abstain("omega runner must run from a verified Git checkout")
    local, manifest = _archive(repo, archive)
    manifest_before = _file_digest(manifest)
    nonce = uuid.uuid4().hex[:12]
    checked = {}
    try:
        for name in PINS:
            checked[name] = _worktree(repo, name, nonce)
        if any(path.parent != repo.parent for path in checked.values()):
            raise Abstain("source worktree and canonical data root are not siblings")
        if tests:
            for task in ("receiver", "outer", "operand", "omega"):
                _run_test(repo, "omega", TESTS[task])
            for name in PINS:
                _run_test(checked[name], name, TESTS[name])
        canonical = checked["canonical"] / "scripts" / "audit_p0_seven_numbered_source_pairs_private.py"
        _json_study(repo, [canonical, "--archive", local],
                    "P0-SANITIZED-SEVEN-NUMBERED-SOURCE-PAIR-AUDIT")
        graph = _json_study(repo,
            [checked["label_graph"] / "scripts" /
             "audit_p0_seven_label_free_graph_private.py", "--archive", local],
            "P0-SANITIZED-SEVEN-LABEL-AGNOSTIC-SOURCE-CONTEXT-GRAPH")
        graph_summary = _graph_extract(graph)
        recv = _json_study(repo,
            [repo / "scripts" / "audit_p0_authenticated_receiver_chain_private.py",
             "--archive", local,
             "--canonical-source-scripts", checked["canonical"] / "scripts",
             "--cfg-script", checked["cfg"] / "scripts" /
             "review_p0_cache_receiver_cfg_mustdef.py"],
            "P0-SANITIZED-SOURCE-GATED-OUTER-INNER-RECEIVER-JOIN")
        receiver_summary = _receiver_extract(recv)
        operands = _json_study(repo,
            [repo / "scripts" / "audit_p0_outer_operand_r4_r30_private.py",
             "--archive", local,
             "--canonical-source-scripts", checked["canonical"] / "scripts"],
            "P0-SANITIZED-SEVEN-CAPTURE-R4-R30-ORIGIN-TRIAGE")
        operand_summary = _operand_extract(operands)
        _json_study(repo, [canonical, "--archive", local],
                    "P0-SANITIZED-SEVEN-NUMBERED-SOURCE-PAIR-AUDIT")
        if _file_digest(manifest) != manifest_before:
            raise Abstain("private canonical manifest was changed during analysis")
        return {
            "kind": "P0-OMEGA-OFFLINE-SANITIZED-RECEIVER-AND-CACHE-AUDIT",
            "status": "PASS_SOURCE_QUALIFIED_STATIC_ONLY",
            "source_pins_are_immutable_not_moving_PR_heads": True,
            "original_14_bank_SHA_verified_before_and_after": True,
            "seven_rev1_selected_scenes_source_gated": True,
            "local_synthetic_tests_passed": bool(tests),
            "provisional_human_phase_labels_treated_as_ground_truth": False,
            "label_free_graph": graph_summary,
            "source_receiver_chain": receiver_summary,
            "outer_r4_r30_source_hints": operand_summary,
            "actual_runtime_receiver_global_vs_player_ball_verified": False,
            "rendered_projectile_ownership_verified": False,
            "guest_frame_or_same_shot_proven": False,
            "physical_xyz_velocity_impact_power_score_verified": False,
            "training_approved": False,
            "allowed_to_publish": False,
        }
    finally:
        for path in reversed(list(checked.values())):
            _remove_tree(repo, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args(argv)
    try:
        result = study(args.repo, args.archive)
    except (Abstain, OSError, TypeError, ValueError, KeyError, IndexError,
            OverflowError, RuntimeError):
        print(json.dumps({
            "kind":"P0-OMEGA-OFFLINE-SANITIZED-RECEIVER-AND-CACHE-AUDIT",
            "status":"ABSTAIN_SAFE_SOURCE_OR_PRIVATE_ARCHIVE_CHECK",
            "training_approved":False,
            "allowed_to_publish":False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
