# P0 constructor-return register write-effect review

**Source owner:** #240. **Exact review base:** `1d250d3bcd8d1b9ea2b78d6279c6a2713fe8e953`. This is a separate, DRAFT code-review child and is NOT a replacement or merge of owner code.

The original 14-bank SHA/Rev1-gated real W5/W6/W7 operator run has independently identified `fn_8029AB78` as a constructor candidate: input r3 copied into r31 near entry, direct call to `fn_80290A48` MapObjBase ctor, one literal `blr` in the 0x21C source symbol, and final supported `mr r3,r31` near that return. This indicates an initial-to-return register candidate, but does NOT establish all-path receiver preservation, dynamic pointer identity, or executed global slot assignment.

## Specific syntax bug and conservative patch

`_r3_assignment_class` originally failed to recognize some PowerPC instructions that write base **rA=r3** even if rT/rS != 3. In particular lwzu/lbzu/lhzu/lhau (op 33/35/41/43) and store-update or floating-memory update variants (op 37/39/45/49/51/53/55). A `mr r3,r31` followed by `stwu r0,4(r3)` would no longer have that preceding `mr` as the latest r3 definition; the old bounded parser could accidentally retain it. Also canonical `mr r4,r3` reads r3 and should not be reported as an unknown r3 write, and `stmw r3,...` is a store, not a GPR assignment. Some op 12/13 immediate integer writers were omitted.

Patch returns only **categorical**, syntactic last-register-write classes, conservatively marks unknown values, and preserves `complete_r3_reaching_definition_at_exit_verified=false`. Five additional adversarial native-free test cases target those behaviors and source-only negative controls. Both inherited public nullguard tests and new constructor tests run on Windows and Ubuntu CI.

## Limits

No new source scan is needed to validate this synthetic fix, and no new private snapshot or human golf shot is requested. The source caller at `RPGolMapObjBall+0x3080` already points to `fn_8029AB78`; this PR does not repeat #262 target mapping, #254 inner receiver CFG diagnostics, #263 outer r4/r30 provenance, or #240 constructor semantics ownership.

No offline real-source result is changed by the fabricated tests alone. In particular the original source-confirmed nearest `mr r3,r31` may remain unchanged after owner review; do not claim class equality over **all paths**, guest-frame truth, physical XYZ, velocity, impact, score, renderer identity, model training, or permission to publish. Stay DRAFT pending S002/S000 owner review.
