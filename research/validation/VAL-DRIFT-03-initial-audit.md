# VAL-DRIFT-03 — initial public 24-run negative-source audit

**Status:** reproducible exploratory tabulation of an already-published **sanitized** cohort, **not** completion of preregistered negative controls or identification of power.

## Evidence source and procedure

Read the immutable published summary [`cohort-20261025T025308Z-fbda2d0e`](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/cohort-20261025T025308Z-fbda2d0e.json) from `research/observations`. It reports 24 valid independent input capture *files*, 0 exclusions and 84 distinct relative word offsets changing in at least two captures. Group `recurrent_words` by literal allowlisted region name; count offsets per region, how many changed in all 24 records, and the highest recurrence among non-minimap groups. No raw data/absolute RAM address/different instance values were examined or re-published.

| Region | Distinct recurring offsets | Offsets changing in all 24 captures |
| --- | ---: | ---: |
| `minimap_ball_effect` | 23 | 4 |
| `minimap_player_effect` | 28 | 6 |
| `minimap_shot_line_effect` | 27 | 6 |
| `golf_config` | 2 | 0 |
| `golf_field` | 4 | 0 |
| **Total** | **84** | **16** |

Thus **78/84 = 92.9%** of the distinct recurring changed offsets are in rendering/minimap-effect regions. All **16/16** universal offsets are in those effect regions. These are *offset counts*, not estimates of game-time change frequency or causal effects.

### Non-rendering recurrence is weak and not gameplay ownership

| Region-relative offset | Captures changing / 24 | Caveat |
| --- | ---: | --- |
| `golf_config +0xBC`, `+0xC0` | 7 each | Unknown content; game configuration region, not source-proven golfer/power |
| `golf_field +0x44`, `+0x50` | 7 each | Known pin/start pointer slots, **not** club power |
| `golf_field +0x6C`, `+0x88` | 5 each | Unknown/field-manager or minimap visibility category; not proven power |

Those six offsets did not change in 17–19 of the 24 analyzed capture files, by the summary's run-count definition. This does **not** establish that they are null under all real swings: phase, sampled window, pointer stability, and capture conditions differ.

### Additional independent negative-control evidence

[Focused idle → aim-only → idle capture `20261025T030124Z-9dab7f37`](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T030124Z-9dab7f37.json): 28 focused snapshots, 0 changed relative words, 9-frame max/mean read span; human stage labels were `unchanged`, `camera_moved`, `unchanged`. This is a **no-shot focused-region null** under one observed session, not a sensitive in-swing measurement or an equal-window contrast with the 22-frame broad legacy audit.

## Falsification-relevant conclusions

1. **Rejected unsupported claim:** Frequent/reproducible offset changes by themselves identify a golf swing-power register. These sources contain no verified gameplay power field.
2. **Promising falsification study:** Track the six non-minimap offsets through independent idle / camera / A-only negative controls; *source-verify* object roles and compare a future same-shot, frame-bracketed contact condition. Until then they are only candidate structural controls.
3. **Sampling failure mode:** 9- and 22-frame spans cannot establish when a fast swing transient occurred. A new bounded source-backed golfer watchlist must demonstrate adequate frame-span distribution before per-frame attribution.
4. **Stop condition:** If candidates change under controls, only reflect score/pointer/scene state, or cannot be source-linked to the golfer, return `no_identified_power_field` and **do not fit a power-response model**.

## Next owner actions

- **S002 (VAL-DRIFT-03):** compute per-phase negative-control rates, not just aggregate `within_phase` versus `boundary`. Report excluded and relocated runs; do not assume 24 captures imply 24 independent clean boots or strokes.
- **S002 (VAL-SOURCE-04):** source-prove the gameplay scene/active golfer pointer chain; the RPGolScene `+0x9C` member alone is insufficient.
- **S001/S002 (VAL-LATENCY-06):** get p50/p95/max read spans with tiny watchlists, record game frame rollback and uncertainty.
- **S003:** exclude minimap, score/mode and pointer slots as numerical swing-power labels; use the VAL-PENALTY-02 score contamination canary.

Evidence is *already public and source-derived*. This document is an analysis of it; no new live Dolphin experiment was run.
