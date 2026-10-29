#!/usr/bin/env python3
"""Read-only agent initialization. No remote calls, process launches, or repository writes."""
from __future__ import annotations
import argparse
import re
import subprocess
from pathlib import Path

ROLES = {
    "S000": "Integration / coordination",
    "S001": "Dolphin runtime / input",
    "S002": "Capture / source provenance",
    "S003": "Control modeling",
    "S004": "Training / optimization",
    "S005": "Evaluation / censoring",
}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=ROLES, required=True)
    parser.add_argument("--instance", required=True, help="Unique instance identifier: e.g. S002-memory-a")
    args = parser.parse_args()
    if not re.fullmatch(r"S00[0-5]-[a-z0-9][a-z0-9-]{1,39}", args.instance):
        parser.error("Instance must be S00N-name, lowercase letters/digits/hyphens")
    if not args.instance.startswith(args.role + "-"):
        parser.error("Instance prefix must match selected role")
    root = Path(__file__).resolve().parents[1]
    charter = root / "docs" / "v2-agent-charter.md"
    if not charter.exists():
        parser.error("Missing docs/v2-agent-charter.md: use the consolidation branch")
    def git(*cmd: str) -> str:
        try:
            return subprocess.check_output(
                ["git", "-C", str(root), *cmd],
                text=True, stderr=subprocess.DEVNULL, timeout=8
            ).strip()
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return "unavailable"
    print(f"AGENT_ID={args.instance}")
    print(f"ROLE={args.role}: {ROLES[args.role]}")
    print(f"BRANCH={git('branch', '--show-current')}")
    print(f"HEAD={git('rev-parse', 'HEAD')}")
    print(f"WORKTREE_STATUS={git('status', '--porcelain') or 'clean'}")
    print(f"CHARTER={charter.relative_to(root)}")
    if args.role == "S000":
        manager = root / "docs" / "S000-manager-playbook.md"
        if not manager.is_file():
            parser.error("Missing S000 manager playbook")
        print(f"MANAGER_PLAYBOOK={manager.relative_to(root).as_posix()}")
        print("MANAGER_DUTY=Collect agent questions; resolve from evidence; escalate operator-only decisions.")
        print("MANAGER_DUTY=Keep roles focused, prevent duplicate implementations, and route answers back.")
    print("READ root merging.md (canonical self-merge checklist) and docs/p0-pr-consolidation-lanes.md")
    print("READ current owner PR, inspect latest main and sibling overlaps.")
    print("POST: [AGENT_ID] CLAIM | owner PR | inputs | outputs | changed paths | test plan")
    print("POST: [AGENT_ID] HANDOFF | branch/head | tests | evidence | blockers | next owner")
    print("POST: [AGENT_ID] QUESTION | blocker | evidence | options | suggested resolution")
    print("NO LIVE DOLPHIN; NO RAW CAPTURE; NO AUTO MERGE/PUBLISH.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
