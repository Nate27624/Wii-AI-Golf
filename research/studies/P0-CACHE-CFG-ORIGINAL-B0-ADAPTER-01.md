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
