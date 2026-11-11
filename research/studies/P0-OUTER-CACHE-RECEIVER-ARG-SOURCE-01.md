# S002 P0 — incoming r3 source hints for two OUTER golf cache-call dispatchers

**Draft, native-free, source-only, source-owner-review required.** This study is a non-overlapping support piece for #219 and #240, not a global ball scanner, PPC xref writer, active game watcher or RAM tool.

## Why this matters

Real operator #240 found the r13 source-global slot loaded at 15 direct sites and directly stored at one PPC source site, in the Golf MapObjBall code unit. The #240 owner is already tracing that exact store site's source register. In the separate cache-update chain, #240 has STATIC near-callee potential `fn_80299ACC` and `fn_80299C20` receiver flow into `fn_80299C70` but has NOT proven the *caller-provided* `r3` receiver object or any actual executed call.

The existing #219 two-hop code study supports two distinct OUTER upstream candidates:
- `fn_8029B43C` (`RPGolSimulateManager` unit) → `fn_80299ACC` (`RPGolMapObjBall` unit) → `fn_80299C70`.
- `fn_8029A204` (`RPGolMapObjBall` unit) → `fn_80299C20` (same unit) → `fn_80299C70`.

This independent script investigates ONLY how the **OUTER** functions appear to prepare GPR `r3` for their inner calls, and nothing about the known single global-slot `stw` site. It does not edit #219, #240, #246/#247/#249/#253, the separate CFG agent's inner-caller work, S001 watchers, ROMs or Dolphin.

## API / limitations

`scripts/review_p0_outer_receiver_argument_source.py` exports `inspect_upstream(read_u32)`. The supplied callback MUST be created by the S002 owner from **already independently attested** original RSPE01 Rev1 source words and original-bank SHA or equivalent approved provenance. The helper itself has **no** file/JSON/bank readers and cannot authenticate the callback; this is deliberately enforced in its report.

For each published outer source entry it examines a fixed **0x100-byte bounded code SEARCH window**; `0x100` is NOT claimed to be the verified function size. The actual inner call can lie outside this window. A source-local `bl` into the exact previously identified inner entry is required; zero or multiple matches abstain. With exactly one syntactic match, a strict 0x40-byte nearest-pre-call search reports only the category of `mr r3,rX`, `addi/addis r3` or `lwz/lbz/lhz r3` GPR candidate, an entry-relative source-code offset and branch/call hazard booleans. Unknown X-form potentially writing `r3` is a hazard, not a known producer. `b/bc/blr/bctr` and intervening calls count as control-transfer hazards.

**Critical:** This is *syntactic only*. Neither the compiler function extent, all-path reaching definition, object identity, actual receiver argument at runtime, game physics, rendered projectile, frame linkage nor whether cache writer executes during wedge are proven. With no hardware bridge/guest-frame attestation, these fields remain FALSE, no training or publication.

## Integration requested from #219/#240 source owners

After reviewing the helper and its fabricated tests, a source owner may call `inspect_upstream(verified_two_bank_source_reader.u32)` on an **existing, SHA-verified** Rev1 pair. Only print the categorical report. A missing source call within 0x100 is an interesting *bounded negative*, never proof that the upstream call does not exist. If source owner's exact call site lies farther away, inspect its public source-symbol function extent before altering the window rather than guessing.

No human Phase labels are consumed or believed. No original archive, pointers, floats, hashes, ROM words or path data are included. All native validation and training gates remain source-owner/S000 decisions.

## Synthetic CI acceptance

`tests/test_p0_outer_receiver_argument_source.py`: 15 fabricated cases covering both known code entry and BL targets, absent/duplicate/unlinked/wrong target branches, control transfers before and after candidate r3 source, intervening call, source operand override, unsupported register definition, strict invalid-word rejection, negative and AA branch decode, schema/privacy. Win/Linux native-free Actions runs; **no native game bytes are needed in CI**.
