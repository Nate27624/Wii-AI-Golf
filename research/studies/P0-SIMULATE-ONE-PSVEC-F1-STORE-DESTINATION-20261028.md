# P0 geometry source: one direct f1 store destination

## Why just this source site?

Operator's exact reviewed PR #266 original private B0 Rev1 study (`84a444800db0f0527a9195914911de5a4ffed543`) passed source/SHA before-and-after and 17/17 fabricated regressions. Of **18 exact direct `PSVECSquareDistance` BLs** in published Golf object units, **17** had recognized local source for both r3/r4 vector args, and **only ONE** had `F1_STFS_SOURCE_STORE_SYNTAX` immediately following the geometry BL before any recognized barrier or FPR op. The other 17 were categorized as floating arithmetic/move *unresolved*, not negative. The unique candidate was **`RPGolSimulateManager.cpp+0x00388`** with source-local `r3 MR_FROM_r27`, `r4 LOAD_GPR_FROM_BASE_r4`. Those are code syntax hints, not pointer identities.

The discriminating P0 next question is **whether this direct `stfs f1` targets a stack-like slot (r1 base), or a static field displacement from a non-stack GPR**, and which exact store-base register is written. A stack-relative temporary should be deprioritized as a persistent result variable; a nonstack store *may* merit bounded source-member tracing. Either observation cannot prove an on-screen result or ball-to-target distance.

## New-only implementation

`scripts/audit_p0_simulate_distance_f1_store_private.py` analyzes the **ONE** exact fixed public Rev1 source code site. It reuses #219/#266 original private B0 **manifest/SHA before and after**, public 832-unit Rev1 source index, exact BL to `0x800E86D0` (public `PSVECSquareDistance`), and the previous #266 first-event source logic. It then decodes the exact PPC D-form `stfs f1,d(rA)` **base GPR rA**, **signed immediate source field offset**, and public source-unit-relative site offset. It optionally reports nearest pre-call 0x80-byte syntactic rA write after last branch/call (conservatively accounting for `lmw`, RA destination, and update form). It never dereferences the base register or reads a dynamic heap object. No raw PPC word, memory bytes, original bank hash/path, vector/float value, guest heap address, source string, or private pointer leaves the operator machine.

`tests/test_p0_simulate_distance_f1_store_private.py` adds fabricated regressions: stack vs nonstack vs zero-base, signed field offset, rA clobber, branch barrier, false-call/refuse, original-B0 guard, sanitized output and Python isolated invocation. Focused Windows/Ubuntu CI runs both these tests and parent #266's 17 tests. This is a separate **child of #266** and does not modify the authoritative #266 source, #256 result/text wrapper, #240 global-object constructor, #254 receiver CFG, #263 upstream static receiver or Dolphin controller.

## Interpretation and strict stop condition

The output is a single source-only JSON. If `source_store_base_class=STACK_POINTER_R1_SYNTAX`, deprioritize that direct store as a *persistent* result field (other 17 FPR sites remain unresolved). If `NONSTACK_GPR_BASE_UNTYPED`, owner should trace the GPR to a source-typed object using a bounded CFG and independently establish that this `stfs` is on a relevant runtime path, **before any real-time or physical-distance claim**. If source first-event differs, fail closed; do not force a result.

**No new Dolphin launch, shot, hole 2, controller input, runtime bank scan, publication, model training, or automatic merge.** Current original B0 is an idle baseline, original seven numbered phases are first-hole-only with uncertain labels, and no source-backed ball-to-pin distance, world XYZ, velocity, power, collision, scoring, visual guest-frame link or training permission has been verified. Keep draft until source-owner review and full repository policy gates.
