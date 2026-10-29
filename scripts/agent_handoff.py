#!/usr/bin/env python3
"""Offline, read-only successor handoff template for existing V2 agent chats.

Does not start another chat, contact GitHub, update claims or authorize gameplay.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

REPO = "Nate27624/Wii-AI-Golf"
INSTANCE = re.compile(r"^S00[0-5]-[a-z0-9][a-z0-9-]{1,39}$")
THREAD = re.compile(
    r"^https://github\.com/Nate27624/Wii-AI-Golf/(?:issues|pull)/[1-9][0-9]*/?$"
)


def local_git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=8,
        ).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unavailable"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=tuple(f"S00{i}" for i in range(6)))
    parser.add_argument("--instance", required=True, help="Existing instance, e.g. S002-memory-a")
    parser.add_argument("--successor", required=True, help="New, different instance in the same role")
    parser.add_argument(
        "--thread", required=True,
        help=f"Canonical https://github.com/{REPO}/issues/N or /pull/N (URL format only; verify existence and ownership on GitHub)",
    )
    parser.add_argument(
        "--handoff-url",
        help="Optional permalink to the posted SUCCESSION HANDOFF issue comment",
    )
    args = parser.parse_args()
    for label, value in (("instance", args.instance), ("successor", args.successor)):
        if not INSTANCE.fullmatch(value) or not value.startswith(args.role + "-"):
            parser.error(f"{label} must be an S00N-name matching --role")
    if args.instance == args.successor:
        parser.error("successor must use a different instance ID from the outgoing agent")
    if not THREAD.fullmatch(args.thread):
        parser.error("thread must be a canonical issue/PR URL in Nate27624/Wii-AI-Golf")

    handoff_reference = args.thread
    if args.handoff_url:
        expected_prefix = args.thread.rstrip("/") + "#issuecomment-"
        if not args.handoff_url.startswith(expected_prefix):
            parser.error("--handoff-url must be an issuecomment permalink on --thread")
        suffix = args.handoff_url[len(expected_prefix):]
        if not re.fullmatch(r"[1-9][0-9]*", suffix):
            parser.error("--handoff-url must have a positive numeric issuecomment ID")
        handoff_reference = args.handoff_url

    root = Path(__file__).resolve().parents[1]
    branch = local_git(root, "branch", "--show-current") or "unavailable"
    head = local_git(root, "rev-parse", "HEAD") or "unavailable"
    status = local_git(root, "status", "--porcelain")
    cleanliness = "unavailable" if status == "unavailable" else ("clean" if not status else "dirty")

    print("=== OUTGOING AGENT: POST THIS TO THE EXISTING CANONICAL GITHUB THREAD ===")
    print(f"[{args.instance}] SUCCESSION HANDOFF")
    print(f"Role: {args.role} | Outgoing: {args.instance} | Proposed successor: {args.successor}")
    print(f"Canonical thread URL (syntax checked; existence and ownership NOT verified): {args.thread}")
    print("Outgoing agent must check the thread exists and ownership is current on GitHub.")
    print("Verified remote main SHA: <fetch latest main; DO NOT substitute local HEAD>")
    print(f"Local branch at generation: {branch}")
    print(f"Local HEAD at generation: {head}")
    print(f"Local working tree: {cleanliness} (check for unpublished local work)")
    print("Owned paths/interfaces and active claim: <exact paths + claim link>")
    print("Changes completed / integration status: <PR links, merges, immutable SHAs>")
    print("Tests actually executed: <commands, OS, results, CI URLs; or NOT RUN>")
    print("Unmerged changes / dependency PRs: <heads, overlap, outstanding reviews>")
    print("Evidence limits and blockers: <confirmed facts, unknowns, operator-only needs>")
    print("Next ONE falsifiable task: <scope, input/output, acceptance tests>")
    print("Ownership transfer: outgoing instance stops editing claimed paths;")
    print("  successor must verify fresh main/claims before posting its own CLAIM.")
    print("Safety: no raw RAM/ROM, savestates, paths, credentials or private data;")
    print("  no implicit Dolphin launch, shot, publication, or training approval.")
    print()
    print("=== NEW CHAT PROMPT — COPY FROM NEXT LINE THROUGH END MARKER ===")
    print("# Wii Sports Golf AI — V2 Successor Agent")
    print(f"Repository: https://github.com/{REPO}")
    print(f"Role: {args.role}; new instance: {args.successor}")
    print(f"Outgoing instance: {args.instance}")
    print(f"Canonical owner thread: {args.thread}")
    print(f"Outgoing SUCCESSION HANDOFF reference: {handoff_reference}")
    print()
    print(f"You are {args.successor}, the successor for {args.instance}.")
    print("You are replacing the outgoing agent, not starting a second parallel owner.")
    print("Continue its unfinished objectives and preserve its existing role boundaries.")
    print()
    print("FIRST: Fetch current main. Read merging.md, docs/v2-navigation.md,")
    print("docs/v2-agent-charter.md, docs/v2-agent-continuity.md,")
    print("docs/v2-universal-prompts.md, docs/v2-evidence-gates.md and")
    print("the relevant role/manager documentation.")
    print("Read the latest [S000-manager] PRIORITY BOARD V2 on PR #320;")
    print("recheck its pinned main SHA and live owner CLAIMs before selecting")
    print("the next in-role task. Your predecessor's unfinished claimed work")
    print("takes precedence over an unrelated board recommendation.")
    print("Verify the canonical GitHub issue/PR exists and that the outgoing")
    print("SUCCESSION HANDOFF is authentic, recent, and from the stated instance.")
    print("Recover its exact owner claims, PR/branch HEADs, changed paths, tests")
    print("actually run, blockers and single next objective; check live competing")
    print("claims and unresolved PR conflicts. Do not rely on this prompt as proof")
    print("that the thread exists, any remote SHA is current, or work is merged.")
    print()
    print(f"Initialize with: python scripts/agent_init.py --mode init --role {args.role} "
          f"--instance {args.successor} --live")
    print("If no authenticated gh CLI exists, use connected GitHub instead;")
    print("the helper never verifies or reserves an agent's ownership.")
    print(f"Before modifying files, post [{args.successor}] CLAIM on {args.thread},")
    print(f"linking the [{args.instance}] SUCCESSION HANDOFF and specifying exact")
    print("owned files, boundaries, acceptance tests, and remaining dependencies.")
    print("Do not inherit uncommitted work or claim unverified test results.")
    print("Then perform substantive work on the next bounded, highest-value task")
    print("immediately; coordinate overlaps using existing GitHub issues/PRs.")
    print("Use one canonical implementation per behavior and do not create duplicate")
    print("PRs merely to document research. Self-merge only when every merging.md")
    print("gate is met, including required exact-head Windows/Ubuntu offline CI.")
    print("Preserve historical source-backed evidence, negative results and branches.")
    print("Never commit ROMs, RAM, savestates, private captures, paths or secrets.")
    print("No live Dolphin experiment, controller input or private publication")
    print("without separate explicit authorization. Do not promote world XYZ,")
    print("velocity, game scores or training eligibility without verified evidence;")
    print("off-green 100-foot penalties are censored outcomes, not physical carry.")
    print("Do not claim to be working asynchronously or to auto-create another chat.")
    print()
    print("End with exactly one OPERATOR STATUS: CONTINUE, ACTION REQUIRED,")
    print("or DECISION REQUIRED. Only escalate irreducible operator decisions.")
    print("=== END NEW CHAT PROMPT ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
