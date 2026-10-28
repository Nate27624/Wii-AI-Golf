# Cross-phase source integrity patch for draft #240

This review branch is stacked on #240 at its original reviewed head, not on main. It addresses three independent fail-closed limitations of the source-global/receiver comparison:

1. Verify the exact two caller BL targets and bounded input-r3 classification in **every** numbered phase, not just phase 1. Reject changed code.
2. Keep the resolved PPC r13 source-global slot **private** in memory and reject a changed displacement/slot across the seven phases, even when all source opcode classes remain the same.
3. Refuse within-shot driver/wedge comparisons when source PIN or START triplet contents change despite stable object pointers, or when GolfConfig BC/C0/C4 selectors change.

Fabricated regressions cover per-phase source-slot drift, changed secondary BL, changed receiver input class, changed pin, changed tee, changed Config selector and missing selector. Output remains ordinal/categorical and keeps every game-physics, renderer, frame-atomicity, velocity, power, and training flag false.

**Important separate outstanding gate:** the existing #230 reader, inherited by #240, checks original lengths and hash-before-vs-after but does **not** compare banks against the canonical #231 14-bank manifest. This patch does not represent that mismatch as solved. Do not interpret a private seven-pair result as the original preserved cohort until an independent exact canonical SHA manifest/attestation gate is added and reviewed by #231's owner. No native files or Dolphin execution are part of this patch.

No self-merge or publishing approval; route review to #240, #231 and S000 owners.
