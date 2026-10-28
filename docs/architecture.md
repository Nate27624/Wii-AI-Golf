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

## Planned training architecture — Dolphin ground truth + learned surrogate

**Decision (2026-10-27; proposed, not implemented):** Prefer a **hybrid model-based workflow** over either training exclusively inside Dolphin or hand-coding a separate imitation of Wii Sports physics. **Dolphin is the authoritative game environment** for real shot collection, independent outcome verification, and final evaluation. Train prediction models and search for candidate swings **outside the emulator**, preferably on the operator's local GPU, then return selected candidates to Dolphin to verify what actually happens. A learned surrogate is an approximation, not a second source of truth.

Conceptual architecture (names below are *future adapter proposals*, not importable implementations):

~~~text
Canonical S001 Dolphin startup/control + S002 verified shot result
          |  same-shot ID, scene, actual trace, measurement + provenance
          v
   Private, versioned real-shot dataset (no raw RAM in Git)
          |
          v
  S003 learned outcome/surrogate model + uncertainty
          |  predict contact, final location/distance, failure probability
          v
    S004 offline candidate-swing optimizer
          |  select promising AND informative swings
          v
   Real Dolphin validation -> add audited examples -> retrain
          |
          v
     S005 frozen held-out real-game evaluation
~~~

### Execution boundaries and staging

1. **First, earn reliable labels.** S001 must reproduce contact/reset and link frame-anchored input traces to the *same* shot as S002's pre/post state and audited result. Require known scene and target geometry (or validated target distance/bearing), actual controller action, contact/failure disposition, and independently verified settled ball location **or** non-censored final distance with units. Candidate RAM offsets, RPC ACK, human gauge fill and displayed off-green penalty are not verified physical labels. See [joint swing-memory evidence gates](https://github.com/Nate27624/Wii-AI-Golf/issues/121) and [research program](../research/README.md).
2. **Baseline on real Dolphin data.** Begin with a small interpretable action-to-outcome regressor or ensemble (and uncertainty), not full per-frame ball physics. Keep the existing `toy_env` explicitly synthetic. Start with repeated, one-factor traces and a preregistered budget; include misses, invalid results, confidence and censored outcomes rather than silently dropping them.
3. **Explore offline, verify online.** S004 searches many hypothetical aim/swing settings against the learned model without launching Dolphin per prediction. Only promising or high-uncertainty candidates are tested in explicitly authorized real emulator trials. Never let the model score its own training success: **verified Dolphin outcomes are the reward/evaluation authority**.
4. **Retrain and guard against model exploitation.** Measure held-out prediction error and calibration, flag out-of-distribution swings, compare predicted vs actual contact/landing/remaining distance, and feed back audited failures. A surrogate can be confidently wrong; the optimizer must not exploit its errors unchecked.
5. **Prove transfer.** Compare direct Dolphin search, random/simple heuristics and surrogate-assisted search using matched **total real-emulator shot budgets**, including data collection and failures. S005 freezes policy and tests on untouched shot/pin/scene groups. Report wall-clock/runtime costs separately from prediction throughput.

**Implementation boundary:** Reuse existing canonical CLI, one-shot guarded Dolphin execution and S002 outcome provenance rather than adding a second emulator controller or altering a shared schema without owner review. Potential `DolphinGolfEnv` / `LearnedGolfEnv` names are descriptive architecture sketches, **not present APIs**. The existing normalized `ShotAction(aim,power)` remains a placeholder until S003 maps it to actual Wii Remote controls. Do not start unattended live training or call this pipeline functional before the measurement and approval gates pass.

## Experiment and acceptance gates

1. **S001:** user-confirmed swing now exists; confirm repeatability on identical full fresh boots.
2. **S002:** verify actual golf outcomes and scoring units with independently checked game evidence; do not count speculative RAM fields.
3. **S003:** controlled one-factor release/speed/distance/aim sweeps with fixed starting scene and actual outcome measurement.
4. **S004:** compare random/search/model candidates under identical total real-game shot budgets, include unsuccessful attempts.
5. **S005:** freeze model and evaluate across genuinely held-out pin/tee/shot configurations.

The longer-term 100 unattended and independently scored attempts gate remains unachieved. See [CLI guide](cli.md), [research program](../research/README.md), and [AGENTS.md](../AGENTS.md).
