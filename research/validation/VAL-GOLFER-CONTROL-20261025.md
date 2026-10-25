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

## Immediate falsification decision

Reject the simple hypothesis that *any change at one of these four words is specific to a swing*. Within human-labelled idle blocks, each changed repeatedly while no explicit swing was dispatched by this control protocol. The **null that these are background-dynamic candidates has not been disproven**. Evidence is consistent with background clocks, animation, counters, state bookkeeping or other update-driven changes, but does not identify which.

Do **not**:
1. Treat `main+0x074` as calibrated swing power or automatically infer its word value is a frame count.
2. Promote 100-ft off-green penalty, score/proximity or a controller-RPC ACK to ball carry or internal power.
3. Train a predictive model on the four changed words without their actual same-shot causal specificity, sample timing and grounded game variable type.
4. Compare `max_non_atomic_frame_span=18` from the 16-child watchlist against the earlier **2-frame** candidate-main-only capture as though the probes had identical size or phase timing. Probe width is a possible confound, not established cause.
5. Upload private RAW-PRIVATE captures to GitHub or ChatGPT. Public aggregate counts only.

## Next test A — S002-GOLFER-NULL-01 (OFFLINE, zero Dolphin)

Use **existing private 20-row source-gated snapshots** with the S002-owned [PR #138](https://github.com/Nate27624/Wii-AI-Golf/pull/138) null-control analyzer. Test whether main `+0x074` u32 word steps in same-stage *idle* relate to actual observed emulator-frame deltas, while keeping stage boundaries and private values out of the public output.

**Preregistered checks**: frame brackets nondecreasing, exact run/scenes stable, no presumed 89-emulator-frame waveform from outgoing samples, repeated idle phase comparisons, classify `within_idle_changed_pairs`, `frame_step_equal_pairs`, and strict `game_power_field_verified=false`. A delta-versus-frame correlation suggests timer-like behavior **only**, not a type proof.

**Known execution blocker to fix before operator runs `--latest`:** currently PR #138 enforces `MAX_SNAPSHOT_FRAMES=12` but the latest public 16-child summary reports maximum 18. The two may or may not refer to the exact same underlying private file; only the operator's local file can establish lineage. S002 should either accept a bounded wider span with an explicit `timing_limited` qualifier and avoid per-frame causal interpretations, or choose a known 2-frame-width main-only capture. No new Dolphin is needed to resolve this. Test both positive and rejected span fixtures. S000 alerted the #138 owner; do not advise users to blindly rerun the old command while the mismatch is unresolved.

**Decision rule**: if `within_idle_changed_pairs>0`, classify `main+0x074` as *not swing-exclusive*. If its u32 step repeatedly equals emulator-frame start gaps, rank it timer-like *hypothesis only*. Otherwise leave as unknown background-dynamic. Any missing/inconsistent provenance blocks interpretability.

## Next test B — four-word common-mode counter test (OFFLINE, after A)

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
- **S001 PR #134 / #140:** dormant Nunchuk/WASD preflight; no forced live actions until workflow and merge checks complete.
- **S003 PR #125:** mark all four as **negative controls for swing-exclusive labeling**. Do not train a power model on them; potential frame counter is an interpretation to test, not a verified fact.
- New reports must use valid source-labelled **sanitized public outputs**, not private values, and clearly distinguish process status, candidate RAM, human labels and verified game measurements.
