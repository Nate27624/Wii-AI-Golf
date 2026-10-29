# P0 seven numbered human-phase snapshots: source-gated offline review

**Scope.** User's real local Windows operator performed 7/7 *paired* 24MiB MEM1 plus 64MiB MEM2 source-to-archive SHA verification. Native originals `tools/FelkDolphin-Clean/User/Dump/1.1.raw ... 7.2.raw` unchanged. Archive `Wii-AI-Golf-Data/captures/p0-new-cohort-*-PRIVATE` with manifest kind `p0-private-numbered-capture-inventory`. These historical capture descriptions are human-operator notes, not machine-joined numeric phase labels:

1. Driver midair, power meter rising, ~27 visible (not RAM).
2. Same driver shot landed/stationary before transition.
3. Putter backswing, A not pressed.
4. Driver backswing, A pressed.
5. Wedge airborne near apex, ~31 on visual meter (not RAM).
6. Same wedge shot slightly later while descending (operator inference).
7. Same wedge strike flag, 'Nice on', ball stopped around 15.2ft (human visual estimate).

**Tool.** `scripts/audit_p0_seven_numbered_source_pairs_private.py --archive <private preserved folder>` reuses #223 full-source Rev1 scene/source selected golf chain and original player record / ball+0x30 plus three caches. It FAILS CLOSED if any bank integrity, expected seven pair membership, scene chain or pin selfref is unavailable. No generic memory scan. It compares only five meaningful edges (1→2, 3→4, 5→6, 6→7, 5→7) guarded for same selected player and hole, reports u32 component-change counts (0..3), selected player record +0x34/+0x38/+0x74 boolean changes, ball-cache equality and pin/start pointer comparison flags, Config selector+0xBC/+0xC0/+0xC4 equality flags. User's original archive manifest has hashes and raw lengths; only sanitized non-numeric positions/paths and no hash text printed.

**Precautions.** A pass is source-chain plausibility and inter-snapshot change only, NOT verified physics, guest same-frame atomicity, independent interval timing, axes, velocity, shot power, actual impact frame or approved training. In particular the 7 numbered pairs cannot be treated as a contiguous 7-frame sequence or as a single shot; they represent different club and shot phases. No new Dolphin, guest memory writes, capture or raw RAM upload. S001 live watch / S002 source ownership / S000 registry remain separate. Pilot only after offline tests and owner review; user runs PowerShell pinned worktree from canonical source checkout. Original bank archive has independently copied hashes, not GitHub observable file bytes.

**Known operational failure mode.** `_get` requires the original selected pin object's +0x4C selfref and Rev1 source-selected player/ball chain to be valid in *every* phase. If the wedge contact / transition phase fails, report ABSTAIN, not a fabricated zero or a direction of movement. Request next narrower owner-gated per-phase audit if needed.

**Status at creation.** Synthetic tests only. No real seven-pair bytes available to remote agents. Dedicated CI Windows/Ubuntu and operator local read must be recorded separately. Do not claim source-vector velocity without two time-indexed physical positions.

## Real operator read-only Windows result — 2026-10-28

Operator ran exact code/test commit `9434b45f2748a526811822d90ccd86694ccf6c55` from a detached worktree against the 7-pair ignored private SHA-verified archive, without Dolphin. All 16/16 local synthetic tests passed and the real seven-pair source-selected audit ended `P0_SEVEN_CAPTURE_SOURCE_AUDIT=PASS`. The seven source-selected actor indices and holes were **slot 0, hole 1** (game-native integer index; do not infer physical hole name). Every matched pair retained source-selected slot+hole and same pin/start/FieldManager pointers.

