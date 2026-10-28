# S002 P0 — seven-phase player writer inputs vs source-selected moving ball and cache

**Scope:** Source-selected offline relationships across existing seven private operator snapshots. This study is deliberately stacked on [S002 #230](https://github.com/Nate27624/Wii-AI-Golf/pull/230) and **reuses its selected-ball, pin, hole, player and raw-bank source gates**. It does not scan unqualified memory, patch Wii Sports, start Dolphin, perform a new swing, expose raw coordinates or overlap #219 PPC direct callsite audit / #183 cache-update disassembly.

## What executable code already proves

- [Source trace #162](https://github.com/Nate27624/Wii-AI-Golf/pull/162) at `RPGolPlayer.cpp` `0x802A0388..0x802A03C8` loads player-record BE-f32 at `+0x60..0x68`, stores a mirrored triple at record `+0x54..+0x5C`, follows record `+0x88` to the ball object and `ball+0x4C` to the live translation pointer, then stores three floats into the translation. Enclosing public symbol is `fn_802A0320`; static callers traced by [#219](https://github.com/Nate27624/Wii-AI-Golf/pull/219). This proves the **source writer path**, not execution on every game frame.
- [Source cache trace #183](https://github.com/Nate27624/Wii-AI-Golf/pull/183) `fn_80299C70` saves r3 receiver as r27, loads a **distinct source-global ball pointer** and its `+0x4C` translation and copies three floats into r27`+0xCC..0xD4` around `0x80299CDC/CE4/CEC`. It conditionally copies into `+0xF0/F4/F8` on planar-to-goal comparison and separately into `+0xFC/100/104` on middle-coordinate comparison. Exact receiver and source-global runtime identity and invoked branches remain unresolved. **Do not assert +0xCC is a predicted endpoint solely from equal values**.
- [Actual seven-phase #230 run](https://github.com/Nate27624/Wii-AI-Golf/pull/230): W5→W6, W6→W7 selected ball `+0x30` changes 3/3, record +0x54/+0x60 unchanged 0/3, all three selected caches unchanged 0/3, pin/start unchanged 0/3, selected player/hole/object pointers constant. [#231](https://github.com/Nate27624/Wii-AI-Golf/pull/231) adds original archived snapshot within-phase relation: selected live+0x30 differs from cache+0xCC 3/3 at W5,W6 and equals it 3/3 at W7. Source positions are u32 bitpatterns; world axes/units, origin and exact frame numbers are unknown.

## Narrow testable hypothesis

An unchanging player-record +0x60 triple **cannot by itself explain all three different observed selected ball-vector snapshot values through an immediate player→ball copy alone**, absent some inter-snapshot second writer, record transients or dynamic object alias. Check exact **within each snapshot** `record+0x60 == ball+0x30` components and `record+0x54 == ball+0x30`. Record input can change between snapshots and reset before capture; cannot prove Player writer did not execute. Separately test static cache+0xCC in W5/W6 already equals selected current ball+0x30 at W7. Neither hypothesis proves executable writer timing or cache semantics.

## Implementation / outputs

`scripts/audit_p0_seven_writer_inputs_private.py` reads exactly local 1..7 24MiB/64MiB native raw pairs under the operator-supplied directory, selects each through **existing #230 source and self-reference validators**, SHA256 before/after each paired read to refuse mutation, tests selected actor/hole and pointer identity across same shot, reports only bitwise component equality counts 0..3 and categorical hypotheses. No raw words, float values, source-global pointer, file hashes, path, private page indices, RAM, ROM, or private source bytes leave the operator device. Explicit `allowed_to_publish=false`, `approved_for_training=false`, independent-frame/physical motion/endpoint flags false.

**Read-only operator command (after focused tests pass):** from the #230-stacked checkout, execute `py -I scripts/audit_p0_seven_writer_inputs_private.py --dump-directory <operator's existing Dolphin Dump folder>`; no additional Dolphin or memory exports. Test results from synthetic fabricated source samples don't stand in for the real 7 snapshots.

## Owner boundaries

Source/PPC #219 owns static symbol, BL and branch destinations. Source/cache #183 owns cache copy conditional code. S002 seven #230/#231 own source-selected trajectories. This new tool owns **only per-snapshot equality against known Player input and distinct cache**; cooperate with #205 evidence registry. If the observed result shows record input constant but live changing, the remaining writer or source-global receiver needs a targeted interpreter/waypoint or same-frame watch by the rightful owner. No duplicate RAM scans and no automatic training.

## 2026-10-28 REAL seven-pair operator result — pinned #236 SHA 59b82ea

Operator executed **exact head `59b82ea4c12b30dfb64f4f8133872ac7d01bc5a0`** in a detached local Windows worktree; **10/10 synthetic tests PASS**, then **REAL seven native source-selected pairs PASS**, `sample_count_source_gated=7`, `all_required_source_alias_and_owner_gates=true`. Original banks read-only. Raw memory, paths, hashes, numeric positions and runtime pointers were not supplied to GitHub.

| Operator-labeled phase | Ball == record+0x060, components/3 | Ball == record+0x054 | Record+0x054 == +0x060 | Ball == cache+0xCC | Ball == cache+0xF0 | Ball == cache+0xFC | Ball == START | Ball == PIN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 driver visibly airborne (operator) | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 0 |
| 2 same driver stationary | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 0 |
| 3 putter backswing A released | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 0 |
| 4 driver backswing A held | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 0 |
| 5 wedge near apex | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| 6 wedge descending | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| 7 wedge flag/on-green UI | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 0 |

Within SAME shot: driver D1→D2 selected current ball changes 3/3, player record +0x054/+0x060 do not change, all three caches +0xCC/+0xF0/+0xFC change 3/3, PIN/START remain fixed. Wedge W5→W6, W6→W7, W5→W7 selected current ball changes 3/3 on all edges, player record+0x054/+0x060 and caches +0xCC/+0xF0/+0xFC each change 0/3, START/PIN each change 0/3. Wedge current ball has three distinct triplet bitpatterns; unchanged CC triple equals final W7 current 3/3 but does not equal W5 or W6 current 0/3. Player records +0x054 and +0x060 are bitwise identical in every snapshot.

### Interpretation, anomalous snapshot and strict gates

1. **Existing static Player record→Ball writer is NOT a sufficient ongoing explanation** for wedge selected ball current+0x30 changes at the three observed points: record+0x060 input remains constant, and it is 0/3 equal to current ball in W5, W6, W7. This does NOT prove the Player writer never executes between captures or that there was no transient record; reverse sync, simulation, other writers and ownership remain candidates. Distinguish **static PPC write-site identified** from **executed active flight writer not identified**.
2. **Static +0xCC and final W7 equality** is a strong pre-existing endpoint-value bitpattern observation. #183 static cache refresh copies from a source-global ball pointer into the receiver +0xCC. Thus an apparent endpoint match might reflect a simulation/preview ball or copied target/previous position, rather than an instruction that calculates an endpoint. Existing #183/#219 code paths should trace **global source ball pointer ownership and receiver r27**; no new broad scans.
3. **Critical discrepancy:** human-labeled D1 ball was already midair, but its source-selected current+0x30 equals START, Player+0x054/+0x060 and all three caches in all components. This actively cautions against equating source-selected simulation ball memory with the on-screen moving-ball object in EVERY stage; possible multi-object ownership / pre/post simulation lifetime, phase annotation and render latency. No unverified reconciliations.
4. F0 and FC are NOT equal to current at D2 or any W5/W6/W7 (0/3), but equal current START at D1 and no-shot P3/D4. Their different update predicates in #183 support independent cached extremum-like roles, NOT independent live XYZ or verified minimum/maximum physical meaning.
5. The result documents seven *human* observation labels; mem1/mem2 native same-guest-frame atomicity, physical axes/units, actual guest frames, cache execution, true impact and score, training and public raw outputs remain FALSE.

### Next responsible source owner task

Existing source owners #183/#219 should trace ownership of source-global ball pointer read at cache refresh fn_80299C70 and r27 receiver **through fn_80299ACC and fn_80299C20** to determine whether receiver is a recorder/simulation ball or player-selected live ball, and whether the code path is simulation phase-specific. Cross-check candidate owner against static / observed D1+W5 exceptions, not simply matching endpoint values. If source-only resolution impossible, specify a *read-only runtime* source-selected watch with frame IDs and rendered-ball association **only after separate S001 approval**. Parallel #233 owns ordinal endpoint distance, #234 pin-axis hypothesis, #235 51-word selected-player mask, so do not duplicate.


### Independent contextual evidence already executed by other agents (no duplicate operator run needed)

- [PR #233](https://github.com/Nate27624/Wii-AI-Golf/pull/233) already contains a **real** operator result: squared distance from W5 current selected ball to fixed cache+0xCC decreases strictly through W6 then equals zero at W7, while CC itself stays fixed. Distances to +0xF0 and PIN ALSO monotonically decrease, so endpoint convergence is NOT uniquely diagnostic of +0xCC as a landing predictor; CC is closer than all of PIN/START/F0/FC by W6, but this is unsigned ordering without physical units.
- [PR #234](https://github.com/Nate27624/Wii-AI-Golf/pull/234) already contains a **real** strict source-axis test: 0/1/2 component trends are increase/decrease/decrease, and NONE of the W7 components exactly or approximately equals its corresponding PIN component. A separately corrected CUP/PIN comparison has equal component masks [true,false,true], suggestive of component 1 as elevation **hypothesis only**, not a proved world-up axis. Do not claim W7 ball reached PIN or at ground just because human UI shows 'Nice on'.
- Together with this #236 record-input mismatch, what is *not yet proved* is the function-and-object ownership of `fn_80299C70` source-global ball and r27 receiver during actual W5→W7. The next action is a targeted PPC caller/receiver dataflow study owned by #183/#219, not another absolute float scan, generic raw page-diff or duplicate endpoint rank calculation.

