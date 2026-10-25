# S000 research decision — golfer candidate controls, 2026-10-25

**Evidence state:** one independent, already-published S002 *sanitized* offline review, not new live acquisition and not a verified swing measurement. This note does not contain absolute Wii RAM pointers, raw bytes, private capture paths, ROMs or controller waveforms.

**Primary public record:** [S002 `20261025T034248Z-7c597d65`](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T034248Z-7c597d65.json), `kind=golf-golfer-control-specificity`, `study_id=S002-GOLFER-CONTROL-SPECIFICITY`. Independently fetched and inspected through connected GitHub on October 24 local / October 25 UTC.

## What the *public record* actually shows

- Exactly **20 observations in one capture**, 12 operator-labelled idle and 8 operator-labelled `aim_only`; **10 within-idle comparison opportunities** and **7 within-aim opportunities**. Human label does not prove objective sensor state or a scene/camera change.
- **16 candidate first-level child regions** monitored, **four** reported changed region-relative words. The public summary does not include actual values, sampling instants for every word, or ground-truth object types.
- Each of four words changed in **10/10 within-idle** and **7/7 within-aim** comparisons (100% in both). Their public source-relative names:
  - `main +0x074`
  - `child_at_main+0x008 / +0x050`
  - `child_at_main+0x020 / +0x038`
  - `child_at_main+0x044 / +0x060`
- `max_non_atomic_frame_span=18`, `timing_limited=true`, `truncated_changed_words=false`, `power_verified=false`, `club_pose_verified=false`. Eighteen emulator frames per broad snapshot is **not** a per-frame swing event trace.
- **Effective experimental independence is ONE session**, not 17 independent trials, four independent gameplay variables, or 16 independent physical golfer objects.

## NEW operator-executed S002-GOLFER-NULL-01 result (2026-10-25 UTC)

**Source:** Operator directly pasted the sanitized output of `py scripts/audit_golfer_null_controls.py --latest` from the isolated PR #138 worktree. The command completed and printed valid schema v1 with no private addresses or bytes. The user tested the branch offline; this is not an independently accessed raw file or a new Dolphin run.

| Stage | Human cue | Samples | Within-stage pairs changing `main+0x074` | U32 increment equals observed frame-start gap |
| --- | --- | ---: | ---: | ---: |
| 0 | idle | 6 | **5/5** | **5/5** |
| 1 | aim_only | 8 | **7/7** | **7/7** |
| 2 | idle | 6 | **5/5** | **5/5** |
| **Total** | one capture session | **20** | **17/17** | **17/17** |

Other fixed, sanitized result fields: `within_idle_changed_pairs=10`,
`within_pointer_only_changed_pairs=7`, `within_stage_total_opportunities=17`,
`max_non_atomic_frame_span=10`, `timing_limited=false` (local >12-frame
rule), `frame_delta_relation_is_exploratory=true`,
`candidate_exclusive_swing_event_indicator_supported=false`,
`game_power_field_verified=false`, `club_pose_verified=false`,
`human_pointer_action_verified_by_sensor=false`,
`independent_sessions_verified=false`, and
`wii_revision_reverified_from_saved_rows=false`.

### Interpretation and exact limits

1. **Confident narrow rejection**: a *change* at `main+0x074` does not require a swing command under these operator-labelled controls, so change-detection alone is not a swing-exclusive event label.
2. **Strong within-session pattern**: the unsigned modular 32-bit increment exactly matches the emulator frame-start gap for 17/17 adjacent within-stage pairs, across idle and aim-only conditions. This is more specific than merely seeing that it changes every time. It is consistent with a 1-unit-per-frame counter or a direct copy/derived proxy of one.
3. **Unidentified semantics**: no value type, owner, writer function, frame hook or actual game-internal clock is source-verified. A per-frame animation counter, render update tick or shared central frame value remains plausible. We cannot infer swing power, ball carry, pose, or even that this word is the canonical emulator frame counter.
4. **Single-session dependence**: 17 pairs share one captured scene and adjacent samples. No independent boot replication, no sensor-proven aim movement, and no statistically independent 17-trial success probability.
5. **Temporal qualification**: 10 is the *maximum non-atomic per-snapshot frame span*, not a 10-frame elapsed time for each adjacent pair. `timing_limited=false` only means the author's provisional 12-frame flag was not crossed; it is not proof of precise per-frame action attribution. U32/frame-start agreement is exploratory.
6. **Cross-report independence unresolved**: previous public `golf-golfer-control-specificity` record used a 16-child watchlist and max span 18, while this `--latest` audit reported max span 10. Do NOT merge the two reports as one matched capture or compare their latency without privately verifying source capture lineage and watchlist size.