| Human-associated pair | Selected ball +0x30 changed 32-bit components | START | PIN | Cache +0xCC |
| --- | ---: | ---: | ---: | ---: |
| Driver 1→2 airborne→stationary | **3/3** | 0/3 | 0/3 | 3/3 |
| 3→4 putter backswing A-off vs driver backswing A-on **confounded different club** | **0/3** | 0/3 | 0/3 | 0/3 |
| Wedge 5→6 near apex→descending | **3/3** | 0/3 | 0/3 | 0/3 |
| Wedge 6→7 descending→flag contact/on-green UI | **3/3** | 0/3 | 0/3 | 0/3 |
| Wedge 5→7 | **3/3** | 0/3 | 0/3 | 0/3 |

Within-snapshot selected current ball equals tee 3/3 on samples #1,#3,#4 and 0/3 on #2,#5,#6,#7. Current ball equals cache +0xCC 3/3 in #1,#2,#3,#4,#7, 0/3 in #5,#6. All five pairwise `pin_object_pointer_identical`, `start_object_pointer_identical`, `field_manager_pointer_identical` and `config_BC_identical` booleans were TRUE. **Windows tables truncated Config C0/C4, other cache columns and player-record +0x34/+0x38/+0x74 flags; no scientific claims about those unprinted values from this transcript.** Original JSON was not uploaded, and source archive remains private.

