# Cross-agent cooperation contract (SPOCOC coordination)

The operator requests substantially stronger cooperation across S001–S005. Treat "SPOCOC" as the operator's label for this collaboration principle; do not assume a specific acronym expansion.

## One shared delivery path

- Exactly one canonical `main` branch, one Python package, one reviewed `research/experiments.json`, and one script-facing entrypoint `bash scripts/golf.sh` / `py scripts/golf.py`.
- GitHub issue/PR threads are the persistent communication channel. Chats are not shared worker state. Each agent must read this file, `AGENTS.md`, `research/coordination.md`, and current blocking issue/PR comments before starting.
- Coordinator S000 handles cross-agent API decisions, merge ordering, conflicts, and escalation to the operator. Domain agents keep authority over domain implementation and evidence quality.

## Required handoff in every PR

Include these fields in the PR description or a top-level comment:

1. **Owner / issue / study ID** and hypothesis.
2. **Upstream dependencies:** concrete PRs, branches, Python modules, data schemas, controller prerequisites.
3. **Downstream consumers:** which agents need this change, and the *exact* import/CLI/JSON contract they can rely on.
4. **Changed paths / collision risk:** identify shared files and ask for a handoff before editing them.
5. **Validation evidence:** exact test commands and results, emulator vs synthetic vs human-labeled evidence, and missing checks.
6. **Artifact privacy classification:** safe to commit vs sanitized publishable vs RAW-PRIVATE. Never upload raw RAM, game image, savestate, credentials or local config.
7. **Merge gate / next owner:** what must be true for integration, who should take the next action, and what question (if any) is blocked.

## Explicit coordination cycle

1. At task start, identify upstream and downstream peers in the GitHub issue and publish intended interface and touched files.
2. Before writing cross-domain code, ask the upstream owner for an exact interface or use the existing stable one. Do not copy sibling code into another checkout.
3. When a dependency changes, post an interface-change notice tagging affected PRs with old/new fields, migration path and test effect. Consumers acknowledge before integration.
4. Hand off a PR with a minimal executable/mock example and test; downstream agent validates on current `main`, not an older personal branch.
5. Coordinator merges dependencies before consumers, resolves divergent base branches without overwriting another agent's code, and removes superseded PRs after preserving functionality.
6. Every merged result updates the issue/PR with commit SHA and remaining validation, and the next owner proceeds from `main`.

## Current dependency chain

- S001 owns Wii Remote and canonical Dolphin startup.
- S002 consumes S001's safe startup contract and produces separately classified observations; S002 does not redefine swing control or claim verified score from RPC acknowledgement.
- S003 consumes S001 motion trace schema and S002 outcome provenance, and supplies parameterized candidate profiles. No broad live calibration until contact/reset and measurement are reliable.
- S004 consumes S003 parameter mapping and S002 scored outcomes; until then Bayesian tests remain synthetic.
- S005 consumes frozen S002 evaluation protocol and S003/S004 candidate policies; train/test isolation must remain explicit.
- S000 accepts typed CLI adapters and tests only after the corresponding domain code is available in the one codebase. The desktop GUI is retired.

## Avoiding duplicate work

If two agents independently solve the same problem, designate one canonical implementation and move the other to compatibility tests or archive documentation. Never retain two equally authoritative Dolphin launchers, swing waveforms, score schemas, or CLI workflows.

## Escalation

Agents resolve ordinary engineering details in linked GitHub threads. Ask the operator only for unresolved product intent, materially different experiment designs, privacy/security decisions or destructive actions. Until resolved, choose the non-destructive fail-closed path and continue independent offline work.

This protocol coordinates work when agents run; it does not claim the chat sessions are continuously active or directly messaging one another.
