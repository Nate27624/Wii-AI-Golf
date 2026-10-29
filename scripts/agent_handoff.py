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
        help=f"Canonical URL syntax for https://github.com/{REPO}/issues/N or /pull/N; existence must be checked in GitHub",
    )
    args = parser.parse_args()
    for label, value in (("instance", args.instance), ("successor", args.successor)):
        if not INSTANCE.fullmatch(value) or not value.startswith(args.role + "-"):
            parser.error(f"{label} must be an S00N-name matching --role")
    if args.instance == args.successor:
        parser.error("successor must use a different instance ID from the outgoing agent")
    if not THREAD.fullmatch(args.thread):
        parser.error("thread must be a canonical issue/PR URL in Nate27624/Wii-AI-Golf")

    root = Path(__file__).resolve().parents[1]
    branch = local_git(root, "branch", "--show-current") or "unavailable"
    head = local_git(root, "rev-parse", "HEAD") or "unavailable"
    status = local_git(root, "status", "--porcelain")
    cleanliness = "unavailable" if status == "unavailable" else ("clean" if not status else "dirty")

    print("=== OUTGOING AGENT: POST THIS TO THE EXISTING CANONICAL GITHUB THREAD ===")
    print(f"[{args.instance}] SUCCESSION HANDOFF")
    print(f"Role: {args.role} | Outgoing: {args.instance} | Proposed successor: {args.successor}")
    print(f"Canonical thread URL (syntax verified; GitHub existence and ownership NOT verified): {args.thread}")
    print("Before posting, verify the issue/PR exists and remains your assigned thread in GitHub.")
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
    print("=== NEW CHAT: APPEND THIS SUPPLEMENT TO YOUR EXISTING V2 PROMPT ===")
    print(f"Take over {args.role} from {args.instance} as NEW instance {args.successor}.")
    print(f"Read the latest [{args.instance}] SUCCESSION HANDOFF at {args.thread}.")
    print("Read current main, docs/v2-navigation.md, docs/v2-agent-charter.md,")
    print("docs/v2-agent-continuity.md and root merging.md; check live overlaps.")
    print(f"Initialize as --role {args.role} --instance {args.successor}.")
    print(f"Post [{args.successor}] CLAIM referencing the outgoing handoff link")
    print("before changing files. Retain the role's existing goals and evidence.")
    print("Do substantive work; no duplicate PR or live gameplay without consent.")
    print()
    print("This tool only prints templates. Post the filled handoff to GitHub and")
    print("start the next chat with your existing prompt; no agent was auto-created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