**Preregistration update for test B:** use *actual observed frame-start gaps* and each existing private word's modulo-u32 difference, not synthetic sample index or repeated change count. The specific hypothesis is that at least two child-word **delta sequences** coincide with `main+0x074` after accounting for the frame gaps in BOTH idle stages and the aim-only stage. Report only safe counts of equal-delta pairs and a lagged/shifted-control comparison; no raw values, addresses, or per-sample traces in GitHub. A constant 1-step/frame across all phases is compatible with multiple background counters, not proof of aliasing. The deterministic shift-control must be checked against the actual varying frame gaps: if gaps are constant, shifting by one row may not discriminate identical counters. If no discriminating frame variability, the negative control is uninformative; do not claim a clean win.

**Next discriminator:** replicate the phase-counter relationship from an **independently booted** source-verified capture with a smaller watchlist and tightly bounded frame spans, then compare whether the U32 difference tracks emulator frame increments through a *controlled non-swing pause/resume or other safely approved change in elapsed emulator frames*. The proposal is conditional and requires S001/S002-approved read-only session + independent operator consent. No new shot and no memory write is authorized here.

## Immediate falsification decision

Reject the simple hypothesis that *any change at one of these four words is specific to a swing*. Within human-labelled idle blocks, each changed repeatedly while no explicit swing was dispatched by this control protocol. The **null that these are background-dynamic candidates has not been disproven**. Evidence is consistent with background clocks, animation, counters, state bookkeeping or other update-driven changes, but does not identify which.

Do **not**:
1. Treat `main+0x074` as calibrated swing power or automatically infer its word value is a frame count.
2. Promote 100-ft off-green penalty, score/proximity or a controller-RPC ACK to ball carry or internal power.
3. Train a predictive model on the four changed words without their actual same-shot causal specificity, sample timing and grounded game variable type.
4. Compare `max_non_atomic_frame_span=18` from the 16-child watchlist against the earlier **2-frame** candidate-main-only capture as though the probes had identical size or phase timing. Probe width is a possible confound, not established cause.
5. Upload private RAW-PRIVATE captures to GitHub or ChatGPT. Public aggregate counts only.

## Test A — S002-GOLFER-NULL-01 (OFFLINE, EXECUTED by operator)

