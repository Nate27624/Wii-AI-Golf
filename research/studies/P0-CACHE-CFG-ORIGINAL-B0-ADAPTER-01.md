# P0 — Authenticated original Rev1 B0 source adapter for conservative cache receiver CFG

**Draft, source-only.** This study does not analyze live game memory or authorize shots. The existing [S002 #219](https://github.com/Nate27624/Wii-AI-Golf/pull/219) source owner already verifies original B0 `checkpoint-manifest-PRIVATE.json`, SHA256 of full 24MiB MEM1, RSPE01 revision 1, and the published 832-way source code ownership map. [Reviewer #254](https://github.com/Nate27624/Wii-AI-Golf/pull/254) independently authored a *pure callback-based* PPC two-caller CFG must-definition checker with 22 fabricated tests. **Before this adapter**, the pure checker had no source-gated native read path; tests could not demonstrate actual original B0 callsite behavior.

## Narrow integration — no duplication of #254, #240, #255, #256

The new `scripts/audit_p0_cache_cfg_original_b0_adapter.py` loads **only** a helper checked out in a separate Git worktree at the exact reviewed commit `8696a46a315499f220ee7c87580a21dc99f21462`. It requires a clean Git status and matches the helper file's content to the committed Git blob before import. It then:

1. Runs original #219 source `checked_private_b0` before reading and again afterward; rejects changed full-bank SHA/manifest and source revision, no altered memory accepted.
2. Validates `load_public_text_units` and the two exact source windows for entry `fn_80299ACC` to its known cache writer BL at `0x80299B64`, and entry `fn_80299C20` to BL at `0x80299C58`, all within published `Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp`.
3. Supplies a `read_u32(pc)` callback scoped **only to those two original PPC intervals**; arbitrary RAM reads and dynamic heap pointer extraction are refused.
4. Invokes #254's unmodified `inspect_known_callers`. Returns only *source function labels*, **categorical** CFG outcome (must-flow / not-proven / abstain), and logical proof flags. No raw PPC instructions, heap addresses, source global slot, pointers, game floats, local paths or hashes.
5. Never treats successful STATIC entry-r3 through r31 to call-r3 path as actual runtime receiver identity, physical ball motion, rendered actor ownership, executed cache refresh, true frame timing, impact, velocity, power, score or training eligibility.

**Hard abstention:** The underlying CFG decoder can legitimately reject an unsupported instruction, indirect branch, internal subcall, or out-of-window jump. That is a *useful inconclusive result*, not a reader failure or evidence that the store is unused. A clean 'STATIC_ENTRY_R3_MUST_FLOW' only establishes a very narrow static reaching-definition under the validator's conservative instruction model, not an executed path or receiver class. #255 separately owns the UPSTREAM argument source to these inner functions. #240 owns source-global pointer and r13 store, while #256 owns HUD result formatting xrefs; this work does not touch their code.

## Gates before native operator run

13 fabricated-only tests cover helper revision/dirty/blob mismatch, invalid ROM revision, wrong published code owner, shortened source bounds, malformed helper/premature training promotion, output redaction, strict B0 SHA pre/post, and missing bank. Source CI runs Windows/Ubuntu **without actual private B0 or helper Git checkout**. S002 #219/#254 owner must review helper SHA and adapter privacy first. The operator can then provide **existing** private B0 folder and separate reviewed helper worktree with a single pinned PowerShell block; do **not** run this from an unreviewed PR revision.

No GitHub action reads local game RAM or native dumps. No operator capture or live Dolphin is requested. No automatic merge, no training approval; all P0 physics/score/shot/UI controls remain open. Source finding can later inform the S001/#248 same-guest-frame watcher contract only if all owners approve.


## Hosted qualification of this new adapter

At revised code+test HEAD `74535ef22009d7643c391437a8d924d63dcc1c27`, dedicated [GitHub Actions run 40650802424](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40650802424) **PASS** on both Windows and Ubuntu (**13/13** fabricated tests per OS). PR #257 contains exactly **four new files** relative to #219 and stays DRAFT. No original B0 native bank was available to GitHub CI and **the adapter has not yet been run on the operator's real B0 source**.

Independent early review detected a scientific provenance bug: the internal `report_from_bytes` helper could have claimed SHA/helper verification if called directly on fabricated bytes. This was fixed in HEAD `74535ef2`: its trust flags are FALSE until the external `audit` wrapper completes **both original-bank SHA checks, published source ownership check and exact pinned helper Git/blob verification**. New focused tests enforce this distinction.

The `CFG_SHA` pin is `8696a46a315499f220ee7c87580a21dc99f21462`, an earlier already-reviewed #254 code version, not a promise of automatic compatibility with later #254 source edits. The parent authors must review this adapter, target helper SHA and original B0 evidence before any interpretation.


## Post-review exact-source-owner hardening

Independent #257 reviewer detected that a same-family *wrong* object-file name could satisfy the original `startswith(Pack/RPSports/RPGolScene/)` check. Corrected this to require **exactly one published Rev1 source unit**, with exact name `Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp`, containing each complete entry-to-BL callsite window. New synthetic negatives reject same-family `RPGolPlayer.cpp` substitution and duplicate overlapping published intervals. GitHub Actions [run 40651407595](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40651407595) at code/test SHA `d28815b10b5150b044e0beb3b116a9354e9b67a0`: **15/15 fabricated tests PASS on Windows, 15/15 PASS on Ubuntu**. The pinned helper at #254 `8696a46a315499f220ee7c87580a21dc99f21462` and current docs-only #254 `095fbedd2ec62b9b22468cb3d8e1ed56ed9ac210` have **identical helper blob SHA** `0c7dc68b31e5484f2968eeaf6ec56dc8df238f4b`, so preserving the earlier reviewed commit does not use different helper code. This is a *static source code identity* comparison, not native runtime proof.

**REAL ORIGINAL B0 SOURCE AUDIT STILL PENDING.** Users must run a fully pinned PowerShell checkout with original private `checkpoint-manifest-PRIVATE.json`; do not claim a source-qualified must-flow result from synthetic CI. Source-owner #219 and CFG owner #254 have been notified; keep unmerged DRAFT.


## Real operator B0 native source audit — authenticated, static CFG abstains (2026-10-28)

Operator executed exact clean adapter worktree SHA `8fad2ced3b1724847b70be56ed0b670ece73cbc6` against existing original *private* B0, with exact clean #254 pure helper SHA `8696a46a315499f220ee7c87580a21dc99f21462`. **15/15 adapter synthetics** and **22/22 helper synthetics** PASS locally on Windows PowerShell 5.1. Full B0 SHA and private checkpoint manifest passed before+after, RSPE01 Rev1 and unique published Golf MapObjBall source code owner passed, reviewed helper exact commit/blob passed. No memory modification, game launch, native code values, dynamic guest pointers, floats, source paths or private SHA values output.

| Source caller | Source-integrity result | Conservative static CFG result | `known_exact_cache_writer_callsite_reached` | All-path entry-r3 receiver propagation |
| --- | --- | --- | --- | --- |
| `fn_80299ACC` | source-qualified B0 | `ABSTAIN_SOURCE_UNRESOLVED` | false | false / **NOT PROVEN** |
| `fn_80299C20` | source-qualified B0 | `ABSTAIN_SOURCE_UNRESOLVED` | false | false / **NOT PROVEN** |

**CRITICAL INTERPRETATION**: The underlying #254 pure CFG helper returns a single coarse `ABSTAIN_SOURCE_UNRESOLVED` whenever it encounters ANY unsupported X-form/PPC effect, control transfer, unknown/outside branch, unrelated linked call, or callback problem. It does **not** emit the first failing PPC location/category; `known_exact_cache_writer_callsite_reached=false` therefore means *proof search aborted*, NOT that Rev1 code cannot reach the BL or does not call the cache writer in real gameplay. Both helper functions can be statically valid and execute even when the conservative decoder abstains. No evidence promotes a rendered/simulated ball class, r3 runtime receiver, cache writer execution, physical XYZ/velocity/power/impact/score or training.

Next OWNER-SPECIFIC fix requested in [#254](https://github.com/Nate27624/Wii-AI-Golf/pull/254): preserve fail-closed CFG but add a *bounded sanitized first-abstention category* and *source-function-relative code offset* for each caller (e.g., unknown X-form, external jump, dynamic branch, other BL, source mismatch), with adversarial synthetic tests and no opcode/native byte output. Then #257 can consume the new reviewed helper version after exact-SHA pin revision. Do not duplicate the CFG implementation; do not repair by treating unknown branch/instruction as safe. A separate #255 seven-bank complete outer/inner source join remains unrun and may likewise return this same coarse ABSTAIN; do not falsely claim new runtime evidence from it.
