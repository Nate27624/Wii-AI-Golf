# Canonical implementation audit and deduplication backlog

SPOCOC = **Single Point of Control Over Change**. The goal is not to merge all agent modules together, but to remove competing production paths. This is an evidence-based audit of repository structure and open PR overlap; not a claim that all paths have been exhaustively code-reviewed.

## Observed duplication risks and actions

| Risk | Existing overlapping paths | Refactoring action |
| --- | --- | --- |
| Dolphin startup | `launch_golf.py`, `launch_hitting_green.py`, `run_golf_experiment.py`, agent scripts that also perform bootstrap | Treat `run_golf_experiment.py` as the standard orchestration wrapper and call the canonical launch/menu helpers. Domain scripts become action-only; no copy/pasted A/A+B/A timing |
| Swing sequences | `probe_swing.build_probe`, S002's collector, S003 proposed `modeling.swing` | Separate **production execution trace** (S001) from **hypothetical model traces** (S003). S002 references trace ID/hash and calls S001; never silently select a different trace |
| RAM outcome/capture | S002 legacy scripts and multiple focused/minimap probe implementations in PR #14/#62 | S002 establishes a single provenance schema and read-only capture service. Feature-specific analyzers consume those records rather than reimplementing bootstrap or raw capture |
| Experiment interface | `scripts/golf.py`, `wii_ai_golf.cli`, `lab.core`, historical `lab.gui` | `scripts/golf.sh` forwards to `scripts/golf.py`; `lab.core` runs typed experiments. GUI is retired; do not add another operator-facing launcher |
| Collaboration metadata | `research/ledger.md`, `research/queue.jsonl`, `research/claims/*`, GitHub PRs | GitHub issues/PRs are ownership and handoff source of truth. Ledger is evidence summary; queue is proposals, not a second live scheduler |

## Refactor sequence

1. Preserve safety/provenance and tests; never remove historical results.
2. For each duplicated path, find callers, scripts and tests before selecting a canonical function.
3. Add adapter/compatibility tests exercising the same input/output contract.
4. Replace duplicate implementations with calls to the canonical module; keep thin compatibility wrappers when users/agents already rely on their names.
5. Only delete wrappers when all callers and documentation migrate.
6. Verify no live commands skip fresh-state and human-authorization gates; no RAW-PRIVATE output is uploaded.

## Merge gates

PR #14 must provide the minimal reusable S002 capture core without a second launcher. PR #62 must be rewritten as CLI-only typed experiments consuming that core; old GUI-oriented code must not be merged. PR #17 can remain offline S003 design but must not establish a competing live waveform. Each PR must state canonical module ownership and downstream contract compatibility.

This file is an integration backlog. It does **not** assert runtime deduplication has already been performed.
