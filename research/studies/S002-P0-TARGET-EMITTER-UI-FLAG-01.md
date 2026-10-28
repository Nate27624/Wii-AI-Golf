# S002 P0 — Source-defined target-effect emitter kill flag (+0xA4)

## New variable, explicit scientific type

Public Wii Sports Golf source-reference layout `RPGolFieldManager.h` (kiwi515/ogws_info pinned commit bcf62e2) declares `bool mKillTargetEffEmitter` **at FieldManager-relative byte +0xA4** with a comment that it kills target effect emitters for blinking. The immediately preceding `RPSysEffect* mMapTargetEff` is at +0xA0; `bool mShowMiniMap` is at +0x88. Source `RPGolFieldManager::sInstance` is mapped through MEM1 pointer storage 0x804BF868 in existing S002 code. This is a **visual/effect-control candidate**, not physical collision, flag hit, ball contact, golf score or landing. Source field type does not show that the specific target effect is active during a shot.

Source reference: https://github.com/kiwi515/ogws_info/blob/bcf62e22f9e7fc1d75acbb24bd8368b03cba1c81/RP/RPSports/RPGolScene/RPGolFieldManager.h

## Existing-data experiment (no new shot)

New-only `scripts/audit_p0_seven_target_emitter_flag_private.py` stacks **exactly** on canonical #231's `audit_p0_seven_numbered_source_pairs_private.py` reader. It requires seven preserved numbered 24MiB MEM1 + 64MiB MEM2 bank pairs and checks all **14 original manifest SHA-256 values before and after the read-only run**. The source reader validates RSPE01 revision 1, actual golf scene, mode4, source-selected player/ball, pin/start/config. The extension reads only FieldManager +A0 as pointer presence/identity, FieldManager +A4's FIRST byte (big-endian bool), and +88's FIRST byte as minimap visibility control. Strict `0` or `1`; malformed source flags trigger ABSTAIN. No arbitrary heap scan or target-effect pointer dereference.

Compare only D1->D2 and W5->W6, W6->W7, W5->W7 **as provisional same-shot annotations**. Require identical selected owner/hole/ball/FieldManager/pin/start/config identities, pin/start triplets and BC/C0/C4 raw selector fields. Print only seven booleans per source UI flag/pointer presence plus four change booleans and selected-ball three-word change counts. A pointer change may indicate the on-screen effect was recreated or absent; it is not a shot-impact event.

**Critical: operator says seven file labels or shot grouping might be wrong.** No machine-verified temporal order, source visual correlation, same-game-frame MEM1/MEM2, impact, score, power, or physical ball XYZ/velocity may be inferred from any outcome. A stable flag is simply a negative in this cohort; a changing flag means only a UI effect control byte changed in the captured scene, NOT that the ball struck the target. Retain `training_approved=false` and `allowed_to_publish=false`.

## Execution after review

From an exact commit-pinned detached Windows checkout with canonical original private archive already preserved under ignored `Data/captures`:

    py -I scripts/audit_p0_seven_target_emitter_flag_private.py --archive <existing-original-p0-new-cohort-PRIVATE-folder>

Do not substitute any other 7-pair directory or fabricate phase labels if the manifest fails; no raw bytes, SHA, absolute paths, floats, source code words, ROM/DOL, game input or Dolphin launch should be uploaded. Owner can review only sanitized result. Native private experiment **not executed** in CI or by this branch.

## Validation / ownership

Test synthetic cases with:

    py -I tests/test_p0_seven_target_emitter_flag_private.py

Focused Windows/Ubuntu Actions workflow: `.github/workflows/p0-target-emitter-flag.yml`. Reviews required from S002 #231 canonical reader and S000 #205 registry/semantic owner; no merge or training approved by synthetic CI alone. Avoid duplicating #150 environment source-field inventory and #245 SequenceMgr scores; this study uniquely observes FieldManager +A4 across original seven human-annotated captures and refuses any collision/impact claim.

**Follow-on only if real change occurs and phase evidence improves:** seek source write-site and control-flow semantics for +A4, and compare independently synchronized visual target blinking versus RAM. If +A4 is unchanged in this cohort, deprioritize it as a shot-result or contact marker instead of repeating scans.