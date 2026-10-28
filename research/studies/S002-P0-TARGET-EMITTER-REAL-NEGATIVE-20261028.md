# P0 FieldManager target-emitter +0xA4 — original seven-capture real result (2026-10-28)

## Evidence provenance

Human operator ran the exact source-pinned parent of draft PR #252, commit `28d7a6069e2a2cfabded7fb75d4da951a1df37fd`, from a local isolated Windows worktree using the seven preserved original private numbered pairs. The operator pasted the **sanitized full console result**. No raw banks, heap pointers, vectors, private file paths, code bytes or bank hashes were published. The report showed:

- Exact source revision and source-file blob checks passed.
- Local fabricated source tests: **15/15 PASS**.
- Original **14/14** native MEM1/MEM2 archive banks checked against their canonical preserved SHA manifest before and after the real read-only analysis.
- Source-based Rev1/scene/selected-player/FieldManager/ball/geometry controls passed; all four provisional source-owner and PIN/START/Config comparisons passed.
- `P0_REAL_STUDY_COMPLETE` and validated report flags were printed only after the real analyzer returned success.

The archive entries 1–7 have **operator-supplied, unverified human phase labels**. The user has indicated earlier that labels may be wrong; no machine-verified shot chronology or guest-frame atomicity was demonstrated. All captures to date were user-described as **first hole only**, without proving cross-hole generality.

## Real empirical observations

| Source-defined variable | First-level source offset | 7 numbered captures |
| --- | --- | --- |
| `RPGolFieldManager::mKillTargetEffEmitter` (first byte of BE word) | Field +`0xA4` | **false for all 7** |
| `RPGolFieldManager::mShowMiniMap` (first byte of BE word) | Field +`0x88` | **true for all 7** |
| `RPGolFieldManager::mMapTargetEff` pointer present | Field +`0xA0` | **nonnull for all 7** |

Four *provisional* comparisons: 1→2, 5→6, 6→7, 5→7.

- `mKillTargetEffEmitter` changed: **false in all 4**, change count **0/4**.
- `mShowMiniMap` changed: **false in all 4**, change count **0/4**.
- `mMapTargetEff` pointer changed: **false in all 4**, change count **0/4**.
- Source-selected ball translation-candidate `+0x30` BE-u32 triplet changed: **3/3 components in each of all 4** comparisons.

## Scope and disposition

**Promote only the observation of a constant source-declared effect-control flag within this dataset.** It is a reliable negative control for these captures, not a discovered impact, target-hit, score, landing, game-phase, physical-motion, or collision variable. Nonnull target-effect pointer does not prove blinking or live target existence. A constant `mShowMiniMap` does not distinguish shot phases. No native input frame labels, rendering proof, world XYZ, velocity, power, contact, timebase or training authorization.

**Recommendation to S002/S000:** mark +`0xA4` as *source_layout_verified, observed_7_of_7_false / not_impact_discriminative_in_current_cohort*; de-prioritize this exact mode-4 first-hole comparison unless a future distinct game mode or independently witnessed target-effect blink becomes available. Do not collect identical seven archives or ask the operator for new shots just for this UI variable. Keep all `training_approved=false` and `allowed_to_publish=false` gates.

The higher-value unresolved P0 source investigations remain the **separate source-global ball object**, the cache receiver, and genuinely live result presentation. Those lanes already have owners (#240/#254/#256); this PR neither modifies their tools nor duplicates their source mapping. 
