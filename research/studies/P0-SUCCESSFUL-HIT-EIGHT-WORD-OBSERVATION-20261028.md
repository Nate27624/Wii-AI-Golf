# S002: real positive-hit eight-word effect overlap result (2026-10-28)

**Evidence:** Operator ran PR #199 on Windows, 12/12 focused synthetic tests PASS, successful PRIVATE offline audit. Actual positive V1 shot used 45 observed Dolphin frames A lead. The resulting 3 PRE / 2 POST / 3 SETTLED source-gated snapshots yielded 8 persistent changed 32-bit words. Each changed in both POST samples and stayed stable in SETTLED; maximum non-atomic snapshot span 22 Dolphin frames. Human contact YES, finished on green NO; all eight had NO raw numeric coincidence with displayed 100.0 ft.

## Exact sanitized candidate map

| ID | Source window(s): relative offsets | Before/after pointer-shaped | Typed |
| --- | --- | --- | --- |
| C01 | player effect +0x078 | no | no |
| C02 | player effect +0x07C | yes | no |
| C03 | player effect +0x108 = shot-line effect +0x078 | no | no |
| C04 | player effect +0x10C = shot-line effect +0x07C | yes | no |
| C05 | ball effect +0x078 = player effect +0x198 = shot-line effect +0x108 | no | no |
| C06 | ball effect +0x07C = player effect +0x19C = shot-line effect +0x10C | yes | no |
| C07 | ball effect +0x108 = shot-line effect +0x198 | no | no |
| C08 | ball effect +0x10C = shot-line effect +0x19C | yes | no |

These are 8 distinct candidate **addresses** not sixteen independent words; multiple windows cover the SAME bytes. Alias relative offsets imply the shot-line window starts **+0x90** after the player-effect window; ball-effect starts **+0x90** after shot-line. Changed words therefore form four repeated adjacent pairs at offsets 0x078/0x07C within successive 0x90-spaced regions. This suggests a repeated layout or contiguous effect storage, **NOT** class/object identity proof and not physics semantics.

Independent public source support: [kiwi515/ogws_info RPGolFieldManager.h](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolFieldManager.h) labels FieldManager +0x94 player effect, +0x98 shot-line effect, +0x9C ball effect as RPSysEffect pointers. Source does not type effect-internal +0x078 or +0x07C or guarantee the pointers always refer to distinct runtime allocated objects. +0x7C per repeated region has a POINTER-SHAPED flag, not a validated pointer/class/ownership relationship.

**Crucial null for P0:** None of these 8 candidates is in golf_config, golf_field or sports_sequence; all source readers classified as visual-effect windows. The actual selected player record, selected simulation/ball translation, club/power, contact, velocity, landing and result state were NOT directly sampled in this capture. This single post-shot effect change cannot establish any of them. No verified numeric power/velocity/ball XYZ or official game score; training false.

## Required ownership handoff

S002 source analyst: trace PPC RPSysEffect construction, lifetime, +0x078/+0x07C writer(s) and effect-management branch conditions using existing Wii Sports Rev1 binary/source, including A-only/idle controls; distinguish effect reinitialization from ball physics. Do not use name 'ball' to infer physics because 'mMapBallEff' is a minimap effect.

S001 integrator: retain successful V1 bridge plus 45 **observed frames** holding A (NOT 45 RPC calls), unchanged 89-sample waveform; verify read budget, noninterference and bridge compatibility before a new selected-record memory watch. #189 V2 watcher is draft and has not demonstrated contact. Do not run a new live shot without explicit approval.

S002 player/ball owner: source-selected record +0x024 untyped state word, +0x088 ball-related child pointer, +0x054/+0x060 initialized vectors, linked ball Base +0x030 via +0x04C, simulation cache vectors +0x0CC/+0x0F0/+0x0FC are stronger dynamic-target leads. Initialization equality != live ball position or speed. S000 privacy and S003 model owners retain strict evidence gate; no raw RAM or unredacted saved candidates shared or published.

This note contains only relative offsets, phase counts, names and boolean classifications. No raw guest memory words, runtime addresses/pointers, ROM contents or local filesystem paths.
