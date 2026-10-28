# S002 P0: public Rev1 Golf typed-layout crosswalk (independent source)

**Source-only, public data; no emulator run, private RAM disclosure, or runtime semantics promotion.**

## New independent upstream discovery

GitHub-wide code search identified the [PackProject/Kokeshi](https://github.com/PackProject/Kokeshi) source repository (pinned **`dfbdda61aadad423911d5345f67f8793aa92cd5f`**). Its [README](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/README.md) explicitly lists **Wii Sports NTSC-U Rev 1** as supported, using published `main.dol` SHA1 **`8bb422971b88b5551a37de98db69557df7b46637`**. This is a *second* public reverse-engineering project, distinct from our already pinned [doldecomp/ogws RSPE01_01 splits](https://github.com/doldecomp/ogws/blob/e5a4d369011062fe243aa63f6c2e2853854c395d/config/RSPE01_01/splits.txt). The two source projects target the appropriate game and revision. **This is not proof that every external annotation was independently tested against our private original B0 banks; do not bypass per-object source and revision gates.**

The following **public header descriptions**, not new RAM measurements, are relevant:

| Public class and pinned header | Public field / structure | Source-relative offset | Confidence boundary |
| --- | --- | --- | --- |
| [`RPGolPlayer`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolPlayer.h) | `u32 mStrokeNum` via `GetStrokeNum()` | `+0x78` | Externally annotated integer stroke count, NOT swing power. |
| Same player header | Total `RPGolPlayer` class size | `0xCC` | Header's explicitly padded record; matches size of existing source-selected **51-word** candidate record (51*4 = 0xCC), but selected memory identity still separately gated. |
| [`RPGolPlayerManager`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolPlayerManager.h) | Four inline `mPlayers[4]` and `GetPlayer(i)` | Contiguous elements with `0xCC` stride if class is represented exactly | Explains *candidate* four-record roster; no absolute runtime manager pointer or pointer-to-this verified by header alone. |
| [`RPGolFieldManager`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolFieldManager.h) | `mNumTargetObjs` | `+0x30` | Distinct from player+0x30 and map-object+0x30. |
| Same FieldManager | `mTargetObjs`, `mCurrentPinObj`, `mCurrentStartObj` | `+0x34`, `+0x44`, `+0x50` | Independently corroborates S002 #183's pin/start/target source dispatch; doesn't prove a given sampled pin is current across shots. |
| Same FieldManager | `mMapBallEff` | `+0x9C` | Minimap effect pointer, NOT a verified rendered physical ball pointer or world-position field. |
| Same FieldManager | `mKillTargetEffEmitter` | `+0xA4` | Bool kill flag; corroborates but must not conflate with ball contact. |
| [`RPGolMapObjBase`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolMapObjBase.h) | `nw4r::math::VEC3 mTrans`, `nw4r::math::VEC3* mpTrans` | `+0x30`, `+0x4C` | Strong independent static map-object position schema match to S002's `+0x4C -> +0x30` selfref. Not automatically physical ball and not Player+0x30. |
| [`RPGolConfig`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolConfig.h) **versus** [kiwi515/ogws_info Config](https://github.com/kiwi515/ogws_info/blob/bcf62e22f9e7fc1d75acbb24bd8368b03cba1c81/RP/RPSports/RPGolScene/RPGolConfig.h) | **CONFLICT:** Kokeshi `mStrokeTotal[9][4]`, ogws_info `mPlayerScores[4][9]` | Both `+0x04` (144 bytes) | Same raw 36 words, **row order DISPUTED**. No selected hole/player cell indexing may be trusted until exact original Rev1 PPC getter arithmetic verified. Distinct from current player `mStrokeNum`. |
| Same Config | `mGameMode`, `mCurrentHole` | `+0x94`, `+0x98` | Distinct source-class fields from unknown Config controls `+0xBC/+0xC0/+0xC4`. |

**Important source-conflict correction (2026-10-28):** Do not privilege
Kokeshi's `[9][4]` Config score annotation over kiwi515/ogws_info's `[4][9]`
without game PPC indexing evidence. They agree on size/location but disagree
on memory order. Earlier crosswalk drafts called Config [9][4] without
explicitly identifying the contradictory upstream. Treat Config selected-cell
semantics as P0 **UNRESOLVED**; use original-code source check in draft #278
before any S000 catalog score-index promotion.

### Why this matters more than another PPC-offset scan

1. Existing PR #244 original B0 source proves a **possible**, local, two-store same-receiver code path: `RPGolPlayer` *compilation unit* `+0x2008: stfs f0,+0x30(r30)` → `+0x201C: mr r3,r30` → `+0x2024: BL +0x1BD4` → `+0x1BE8: mr r31,r3` → `+0x1C18: stfs f0,+0x90(r31)`. This does **not** type the pointer. In particular, **Kokeshi does not name Player +0x30 or +0x90**, so do not transfer MapObjBase's `mTrans` field to player offsets by coincidence.
2. Independent Kokeshi `RPGolMapObjBase +0x30/+0x4C` is a structural crosscheck for the map objects in #183/#240. It **does not** decide which of global and inline ball-related objects is visually rendered, nor establish same physics frame.
3. **Two independent public annotations CONFLICT on the Config +0x04 table's row order:** Kokeshi [9][4] versus kiwi515/ogws_info [4][9]. Existing #239 original four-edge 0/36 aggregate negative remains unaffected; the selected hole/player cell is **unresolved**. See [draft #278](https://github.com/Nate27624/Wii-AI-Golf/pull/278) for a bounded original-B0 PPC getter arithmetic audit at 0x8029CBD4/0x8029CC54. The independent Player+0x78 current-stroke candidate is a **different owner/field**. No score should be called power or impact.
4. The Kokeshi `FieldManager` public layout independently corroborates the S002 source `mCurrentPinObj` / `mCurrentStartObj` offsets and S002's pin/target confound.

### Recommended single read-only follow-up (not run or authorized here)

**Existing original B0 only**: S002 source owner should create or reuse a SHA-pinned strict native reader that independently validates (a) selected player record stride and exact four-entry manager membership (without printing addresses), (b) type-compatible `+0x78` u32 current-stroke plausibility with a static no-shot capture and an independent existing score counter, (c) Config `+0x94/+0x98` mode/hole against independently gated context, (d) FieldManager `+0x44/+0x50` pointer validity against already proven source pin/start selfrefs, and (e) MapObjBase `+0x4C` selfref→`+0x30` match. Emit **only** per-condition booleans / categorical errors, no pointer values, raw counts, floats, bank SHA, private paths or original code words. Original #219 B0 and #231 full seven-pair SHA before/after, exact source-public pin, and typed object owner need independent verification; do not dereference pointers guessed from this document. Externally annotated player score field stays *candidate* until source class and revision validation. The published DOL SHA1 is a provenance target, not permission to dump/compare user disc bytes publicly.

Then favor #215 no-swing stationary V1 runtime feasibility (S001-owner approved only), #248 independently attested guest **physics** frames and a visually verified moving-ball witness; stop new abstract register-scans. Training/physical world XYZ/velocity/impact/power, full-function CFG, and runtime selected player receiver remain **FALSE/UNVERIFIED**.

### Review / provenance

Public type data: Kokeshi `dfbdda61aadad423911d5345f67f8793aa92cd5f`; our source-split parent #219's pinned ogws/RSPE01_01 index (832 units). Typed annotations and line-by-line declared sizes are public external evidence, not a substitute for authored original B0 source witness. No private capture was read for this document. Do not merge/promote memory schema without S002 + S000 review.