**Independent S002 cross-check**: [PR #230 operator real W5→W6→W7](https://github.com/Nate27624/Wii-AI-Golf/pull/230#issuecomment-6462446159) independently confirms 3/3 *selected-only* changing ball+0x30; three inactive slots unchanged (0/3 each), stable tee/pin and Config BC/C0, and three candidate cache triplets unchanged 0/3 at every wedge pair. It also found selected ball+0x30 equals **unchanged** cache+0xCC at human flag/on-green W7, not at W5/W6; this supports a possible cached endpoint but **does not prove prediction/landing-target semantics**. Direction of three candidate components across both wedge intervals was +/−/− by #230; no axis interpretation, numeric coordinate, time intervals, velocity or physical trajectory magnitude verified.

**Scientific disposition:** A strong, repeatable, stable-geometry and player-slot-specific **source-selected ball-motion correlate** has now been observed in the human-labeled wedge sequence and separately D1→D2 driver pair. This is **not yet independently verified rendered world XYZ, kinetic velocity, measured swing power, impact time or green outcome**, because source+screen association, guest-frame/time provenance and physical units remain open. Keep all training/automatic publication flags FALSE. Do not merge duplicate source analyzers: #230 owns primary trajectory/4 inactive controls; this PR owns exact preserved private manifest revalidation, record +0x34/+0x38/+0x74 and Config+0xC4 supplementary candidate checks. S000 #205 registry, S001 #215 watcher, S003 #125 model gate informed by GitHub issue comments 6462455139 .. 6462460449. No new shot or full RAM export needed for this review.

## Actual Windows untruncated three-field and Config readout (2026-10-28)

The human operator reran canonical #231 exact reviewed source-gated seven-pair private archive auditor in its existing detached worktree, parsing **complete sanitized JSON** instead of PowerShell's truncated `Format-Table`. Final `P0_RECORD_PHASE_FLAGS_COMPLETE`; original native RAM not uploaded, Dolphin not started, training and physical fields FALSE. The full field-change matrix is:

| Phase transition (human annotations) | selected ball +0x30 changed words | record +0x34 | record +0x38 | record +0x74 | Config BC/C0/C4 | source tee/pin |
| --- | ---: | --- | --- | --- | --- | --- |
| D1→D2, driver airborne→settled | 3/3 | **changed** | unchanged | unchanged | all unchanged | both 0/3 |
| P3→D4, putter A-off vs driver A-on backswing, **DIFFERENT CLUB/POSE** | 0/3 | unchanged | unchanged | **changed** | all unchanged | both 0/3 |
| W5→W6, wedge rising→descending | 3/3 | unchanged | unchanged | unchanged | all unchanged | both 0/3 |
| W6→W7, wedge descending→flag-result | 3/3 | unchanged | unchanged | unchanged | all unchanged | both 0/3 |
| W5→W7, wedge bracket | 3/3 | unchanged | unchanged | unchanged | all unchanged | both 0/3 |

**Interpretation:** `record+0x34` is a **driver shot-phase association only** in these comparisons; `record+0x74` differentiates two pre-swing snapshots but shot club, pose and A-held status all vary together, so it is **not a causal A flag**; `record+0x38` did not change on any analyzed edge (it may differ across *uncompared* shots or past separate boots). The dynamic wedge current ball changes twice while all three record flags are stationary, so NONE of these record words is an all-shot movement/XYZ/velocity proxy. This specifically resolves the prior #227 B0→human airborne 21-word/aim-only 18-word overlap / three flight-exclusive clue: flight-exclusive relative to that finite B0–B3 aim cohort does **not** imply physically dynamic shot data. All seven selected slot/hole and tee/pin/config controls were source stable on the checked edges. Source meaning of words remains untyped; no physics XYZ, velocity, launch, impact, score or training.

This result was handed to S002 #219 and #227, S000 #205, S003 #125 and coordination #121 (comments beginning 6462626008). **Next qualified source step** (lower priority than CC +0xCC writer conditional branch): typed receiver/source reads/writes of selected record+0x34,+0x38,+0x74. Do not repeat existing per-edge RAM field reader or compare 3→4 causally as an A-only experiment.


## P0 follow-up: source-selected ball `+0x34` single-component hypothesis (October 28)

**Hypothesis, not interpretation:** the **middle big-endian float32** at the source-selected player's active ball object `+0x34` may vary with visible ball height. This is the second float of the source-validated `ball+0x30/+0x34/+0x38` vector; it is NOT the selected **player record** `+0x34` field, a different address. Do not label it world Y, vertical height, or velocity until independently linked to rendered ball/guest physics.

**Implemented in this existing seven-source audit**, preserving the original 14-bank SHA manifest and read-only source-gated scene/mode/player/ball chain. The sanitizer adds `ball_middle_component_hypothesis` with three *only* same-human-wedge-shot edges (5→6, 6→7, 5→7), and categorical float32-numeric `increasing/decreasing/unchanged` for: source-selected ball `+0x34`, selected ball cache `+0xD0` (middle of `+0xCC`), PIN middle and START middle. It requires unchanged source-selected ball object, PIN, START, FieldManager pointers, selected slot/hole and Config BC/C0/C4; pin/start entire triples must stay bitwise equal. Any nonfinite word, malformed sample, shifted identity, or changed geometry **ABSTAINS**. Signed-zero bit flips are considered numerically unchanged, not flight.

The main #231 reader cannot independently read the #240 source-global singleton, so output explicitly says `source_global_control_measured_in_this_reader=false` and requests an **independent S002 #240 cross-check**. Existing #230 evidence reported component directions `+/−/−` across both wedge intervals, already consistent with the *middle component decreasing*; this is a source correlation, not machine-confirmed ascent, speed, or physical axis. W5/W6/W7 descriptions are human filename-associated hypotheses, not verified frame-time evidence, and driver D1 airborne==START is a counterexample to treating selected ball as the renderer.

**Operator validation once CI is green:** use existing locally preserved `p0-new-cohort-*-PRIVATE` and the pinned reviewed #231 commit, run the existing `audit_p0_seven_numbered_source_pairs_private.py --archive <archive>` read-only. View **only** `ball_middle_component_hypothesis` from the sanitized JSON. No RAM values, pointers, hashes, file paths, or exact source address values need sharing. No new Dolphin process, memory dump, or shot. If original archive unavailable, report ABSTAIN rather than synthesizing.

**Promotion criteria:** selected middle numerically changes on relevant wedge intervals while stationary PIN/START/cache distinguish it; independent source-global middle measurement and source/renderer/guest-physics-frame linkage still REQUIRED. If absent, no height/XYZ/velocity/power/score/training claim, even when all synthetic tests pass. Original SHA and game provenance are necessary but not proof of capture-phase chronology.
