# Evidence-first falsification portfolio (S000; 2026-10-24)

**Status:** ten preregistered *proposals* in `research/queue.jsonl`; **not** an unattended job queue, execution approval, or evidence of passing a test. This plan narrows the existing S001–S005 goals. All remaining real-game shots require distinct explicit operator consent, canonical startup and independently reviewed S001/S002 timing interfaces.

## Fresh evidence already checked on the public GitHub results branch

| Independent published source | Measurement actually supported | What it **does not** show |
| --- | --- | --- |
| [24-run S002 memory cohort](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/cohort-20261025T025308Z-fbda2d0e.json) | 24 valid independent captures; 84 distinct changed relative words; 16 change in **all** captures, each in minimap-effect regions | Not swing power/club/ball XYZ; 24 captures do not imply 24 independent golfers or shot conditions |
| [Broad legacy memory phase audit](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/offline-20261025T024447Z-a37ee401.json) | 8 pre/post/settled samples, 21 changed words, 22-frame maximum **and mean** read span | Not an impact-aligned real-time swing trace; observed phase changes not proof of golf physics |
| [Focused idle/aim/idle negative control](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T030124Z-9dab7f37.json) | 28 samples (16 idle, 12 aim); human labels idle unchanged and aim camera_moved; **0 changed words** in that focused region, 9-frame maximum and mean read span | Not evidence that no swing-related state exists elsewhere; not a controlled matched timing experiment comparing broad vs focused |
| [Published offline test](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T024510Z-fe87c132b7.json) | Test runner passed, exit code 0; Git-based publication works without a newly created personal token | Not a shot, score, verified power or proof every future S002 schema is safe |

This is *source-derived observation*, not a new local experiment. The queue below specifies **future** discriminating tests.

## Rank by expected information gain / human cost

| Study ID | Study and decisive question | Owner | Operator shot budget | Dependency |
| --- | --- | --- | ---: | --- |
| `VAL-PUB-01` | **Privacy canary**: are only explicitly reviewed record kinds accepted before any Git write? | S000 | 0 | PR #126, S002 schema |
| `VAL-PENALTY-02` | **Label semantics**: does any off-green 100-ft *penalty* become physical ball carry or power? | S003 | 0 | PRs #118/#119 |
| `VAL-DRIFT-03` | **Null offsets**: which 24-run recurring words are only minimap, UI or phase-transition effects? | S002 | 0 | PRs #109/#120/#116 |
| `VAL-SOURCE-04` | **Pointer provenance**: can we document scene → main ownership without inventing a scene address? | S002 | 0 | PR #122 |
| `VAL-SCENE-05` | **Scene and instance control**: same verified golfer region across two clean boots? | S002 | 0; 2 read-only sessions | source+privacy |
| `VAL-LATENCY-06` | **Sampling resolution**: do actual bounded reads support per-frame claims? | S001/S002 | 0; 2 read-only sessions | frame provenance |
| `VAL-CONTROL-07` | **No-hit specificity**: distinguish idle, camera-only and stationary A-hold before searching stroke fields | S001/S002 | 0; 6 read-only sessions | stable object + timing |
| `VAL-JOIN-08` | **Paired clocks**: reciprocal same-shot ID, same scene and observed start/completion frame (not +89 assumption) | S001/S002/S003 | up to 2 | valid controls |
| `VAL-PERTURB-09` | **Observer effect**: does probing alter contact/timing/power of fixed control trace? | S001/S002 | up to 4 | valid same-shot join |
| `VAL-POWER-10` | **Power dose response**: can one approved axis create three independently *observed*, replicated visual-meter levels? | S003/S005 | up to 6 | stable no-perturb capture |

Budgets are **ceilings across separately approved invocations**, not queued shots to execute automatically. There is deliberately **no** 10-shot speed sweep or unconstrained GPU training job here.

## Validity threats and acceptance criteria

**1. Wrong target.** `100.0 ft` off green is a penalty display, **not physical distance** and not a right-censor bound on ball carry. Even on-green distance is *proximity*, not carried distance. Reject any regression dataset using these as numeric carry labels. The power gauge (~75%) is human-visual unless game-internal validation is independently established.

