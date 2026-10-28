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

**Current status:** additive code and synthetic tests are in draft #209. Hosted Windows/Ubuntu CI and S000/S002 review required for exact new head. No actual settled-variability offset/result has been observed yet. Operator can run the separate isolated worktree PowerShell from the reviewed PR handoff when asked, never a manual Dolphin step.
