# P0-SHOT-SETTLED-VARIABILITY-02 — classify five unstable settled words (offline)

**Evidence origin:** the user's ACTUAL 2026-10-28 Windows PowerShell execution of [draft PR #209](https://github.com/Nate27624/Wii-AI-Golf/pull/209) at exact head `63f4e0e27ac04cc0354e4386303cc42c284ffdbd` on the original human-confirmed positive V1 shot. No new emulator capture.

## Proven result vs new hypothesis

| Original private original-shot metric | Observed |
| --- | --- |
| Synthetic tests | 15 executed: **14 pass, 1 skipped** (Windows symlink privilege) |
| Actual strict PRE-stable → POST-changed → SETTLED-restored words | **0** |
| Previously audited persistent PRE != SETTLED words | **8**, same visual-effect-associated alias group |
| Words excluded because PRE samples differ | **0** |
| Words excluded because SETTLED samples differ | **5** |
| Max non-atomic bracket for any source-gated sample | **22 Dolphin frames** |
| Training approval / verified ball-world-XYZ / velocity / swing power | **NONE** |

**Do not confuse** the synthetic fixture's separate `unique_transients=4 persistent_crosscheck=1` console output with the real `0/8/5` evidence. The actual result refutes the **specific restored-to-baseline transient hypothesis inside the sampled windows**, not all other RAM. A value that changes within nominal SETTLED might be a timer, cursor/effect lifecycle, transition state, a late shot effect, or an invalid phase label. This study does **not** infer which one.

The operator separately recalls one other JSON-associated capture with a **definitely nonstationary** ball, but is **not sure** whether it was descending or which B0–B3 sample belongs to it. Do not confuse that unrelated, unlocated capture with this confirmed V1 strike.

## Actual operator-run outcome — 2026-10-28 (supersedes planned-only status)

The operator ran pinned commit `a75dbff96e41381bb75fc6f42d2d0beababc938a` from an independent **clean detached Windows worktree**. The historical-source private capture checks and result schema all PASS, including the prior saved `0 transients / 8 persistent / 5 unstable-SETTLED` evidence. Original 15 synthetic tests: 14 pass, 1 skip (Windows symlink privilege); additional settled tests: 8/8 pass. The **real**, non-synthetic capture produces:

- `unstable_settled_unique_word_count=5`, `non_effect_count=0`, `effect_only_count=5`, `original_transients_crosscheck=0`, `original_persistent_crosscheck=8`, `max_snapshot_frame_span=22`, `training_allowed=false`.
- All five *unique aligned sampled addresses* occur **only** in the bounded source window named `minimap_ball_effect`; relative offsets: **+0x1EC, +0x1F0, +0x1F4, +0x1F8, +0x1FC**. Each differs from PRE in both POST samples and all three nominal SETTLED samples, with two distinct SETTLED bit patterns, and the last is not equal to PRE. These are **not** equivalent to five distinct semantic game fields.
- **Source boundary caveat is critical:** `src/wii_ai_golf/audit/outcome_transition.py` declares `EFFECT_BYTES=0x200`, begins this window at a pointer read from `golf_field+0x9C`, and reads 0x200 bytes *exploratorily* without proving object size. The five words are the **last 20 bytes of this arbitrary read window**. The three effect pointer starts are only 0x90 bytes apart, verified independently in #197/#208, so overlap/adjacent records or tail-of-allocation are real confounds. **`effect_only_count=5` means only the named source window contains these words; it does NOT establish the words are owned by an `RPSysEffect` or a true ball object.** No guest object size/field meaning or independent physical ball movement is established.
- This closes the specific strict-restored POST candidate hypothesis and this five-word settled-tail count for the **six originally sampled narrow windows**, not all Wii RAM. The correct next investigation is source-bound `golf_field+0x9C` pointer/object lifetime/known `0x90` repeated layout and source-selected ball object `+0x4C` translation mapping with an independent no-hit control, not merely raising a snapshot byte budget or repeating the same live swing. S002/#208 owns effect lifecycle investigation, S000/#205 owns registry; do not edit their files without review.

Sanitized **FINDING** is recorded in PR #209, S002 issue #3, P0 issue #121, and the #205/#208 owner threads. **No automatic `research/observations` upload** occurred; the local sanitized result and all original raw capture files remain in ignored Data. No additional Dolphin execution was requested.

## Targeted next analysis

The new additive `scripts/audit_p0_settled_variability_private.py` (driven by `scripts/Invoke-P0ShotSettledVariability.ps1`) reuses **exactly the same original `audit_p0_shot_transients_private._samples()` verification**: correct RSPE01 US rev1, mode4, actual 45 **observed frames** A-lead, frozen 89-sample trace, human contact YES, ordered guest frame starts, bounded and stable source window addresses, original persistent-rank crosscheck and conflicting-alias exclusion. It also recomputes the previous transient count.

For the five candidate **unique aligned words** with stable PRE but **multiple different SETTLED values**, the report includes:
- Anonymous IDs S001–S005 and **source-window-relative offsets only**, with overlapping aliases listed under the **same ID**, never private runtime addresses or raw 32-bit words.
- How many POST samples differ from the PRE value (0–2); how many SETTLED samples differ (0–3); count of distinct SETTLED bit patterns; whether the *last* SETTLED word equals PRE.
- Whether each word belongs solely to the known minimap/effect windows or appears in source-gated config/field/sequence data, and whether any sampled bit pattern is pointer-shaped or finite-float-compatible. **These shape flags are not semantic types or physical measurements.**
- `effect_only_count` and `non_effect_count`, max non-atomic snapshot span, 0/8 original control crosschecks; all training/ball XYZ/power verification flags FALSE.

The output is **exclusive-created** in the ignored sibling `Wii-AI-Golf-Data/captures` as `*-SETTLED-VARIABILITY-SANITIZED.json`. Raw original captures are neither modified nor uploaded. A new filename avoids overwriting the first real 0/8/5 report. The PowerShell runner requires that earlier report with exactly **0 POST-restored / 8 persistent / 5 unsettled** before running the second experiment. It uses only the existing PR's isolated offline code and synthetic tests; **no Dolphin start, savestate, input or swing**.

## Review and next variable attribution

**S002 owner**: if any source-window-relative non-effect candidate survives, identify the corresponding PPC writer, its object lifetime and which phase/game mode can change it. Compare no-shot idle/aim (B0–B3) controls and actual frame-aligned flight before claiming shot relevance. If all five are effect/sequence timing words, log a negative with the redacted offsets and stop investigating them as ball XYZ.

**S000 publication owner**: the trusted `research_cli.py` only auto-publishes existing `test` and `v1` allowlisted schemas. This special private audit **DOES NOT AUTOMATICALLY UPLOAD TO GITHUB**, and must not silently publish raw JSON, source words or dynamic pointers. Its safe aggregate 0/8/5 finding was posted in [P0 issue #121](https://github.com/Nate27624/Wii-AI-Golf/issues/121), [S002 issue #3](https://github.com/Nate27624/Wii-AI-Golf/issues/3) and [PR #209](https://github.com/Nate27624/Wii-AI-Golf/pull/209). Upon any future real settled-run result, post only verified sanitized counts/offsets in those issues and request registry #205 owner to add **candidate or falsified** entries with source provenance; zero training approval.

**Current status:** the real settled-variability offline audit was completed and produced **five named source-relative effect-window-tail offsets**, all non-training. Draft #209 remains unmerged, pending S000/S002 review and full-suite gates; the targeted cross-platform synthetic tests were green at the operator's pinned code revision. No new live shot, raw data upload or further operator action is required for these same captures.
