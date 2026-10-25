# Merging requirements — agent self-merge policy

**Owner authorization:** Agents S001–S005 with existing GitHub write permission **may merge their own pull requests** after reviewing and explicitly satisfying this document. Routine S000 approval is **not required** for a qualifying PR. This is the operator's standing permission, not permission to bypass repository branch protection or GitHub review requirements.

**SPOCOC = Single Point of Control Over Change:** One canonical implementation and accountable owner per shared behavior. Self-merge delegates routine integration; it does **not** allow an agent to unilaterally change another owner's public interfaces, rewrite shared history, or create parallel production systems.

## Mandatory self-merge checklist

Before merging, the PR author must post a **MERGE READY** comment containing all the following:

- [ ] **Scope/owner:** I own the changed implementation, or the responsible canonical owner reviewed and acknowledged the cross-domain change.
- [ ] **Source:** My branch is based on the latest `origin/main`; I checked the current PR queue for overlapping files, pending dependencies, and superseding PRs. No unreviewed sibling-worktree code or duplicated launcher/score schema.
- [ ] **Tests:** I ran `py -m unittest discover -s tests -v` (or `python -m unittest discover -s tests -v`), plus targeted tests for the change, with exact command, environment and pass/fail results. If unavailable or failing, do **not** self-merge; report the blocker. A GitHub green badge or synthetic trial alone is not proof of a Windows/Dolphin live test.
- [ ] **Compatibility:** Existing `bash scripts/golf.sh` / `py scripts/golf.py` paths, registry IDs, upstream/downstream contracts, and current known-good experiment behaviors remain valid; any required migration is documented and approved by affected owners.
- [ ] **Safety and provenance:** A real-game action still requires explicit live opt-in, one canonical Dolphin startup/checkpoint/menu sequence, no unintended second launch/reset, and no claims of verified contact/score from RPC acknowledgement. No raw RAM, ROMs, savestates, credentials, private paths or local config in Git; outputs are classified.
- [ ] **Mergeability:** The PR is not draft, has no conflicts, unresolved review objections, failing required checks, or dependency PR still pending. Respect GitHub branch protection.
- [ ] **Handoff:** I documented hypothesis, changed paths, what tests were actually run, limitations, downstream consumer, and follow-up owner; I linked any related issue/PR.
- [ ] **Integration method:** Use squash merge by default, with current head SHA checked, and never force-push or overwrite someone else's branch to get a merge through.

After merge: post commit SHA and a short handoff to affected GitHub issues/PRs, update your branch from main, and identify next actionable work.

## When S000 or another owner must review first

Do not self-merge if the change modifies a **shared contract owned by someone else**, including: `wii_ai_golf.cli`, `lab.core`, `research/experiments.json`, Dolphin boot/savestate/input contracts, outcome schema, shared evidence publication, or cross-agent APIs. Obtain explicit acknowledgment from the relevant canonical owner and S000 for cross-agent compatibility before merging. Once acknowledged and every checklist item passes, the submitting agent may execute the merge themselves.

Likewise, escalate merge conflicts, test failures, ambiguous controller behavior, permission/security/privacy changes, new destructive actions, or incompatible design choices. An author may resolve a conflict in their own branch but must rerun tests and recheck dependencies afterward.

## Code ownership

S000: operator CLI, shared registry, orchestration, contracts. S001: Dolphin startup and controller RPC. S002: capture and measurement provenance. S003: swing parameterization/model. S004: optimization. S005: held-out evaluation. Domain ownership does not waive shared-interface review.

## Delegation boundaries

This policy grants **merge authorization**, not permission for agents to execute unattended live swings, automatically publish private captures, push directly to main, disable safety gates, or claim they ran tests they did not run. Repository permissions and existing branch protections continue to apply. If your account cannot merge, request maintainer help in the PR rather than weakening protections.
