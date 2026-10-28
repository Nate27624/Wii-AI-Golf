# P0-EFFECT-TAIL-OWNERSHIP-01 — test the source pointer and five window-tail words

**Status:** S002/S000 review required. This study uses the operator's **already successful** V1 positive-shot capture (3 PRE, 2 POST, 3 nominal SETTLED). **No new Dolphin run or controller input.** The script lives in a new branch **stacked on draft PR #209**, so it can reuse #209's strict private source/phase/pointer-alias validation without duplicating it. Do not merge this child before its parent. The operator has not yet run this particular new analysis.

## Specific question / source foundation

The previous real offline run produced **zero strict POST-restored transient words, eight persistent effect-associated words, and five unstable SETTLED words**. All five are at the **last 20 bytes** of the bounded `minimap_ball_effect` source window: `+0x1EC, +0x1F0, +0x1F4, +0x1F8, +0x1FC`. These five differ in both POST and all three SETTLED samples but were not linked to the source-selected physical ball object.

In [`src/wii_ai_golf/audit/outcome_transition.py`](../../src/wii_ai_golf/audit/outcome_transition.py), `capture_outcome_windows()` reads three candidate effect pointers from `golf_field+0x94` (player), `+0x98` (shot line) and `+0x9C` (ball), each for **exploratory `EFFECT_BYTES=0x200`**, which is **NOT a source-proven object size**. Independent effect-handle study [#208](https://github.com/Nate27624/Wii-AI-Golf/pull/208) supports the observed **`0x90` spacing of effect-window starts**, not a proven allocation or array. The first, second and third 0x200 reads overlap; the last five bytes/words of the third do not overlap either prior read.

**Hypothesis (arithmetic only):** With the first effect-window pointer as a *calculation origin*, all five tail words fall at **hypothetical stride index 5** (`0x90 * 5`), with positions `+0x3C, +0x40, +0x44, +0x48, +0x4C` *within that hypothetical stride*. This does **not** establish six real allocated effect instances, field offsets, an object size, or physical ball XYZ. The source-selected true ball object's `+0x4C` is a DIFFERENT pointer/object graph; equal numeric offsets are NOT an identity match.

## One narrowly targeted offline operation

The new `scripts/audit_p0_effect_tail_ownership_private.py` reuses the original shot and unsettled validators from parent #209. It:

1. Requires the exact human-positive V1 45-observed-A-lead + frozen-89 trace and validated 3/2/3 phase cohort, source revision, stable windows and original **0/8/5** control counts.
2. Re-reads only the ALREADY recorded `golf_field` bounded words at `+0x94/+0x98/+0x9C` and confirms **each field's pointer value equals the corresponding source-window start** in **all eight** phase snapshots, with no relocation and `0x90` adjacent start spacing.
3. Independently confirms the five unique tail locations are covered by **one** recorded source window, and occupy the hypothetical slot index 5, relative +0x3C/+0x40/+0x44/+0x48/+0x4C.
4. For **each** of six *hypothetical* 0x90-spaced indices (0–5), compares only those five corresponding positions across PRE/POST/SETTLED, reporting **counts**, number of overlapping captured windows (1/2/3), stable PRE, any POST difference, and unstable SETTLED—**no bytes or values**. Detects alias contradiction as invalid rather than inventing semantic ownership.
5. Saves one `*-EFFECT-TAIL-OWNERSHIP-SANITIZED.json` ONLY under the ignored sibling `Wii-AI-Golf-Data/captures`. If the same file already exists, it **recomputes and verifies identical JSON without overwrite** (a previous operator blocker). It never uploads raw/private JSONL, guest addresses, vectors, config, ROM, or game bytes.

PowerShell `scripts/Invoke-P0EffectTailOwnership.ps1` runs source/settled/new synthetic tests, checks both earlier successful sanitized results (0/8/5 and five effects), and prints only safe counts/alignment flags. It cannot launch Dolphin or modify other agents' worktrees.

## Expected interpretation

- **All pointer field checks pass and tail is only covered once:** confirms the bounded capture's *pointer/overlap geometry*, **NOT** memory allocation boundaries. A one-window measurement is less independently corroborated than two or three overlapping reads.
- **Same relative position behaves differently in other hypothetical strides:** evidence of differential byte behavior only. The `0x90` spacing could be disjoint fields, an array, or adjacent memory; the script cannot choose.
- **Any pointer mismatch, unexpected sample timing, ranker crosscheck failure, contradictory overlap, or changed study profile:** fail closed; no source-owner claim.
- The five tail values' original SETTLED variability can reflect visual effect lifecycle, neighboring memory, late transition or non-atomic temporal drift; never infer ball XYZ, vertical velocity, power, score or training eligibility.

**Next S002 owner source step:** investigate allocation/lifetime/source stores of `golf_field+0x9C` pointee, compare actual `RPSysEffect HandleBase` layout and known `0x90` effect-handle IDs from PR #208, and *only after proving owner/size*, investigate actual source-selected linked ball object translation +0x4C with a separate confirmed in-flight/no-hit pair. No further generic broad memory scan.

## Real operator-run result, 2026-10-28

The operator executed the exact reviewed child head `fcfb9ac2bacb6d2da6ed1bedbeac4c63eb1699e4` from a clean **detached worktree**, using **existing local private snapshots only**. All source tests passed locally: 15 baseline synthetic tests with **one Windows symlink-privilege skip**, plus 8 settled-pattern tests and 8 effect-tail tests (30 passed, 1 skipped, 31 executed). The **REAL** audit (not synthetic) wrote a private sanitized result:

- Source `golf_field` pointer words at `+0x94/+0x98/+0x9C` match the associated captured sample window starts in **all eight phase snapshots of the same shot**; all starts fixed over the cohort; pointer start spacing **144 bytes (`0x90`)**.
- Each effect-named source window is **512 bytes (`0x200`) of exploratory READ**, **not proved object allocation size**. All five unstable addresses at `minimap_ball_effect` +0x1EC, +0x1F0, +0x1F4, +0x1F8, +0x1FC are only covered **once** among the three overlapping reads. Their arithmetic re-expression relative to first effect start is at hypothetical index 5 +0x3C/+0x40/+0x44/+0x48/+0x4C, not a genuine instance number or join to the source-selected ball translation.
- In the five corresponding sampled words per **hypothetical** index, all indices 0–4 have **zero** POST differences and **zero** unstable SETTLED; index 5 has **5 of 5** POST differences and **5 of 5** unstable SETTLED. Coverage by effect-named windows for indices 0–5 is respectively 1, 2, 3, 3, 2, 1. The one-window coverage at index 5 cannot serve as an independent overlapping-read confirmation.
- Maximum phase snapshot read bracket: **22 Dolphin guest frames**, not an atomic game-state sample. `SourceAllocationSizeVerified=False`, `TrainingApproved=False`, `AutoGitHubUpload=False`. This establishes sampled pointer consistency and localization, not real `RPSysEffect` allocation ownership, physical ball coordinates, power, velocity, an actual sixth array item, or training eligibility.

This source-relative finding was posted to draft [#216](https://github.com/Nate27624/Wii-AI-Golf/pull/216), S002 [#3](https://github.com/Nate27624/Wii-AI-Golf/issues/3), P0 [#121](https://github.com/Nate27624/Wii-AI-Golf/issues/121), and effect lifecycle [#208](https://github.com/Nate27624/Wii-AI-Golf/pull/208), without raw data or runtime addresses. The saved private sanitized JSON is **NOT UPLOADED** to research/observations; public issue comments are not an observation-branch upload.

**Next comparison before another swing:** S002/#199's latest capture inventory reports **11 matched human-contact-positive pairs** including the one studied here. Have the S002 owner compare stable source-relative signatures and effect-pointer geometry *per exact run*, with provenance/phase-shape checks and no-hit controls. Other pairs have different persisted counts and may have different window availability; do **not** blindly apply this cohort's hardcoded 0/8/5 to the others, and do not treat multiple hits as independent same-scene/identical-power trials. Compare only what each independent source audit actually proves. Because draft #208 already investigates effect handle IDs/pointers, don't duplicate its source work.

## Privacy, GitHub and review

This is a new-only branch with no S001 live controller or S002 #208 source changes. The **automatic sanitized observation publisher** in `scripts/research_cli.py` does not yet support this special offline study, so **`AUTO_GITHUB_UPLOAD=NOT_IMPLEMENTED`**. The agent must record a safe source-window-relative **FINDING** comment on the owning issue/PR when the operator supplies its results; do not upload native snapshots or pretend an observation branch commit exists. Source scientific significance must pass S002 review, and any typed registry update belongs to S000's #205 owner. No full repo suite or live game test is represented by focused CI.

**Operator action:** one self-contained reviewed-head isolated-worktree PowerShell block provided separately in the conversation after cross-platform targeted CI passes. Do not run a literal placeholder head or ask the operator to operate Dolphin manually.
