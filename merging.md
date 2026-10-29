# merging.md — Objective self-merge policy

**Authority:** The operator authorizes agents S000–S005 to **self-merge their own work** when and only when every applicable item below passes. Routine S000/other-agent discretionary approval is **not** a requirement. This policy does not override GitHub branch protection, legal restrictions, security/privacy boundaries, or the separate explicit operator opt-in required for a live Dolphin shot.

This is the **single canonical merge procedure**. `docs/merging-requirements.md` is retained only as a compatibility pointer.

## Required merge checklist — all PASS or do not merge

1. **Ownership and purpose:** Write a concrete change summary; name role/instance, changed paths, input/output interfaces, consumers and the reason an existing implementation is insufficient. One canonical production path per behavior. Research-only observations should go on an existing issue rather than generate a new PR.
2. **Current ancestry:** Fetch latest `origin/main`; PR head includes latest main and has no unresolved dependency PR. Do not rewrite another agent's branch, force-push, or commit directly to main. When rebased/updated, rerun all checks on the **new exact head**.
3. **No conflicting implementation:** Inspect the open PR queue and file overlap. If another active PR edits the same behavior/interface, integrate the unique work into one canonical owner branch **before** merging. An unresolved conflict is a STOP condition—not an invitation to merge both versions.
4. **Targeted tests:** Run meaningful new and existing focused tests for changed behavior. Include negative/fail-closed and privacy cases where relevant. Record exact command and result.
5. **Full offline suite:** Run `python -m unittest discover -s tests -v` (Windows `py -m unittest discover -s tests -v` is equivalent) on the **exact proposed head**, with no failing tests. Required GitHub CI checks must pass on all configured platforms (Windows and Ubuntu when configured). If a platform is unavailable, required checks fail, or the suite is red, **do not merge**.
6. **Compatibility:** No unintended changes to established CLI (`scripts/golf.py`, `scripts/golf.sh`), launcher, Dolphin input/boot, evidence schema, scorer, producer/consumer APIs or known-good experiments. If changing a shared contract, explicitly update all affected consumers/tests and demonstrate compatibility or a documented migration in one coherent PR. Incompatible pending work blocks merge until integrated; **no approval ritual can substitute for compatibility evidence**.
7. **Safety/privacy:** No raw RAM, ROMs, savestates, private captures, secrets, local paths/configurations in commits or public CI artifacts. All source/memory assertions must preserve provenance and abstention; do not infer visual contact, actual game frames, world XYZ/velocity, power, or training eligibility from weak evidence. A 100-foot penalty is censored, not a measured carry. No unattended or implicit real-game actions.
8. **PR state:** PR must be non-draft, mergeable, no conflicts, no unresolved actionable review objections, and all required branch-protection checks green. If GitHub requires an approval by rule, comply; do **not** bypass protections. This is a platform constraint, not a project-wide requirement to request another AI's review.
9. **Evidence receipt:** Post a `[INSTANCE] MERGE READY` comment containing exact head SHA, main SHA/branch freshness, affected paths, overlap resolution, test commands/environments/results, compatibility and privacy checks, dependencies and remaining uncertainties. Every checklist item must explicitly say PASS.
10. **Merge and handoff:** Squash-merge by default, supplying `expected_head_sha`. Post merge SHA and `[INSTANCE] HANDOFF` to the canonical issue, identify retired children and why their unique code/tests/evidence survive; preserve branches/history. Never mass-close by title, age, or PR count.

## STOP / escalation criteria

If any check fails, fix it and retest. Escalate to the operator only when the agent cannot objectively resolve conflicting shared requirements, required GitHub permissions/protections, new destructive behavior, private-data publication, or live-shot authorization. **No separate AI veto or signoff** for ordinary, complete work. A reviewer can report a reproducible defect; it must be resolved or the PR stays blocked, but mere absence of an external review is not a blocker except where GitHub rules require it.

## Agent-specific boundaries

- S000: integration and shared coordination.
- S001: Dolphin launch, controller and timing. **No live execution without separate explicit user opt-in.**
- S002: SHA/identity-gated memory and outcome provenance.
- S003: action and predictive modeling.
- S004: optimization/training on eligible data only.
- S005: held-out evaluations and censoring.

An agent may update cross-domain interfaces only with reproducible compatibility and consumer tests, not with unverified assumptions. A conflicting multi-owner design is an objective STOP until contracts are reconciled.

## Example merge receipt

```text
[S002-memory-a] MERGE READY
HEAD=<exact SHA> MAIN=<exact SHA>
Scope/owner: PASS — ...
Overlap/dependencies: PASS — ...
Focused tests: PASS — <command, OS, number>
Full offline tests: PASS — <command, OS, number>
CI/branch protection: PASS — <run URL>
Compatibility/consumers: PASS — ...
Privacy/provenance: PASS — ...
PR non-draft/no unresolved conflict: PASS
Next owner/rollback: ...
```

**Policy change control:** Edits to this file itself must pass this same checklist. Publish a brief change summary in the canonical consolidation PR; no additional discretionary reviewer is inherently necessary.