**2. Timing aliasing.** Existing 9-frame and 22-frame reads are non-atomic, so fast swing state can be skipped. `VAL-LATENCY-06` preregisters a *provisional design acceptance target* of p95 ≤2 emulator frames for a proposed per-frame transient trace. **This is a chosen stop threshold, not a measured Wii sampling requirement.** Record p50/p95/max, read size, missed/negative frame jumps and scope; if the target fails, report only slower phase comparisons, use a smaller watchlist or propose an S001-reviewed frame hook.

**3. Confounding by scene and rendering.** Score, mode, minimap, UI and moving-camera fields are negative controls, even if they change across **all** 24 captures. `VAL-SOURCE-04` must distinguish `RPGolScene +0x9C` *member offset* from a resolved live scene base; failure to establish ownership blocks claims about active golfer memory. Wrong revision/mode/scene must fail closed.

**4. Pseudoreplication and leakage.** Treat an independent clean boot/run as the unit of evidence, **not** RAM words, frames, derived feature windows, a repeated hash, or a copied human label. Join no records by timestamp alone; require reciprocal shot identity, scene/boot, bridge SHA, waveform SHA, observed A lead, frame-start and **bridge-observed completion frame**, plus actual RAM bracket overlap. An outgoing 89-sample waveform is not 89 guaranteed emulator frames. S003 PRs #123/#125 should converge on one canonical join contract.

**5. Sampling interference.** Capturing RAM may delay input. `VAL-PERTURB-09` is **two pairs of separately consented control strokes**, descriptive pilot only; it does **not** statistically prove equivalence or establish safety if outcome appears unchanged. Stop on timing disruption/contact regression.

**6. Unidentifiable power.** A change in programmed speed is not evidence of a change in in-game power; existing human estimates clustered ~75%. `VAL-POWER-10` requires 3 discernibly different human meter levels separated by at least 10 percentage points, independently observed across two fresh boots per condition. That 10-point gap is a **pilot resolution target**, not a claim of the display's accuracy. Six shots are for feasibility, not final model training. If no meter range, stop and inspect the bridge/input mapping.

**7. Overfitting.** No predictor is accepted from a single observed shot. Freeze source-derived candidate inclusion/exclusion rules and withhold independent boots before fitting; no repeated frames from one shot split across training and test. S004/S005 model evaluation remains blocked until response levels, negative controls and meaningful grounded targets are available.

## Start here, without a new live swing

1. **S000:** run new planning/contract tests and publish only after review. `VAL-PUB-01` needs both `test`/ `v1` legacy shapes and S002's `golf-memory-phase-differential` and `golf-memory-cohort-relative-words` public schemas. A working legacy test upload is not proof that all future kinds are accepted.
2. **S002:** finish `VAL-DRIFT-03` from the 24 existing captures; explicitly count controls for the 16 universal *rendering* offsets. Validate source-only RPGolScene chain in `VAL-SOURCE-04`; do not dereference an unresolved live pointer.
3. **S001/S002:** design `VAL-LATENCY-06` read-only frame-span measurement; preregister scope/watchlist and error exits before using it with an already running approved session.
4. **S003:** run `VAL-PENALTY-02` with published human labels and synthetic failure canaries; no power fit. Choose **one** shared linkage contract across PRs #123/#125.
5. **S000:** only after owner approvals and offline tests, surface `VAL-SCENE-05` and `VAL-CONTROL-07` as separately consented read-only checks in the *existing* CLI. Do not build another runner.

## Single canonical CLI view

```powershell
py scripts/golf.py research studies
py scripts/golf.py research validation
py scripts/golf.py research validation --study-id VAL-LATENCY-06
py scripts/golf.py research validation --json
```

The new `validation` action is **read-only** and reports the machine-checked hypotheses, controls, budgets, dependencies, falsification and stop rules. It does not claim any study has run.

New offline tests: `py -m unittest discover -s tests -p "test_research_validation.py" -v`; then full tests. No Dolphin needed. Validation is a static contract check, **not** empirical validation of the golf hypotheses.
