# Architecture — one research loop, one public CLI

The project consists of **one source-local CLI orchestrator** and several independently owned modules. The CLI does not duplicate validated game startup, input scheduling, model physics or score extraction.

~~~text
           py scripts/golf.py / (optional) wii-golf
                           |
       +-------------------+--------------------+
       |                   |                    |
      CLI offline       CLI real-game       CLI research
    tests / doctor     play / swing /       studies / evidence /
    synthetic demo     experiment           scenarios / audit
       |                   |                    |
  toy_env/agents      launch_golf.py        research_catalog.py
  only SYNTHETIC            |               local JSONL summaries
                    Emulated Wii Remote 1
                    + existing named state
                           |
                  launch_hitting_green.py
                    + menu_sequence.py
                    A / A+B / A canonical intro
                           |
                    probe_swing.py (one)
                           |
               Felk atomic swing bridge
                           |
                 Human/game observations
                           |
            S002 audited score/units -> S003
                   parameter calibration
                           |
              S004 optimization / S005 heldout
~~~

The implementation is additive: older `scripts/*.py` entrypoints remain valid for advanced diagnostics, but normal operator workflows run through `golf`. Live commands delegate, rather than reimplement, startup. This preserves the user-verified named `green-pre-start` savestate and seven-phase intro request timeline `120/30/315/60/135/45/300`. Nonfirst-shot scenarios need an explicit alternative reset contract. A bridge ACK does not prove game recognition or measured score.

## Module boundaries

| Layer | Owned modules / capabilities | Contract |
| --- | --- | --- |
| User interface | `src/wii_ai_golf/cli.py`, `scripts/golf.py` | Stdlib dispatch, discoverability, safe dry-runs; no emulator logic |
| Real-game integrator S001 | `integration/`, `menu_sequence.py`, canonical launcher scripts | Exactly one Felk session; correct controller mode; trace timing; named reset and outcome provenance |
| Measurement S002 | `audit/`, evaluation agent branches | Raw score and position with version/unit verification; distinguish candidate RAM offsets from validated coordinates |
| Modeling S003 | Modeling agent PR | Parameterized swings and physical response, not inferred solely from RPC ACK |
| Learning S004/S005 | Learning agent PR, policy interfaces | Attempt-budget-matched training and untouched test scenes; synthetic scores labeled |
| Research | `research/queue.jsonl`, `research/ledger.md`, local sibling data | Static hypotheses, chronological evidence, no fabricated attempts |

Provisional `ShotAction(aim,power)` and `DolphinEnvironment` in `protocol.py` / `emulator.py` remain interfaces, not a validated controller-to-golf mapping. The toy physics/demo stays explicitly synthetic.

## Unified evidence contract

Each real trial has controller sample hash/timing, scene/profile/slot, emulator and game revision, source (live RPC vs human versus verified game extraction), failure/reset disposition, human observation and raw measured value/unit when available. `research_catalog.py` only summarizes local evidence, counting a score as verified **only when the record explicitly carries independent verification**. Do not report visual gauge fill as game power or a successful swing as a green landing. The initial recorded complete 89-frame forward trace had human `ball_moved=yes` and `on_green=no`, but no validated score.

Private data lives under sibling `Wii-AI-Golf-Data`. Code, plans, sanitized reports and schemas are in Git. Never commit ROMs, savestates, emulator binaries, credentials or private Dolphin user settings.

## Experiment and acceptance gates

1. **S001:** user-confirmed swing now exists; confirm repeatability on identical full fresh boots.
2. **S002:** verify actual golf outcomes and scoring units with independently checked game evidence; do not count speculative RAM fields.
3. **S003:** controlled one-factor release/speed/distance/aim sweeps with fixed starting scene and actual outcome measurement.
4. **S004:** compare random/search/model candidates under identical total real-game shot budgets, include unsuccessful attempts.
5. **S005:** freeze model and evaluate across genuinely held-out pin/tee/shot configurations.

The longer-term 100 unattended and independently scored attempts gate remains unachieved. See [CLI guide](cli.md), [research program](../research/README.md), and [AGENTS.md](../AGENTS.md).