**Executed by operator:** The S002-owned [PR #138](https://github.com/Nate27624/Wii-AI-Golf/pull/138) analyzer consumed an existing private 20-row capture and produced the sanitized stage/table result reproduced above: **17/17 within-stage increment equalities**, including idle **10/10**. Private rows remain inaccessible here. This satisfies the narrow exploratory frame-step hypothesis inside this **single capture**, but does not identify a clock or a power encoding.

**Preregistered checks**: frame brackets nondecreasing, exact run/scenes stable, no presumed 89-emulator-frame waveform from outgoing samples, repeated idle phase comparisons, classify `within_idle_changed_pairs`, `frame_step_equal_pairs`, and strict `game_power_field_verified=false`. A delta-versus-frame correlation suggests timer-like behavior **only**, not a type proof.

**Resolved implementation compatibility gate, but latest operator result pending:** S002 PR #138 initially required `MAX_SNAPSHOT_FRAMES=12` and therefore rejected the actual wider capture (public 16-child report has maximum 18); the operator confirmed that exact error on the original branch. S002 has since expanded the offline input cap to source PR #129's existing 240-frame contract and added `timing_limited` for spans >12 and `frame_delta_relation_is_exploratory`. This preserves descriptive no-shot comparisons while explicitly disallowing precise per-frame clock conclusions from broad non-atomic reads. **The latest PR #138 head is not yet Windows-tested or run on private capture after this correction**. A fresh targeted/full offline regression and `--latest` are the next operator task; never auto-relaunch Dolphin if local files mismatch.

**Decision reached:** `within_idle_changed_pairs=10` and `frame_step_equal_pairs=17/17`. Classify `main+0x074` as **not swing-exclusive** and as a **frame-linked background timing candidate**, with no verified internal type. The S002 collector obtains `frame_start` from an independent Dolphin RPC `frame.get_count` *before* reading candidate `bytes_hex`; the public analyzer compares the stored count with the private RAM word, rather than constructing one from the other. They still share emulator time and non-atomic sampling, so exact match alone cannot prove ownership or semantics.

## Next test B — common-mode plus cross-boundary counter test (OFFLINE, not yet executed)

**First, finish an already-captured two-pair control (cheapest discriminating check).**
PR #138 deliberately omits the two adjacent pairs where human stage changes
0→1 and 1→2 from swing-event **specificity**. S002 can still separately
test their *arithmetic* delta-versus-observed-frame relationship without
calling them verified input events. Publish `stage_boundary_pair_count=2`,
`stage_boundary_equal_frame_gap_pairs` in 0..2, and
`same_additive_offset_across_all_stages` (boolean) only. Never publish
the additive offset itself. If both also match, the same single-session
frame-linked equation spans all 19 adjacent pairs; if either differs,
report a stage-boundary discontinuity and investigate offset timing rather
than automatically attributing it to the pointer. Validate source identity,
frame monotonicity and the 10-frame bracket caveat before computing any count.

## Part B — four-word common-mode counter test (OFFLINE, after A)

Within the **same existing private capture**, compare the **per-sample change/not-change sequences** and modulo u32 deltas of the three child candidates to `main+0x074`. Preregister before viewing trajectories:

- **H0**: the four words are unrelated asynchronous background state; synchronized change *counts* alone are not proof of shared storage or shared clock.
- **H1**: across all within-stage adjacent pairs, their *delta vectors* are equal or have a stable linear ratio. If this occurs in both idle and pointer-only phases, mark **common-mode background clock/update hypothesis**, not verified power.
- Control: deliberately shift one candidate's frame sequence by one row; an exact same-row relation should weaken under the shift. Compare each candidate against **actual observed frame count gaps**, not sample indices.
- Unit of inference: one capture session; do not compute independent-shot p-values from adjacent rows. Do not publish raw deltas or private addresses; emit only bounded similarity counts and fixed labels.
- Stop: no source-validated owner for candidate children, inconsistent identities or 18-frame non-atomic brackets -> retain descriptive **phase-level** only and explicitly label timing limited.

This study is a research proposal for **S002 ownership**, not implemented here. It should extend the canonical offline reviewer only after #138/#135 ownership and schema reconciliation; do not create another parallel raw-reader.

## Conditional test C — lower-latency gameplay watchlist (READ ONLY)

Only after S002 reviews source ownership and S001's controller preflight PR #134 merges: re-measure p50/p95/max frame spans with a source-gated *minimal* candidate watchlist, repeated separately across two clean boots, no motion or golf shots, and same idle/aim-no-shot controls. Frame-span acceptance target p95 <= 2 frames is **a preregistered resolution goal**, not a measured requirement. Stop on revision/mode error, relocated scene/manager/backlink, overlap/rollback, wrong source pointer, or broad sampling perturbation. Use existing canonical S001 launcher; no new standalone boot mechanism. Explicit operator approval required before any additional live interaction.

**Research priority:** A before B; C only if source/timing checks can plausibly disambiguate game input effects. For next power studies, a **distinct human-visible power level** and frame-joined same-shot RAM/controller measurement are still unobserved prerequisites. No repeated swing sweeps until then.

## Integration boundaries / collaboration

- **S002 PR #129:** owner of bounded live candidate golfer RAM capture and private file format. PR #138: focused `main+0x074` offline falsification. PR #135: generic relative-offset phase review. Avoid duplicate competing readers or unreviewed schemas.
- **S000 PR #126:** strict public publication allowlist; its strengthened PR #132 scene-root shape was just added but latest Windows regression remains pending.
- **S001:** the dormant Nunchuk/WASD preflight correction is now present in latest `main` (commit `953e85a`); still use one canonical Dolphin session and keep read-only studies separate from startup.
- **S003 PR #125:** mark all four as **negative controls for swing-exclusive labeling**. Do not train a power model on them; potential frame counter is an interpretation to test, not a verified fact.
- New reports must use valid source-labelled **sanitized public outputs**, not private values, and clearly distinguish process status, candidate RAM, human labels and verified game measurements.
