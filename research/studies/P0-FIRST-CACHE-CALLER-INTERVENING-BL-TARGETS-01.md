# P0 — source-authenticated first-intervening BL targets in both cache receiver callers

Owner/support [#257](https://github.com/Nate27624/Wii-AI-Golf/pull/257); original source [#219](https://github.com/Nate27624/Wii-AI-Golf/pull/219), pure CFG source [#254](https://github.com/Nate27624/Wii-AI-Golf/pull/254). **New narrow source-only investigation; no runtime game action.**

## Actual prior real operator evidence (not rerun in this PR)

At B0 original private Rev1 source, fully authenticated #257 (19/19 dedicated adapter tests) + #254 exact reviewed `abd875dc83f3cf8e773c1790272ffb4759f37ef7` (34/34 dedicated tests) returned:
* `fn_80299ACC`: `INTERVENING_CALL` at source-relative `+0x001C`; `ABSTAIN_SOURCE_UNRESOLVED`.
* `fn_80299C20`: `INTERVENING_CALL` at source-relative `+0x0020`; `ABSTAIN_SOURCE_UNRESOLVED`.

Both exact SHA, public source-file and helper commit gates PASS. Crucially `exact_writer_call_reached=false` is only a *bounded proof abstention*, **not** a negative actual call/receiver claim.

## Independent new study

New `scripts/audit_p0_cache_cfg_first_intervening_bl_private.py` uses the #257 authenticated B0 SHA/manifest/RSPE01 Rev1/public 832-unit code owner/pre-post SHA, and exactly the new #254 reviewed helper. It accepts ONLY two source-report rows, each with `INTERVENING_CALL` and bounded uppercase source-function-relative `+0xNNNN` offset. It reads exactly two native PPC **code words** from their source-authenticated windows, does **not print either**, decodes ONLY true direct PPC major-op18 linked `bl`, and maps each static callee destination to an unambiguous public ogws source object-file and object-relative code offset. If linked `bc`, it reports conditional unresolved; if no published source unit, it reports out-of-index; if an opcode is not a link branch at the exact quoted witness or source maps are ambiguous, it safely refuses.

There are **no native RAM arrays, float words, dynamic guest pointers, private SHA hashes or file paths** in the emitted JSON. Uses original immutable B0; does not read the seven new shot capture banks. The `source_only_two_callers` report is qualified only after all original #257 B0 + exact #254 helper checks passed. It does not traverse whole functions or assign source-register reaching definitions, r31 semantics, callee return registers, runtime execution, rendered ball, physical XYZ, velocity, power, contact, shot scoring or training. In particular it does not repeat #240/#262's two *GLOBAL-STORE* BL callees or #255/#263's upstream outer-argument r4/r30 investigation.

## Synthetic gates and interpretation

15 fabricated tests include exact two public source-owner labels, real-looking direct BL generated words, changed/incorrect opcodes, conditional link, out-of-index target, overlapping published source unit ambiguity, swapped callers, wrong SHA claim, malformed/overlong offsets, redacted privacy schema, isolated `python -I` help and SHA-before/after behavior. CI tests on windows-latest and ubuntu-latest without game binaries.

A direct BL target public code unit is a real static code-flow edge from the original B0 if source authentication succeeds. It is **not** proof of call execution on any user shot or an ABI callee preserving volatile `r3`. Keep #254 `ABSTAIN_SOURCE_UNRESOLVED` and all runtime/training flags unchanged. S002 owners can choose whether to inspect just those identified public callees for actual ABI effects, then refine #254 only with reviewed sound PPC semantics.

All seven human-labeled shots remain first-hole-only, phase labels unverified. No new shot/dump/hole2 needed or authorized.

## Operator follow-up

Only after cross-platform CI and S002 source review, fetch an immutable reviewed branch SHA by `gh api` and `git fetch`, worktree-detach the reviewer-pinned #254 helper at `abd875dc83f3cf8e773c1790272ffb4759f37ef7` and this branch, run focused synthetic tests, then `py -I` new analyzer with existing `--private-session`, `--data-root`, and `--helper-root`. Print only `source_opcode_class`, public callee file/relative offset, and all scientific false flags.


## Real operator authenticated B0 call-target results — 2026-10-28

The operator ran exact immutable #264 SHA `7d9d3a4559c81a00d8c7d82dfc0af368bcb840b2`, #257 inherited authenticated original B0 source adapter, and exact diagnostic CFG #254 `abd875dc83f3cf8e773c1790272ffb4759f37ef7` through gh-pinned clean worktrees. Local **15/15 new target**, **19/19 adapter** and **34/34 CFG** synthetic tests PASS (total 68). Original private B0 full SHA pre/post and RSPE01 Rev1/public owner gates passed; `P0_INTERVENING_CALL_TARGETS=COMPLETE`; no Dolphin, new shot, original bank write or native bytes published.

| Proven source caller first unresolved BL | Native direct-call syntax | Public callee compiled source object | Source-object-relative callee destination |
| --- | --- | --- | --- |
| `fn_80299ACC +0x001C` | `DIRECT_BL_TARGET_IN_PUBLIC_SOURCE_UNIT` | `Pack/RPSports/RPGolScene/RPGolScene_unsplit.o` | `+0xB048` |
| `fn_80299C20 +0x0020` | `DIRECT_BL_TARGET_IN_PUBLIC_SOURCE_UNIT` | `Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp` | `+0x3614` |

Both `ReturnSemanticsVerified=False`, `RuntimeReceiverVerified=False`. **This is two AUTHENTICATED STATIC direct PPC BL target source-unit placements**, not an exact named function/symbol identity or proof calls execute in a recorded shot. The named compiled source unit `RPGolScene_unsplit.o` cannot by itself assign a higher-level function, code effect or data owner. The #254 CFG for both inner functions remains `ABSTAIN_SOURCE_UNRESOLVED` on `INTERVENING_CALL`. No justified all-path entry r3 preservation, r31 callee effect, selected-vs-global receiver, actual cache writer activation, rendered physical ball, velocity, XYZ, time, impact, score or training.

**Handoff / ROI decision:** Share these two public callee object placements with #254 CFG and #219 source owners, then STOP this child lane as requested in central #121 triage. Only source-owner review of the *existing published compiled code/symbols* is reasonable if it can directly change the conservative call-effects/receiver proof; do not run another unowned per-call decoder or ask operator for duplicate B0 scans. More effective parallel priorities remain #240 constructor return semantics and S001/#248 dual-object same-guest-frame evidence, with user approval for any new runtime input. Existing seven shot captures are all hole 1, human phase labels not machine validated.
