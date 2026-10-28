# Multi-agent coordination — read before starting work

## ACTIVE cross-context onboarding and CURRENT baseline (2026-10-27)

**Every NEW or resumed S000–S005 context MUST read rules before answering or changing code:** README.md active top, AGENTS.md active top, docs/agent-session-protocol.md, docs/operator-powershell-contract.md, docs/repository-map.md, this file, actual source/tests and latest owner issue/PR/HANDOFF/FINDING. Confirm which were actually read; a GitHub issue or chat summary is not proof of current source state.

**Before each substantive reply re-establish a short CURRENT baseline:** latest pasted PowerShell result; actual branch/commit and whether current PR is draft/merged; owner claim and other overlapping PRs; verified vs candidate/human/synthetic evidence; P0 blocker; one next action. Refresh relevant changing GitHub state, not every historical file. If unavailable say NOT CHECKED. Never assume that separate agent chats share memory, live Dolphin state, consent, source checkout or worktree changes.

**HANDOFF before leaving:** post dated owning issue/PR comment with head SHA, changed paths, focused/full tests and exact environment, known-good frozen A45/89-sample/bridge profile, explicit success/failure evidence class, sanitized UPLOADED link or NOT UPLOADED blocker, pending safety/merge gates and next agent. Significant positive and negative results also get FINDING comments and reviewed research/ledger.md entries. Preserve private RAM and local user configuration. Follow [mandatory agent session protocol](../docs/agent-session-protocol.md).


This file is the map; **GitHub issue comments are the live claim and handoff log**. A JSON file in `research/claims/` is a durable index, not an atomic lock. Work is not automatically scheduled; other agents must be started in their own sessions.

## Claim protocol

1. Read `AGENTS.md`, this document, active [issues](https://github.com/Nate27624/Wii-AI-Golf/issues), [pull requests](https://github.com/Nate27624/Wii-AI-Golf/pulls), `research/claims/` and `research/ledger.md`.
2. If an issue is unclaimed and paths do not overlap, comment `CLAIM` on its issue **before** writing code. Record unique worker ID, work branch, paths, anticipated changes and validation limits; then create/edit `research/claims/<worker-id>.json` in your own PR. Issue comments establish chronological precedence.
3. If any claim conflicts, **do not change the overlapping paths**. Negotiate on the issue and agree on one owner or a narrower task. Never assume lack of recent chat activity means ownership is abandoned.
4. Keep experiments on `agent/<role>/<slug>` branches; avoid feature commits directly on `main`. Create PRs and link issue/claim. Use merge conflict checks; avoid force pushes to shared branches.
5. For handoffs, append `HANDOFF` to the issue and add a dated `research/<worker-id>/README.md`. Explain state, tests, measured data, source, reproducibility, next tasks and blockers; explicitly release paths when done.
6. Make a new claim for major additional scope. Close or mark claims `handoff` when ownership is relinquished, **not when a background worker is expected to keep running**.

## Current issue ownership table (snapshot, inspect live issues)

| Worker | Issue | Workstream | Scope | Status |
| --- | --- | --- | --- | --- |
| Worker 1 | [#2](https://github.com/Nate27624/Wii-AI-Golf/issues/2) | Dolphin integration probe and trace infrastructure | `src/wii_ai_golf/integration/`, `tests/test_integration_*`, `scripts/probe_dolphin_bridge.py`, `docs/integrator-research.md`, `research/worker1/` | Scaffold built; **real game not verified** |
| Available | [#3](https://github.com/Nate27624/Wii-AI-Golf/issues/3) | Score extraction + evaluation | Evaluation paths (coordinate interface) | Unclaimed at snapshot |
| Available | [#4](https://github.com/Nate27624/Wii-AI-Golf/issues/4) | Calibration / model identification | Models and own studies | Unclaimed at snapshot |
| Available | [#5](https://github.com/Nate27624/Wii-AI-Golf/issues/5) | Baseline search | Agents and own studies | Unclaimed at snapshot |
| Available | [#6](https://github.com/Nate27624/Wii-AI-Golf/issues/6) | Generalization policies | Separate advanced ML modules | Unclaimed at snapshot |

## Integration contracts for other agents

- Worker 1 owns the raw bridge transport; **it does not own** score parsing or policy algorithms.
- Current `ShotAction(aim, power)` is a placeholder. Do not map its values to acceleration without calibration and coordination with modeling.
- Frame counts in Worker 1's trace reports are request/acknowledgement observations, **not guaranteed button/accelerometer application timestamps**.
- Real scoring should enter via `ShotResult` only after units and extraction are independently verified by evaluation.
- To request protocol changes, comment on [Issue #2](https://github.com/Nate27624/Wii-AI-Golf/issues/2) or open a dedicated interface issue; do not silently alter integrations across roles.

## Ledger rules

Each worker writes research outcomes in its own folder/PR and adds a concise dated entry to `research/ledger.md` only during integration. If others edited the shared ledger, refresh before patching and **append without discarding their entries**. Never fabricate experiments: mark synthetic, mock bridge, live emulator, or game verified separately.
