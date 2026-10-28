# S002 P0: Rev1 FieldManager pin/start store candidates — bounded PPC provenance

**No Dolphin, controller, network, model training, or RAM writes.** This draft PR stacks on #224→#223, requires #223 exact preserved B0 and human-airborne private manifest/hash/source scene/player/ball validation first, and examines only source instructions in the public `RPGolFieldManager.cpp` `.text` unit 0x80290B44..0x80294184. No native instruction words, vectors, private hashes, dynamic heap pointers or filesystem paths are emitted.

## Real operator evidence (the precursor)

User ran SHA-gated source scan against original B0 and operator-attested **same-paused-frame MEM1/MEM2** human-airborne export: B0+flight hashes and source unit equality all PASS; four known pin/start getter source instructions PASS. 15 total `stw` displacement +0x44 or +0x50; nine are stack `r1` base, remaining six source-relative sites: +0x2CCC, +0x2CF0, +0x2D14, +0x2EA8, +0x2ECC, +0x2EF4. Source store matches are **not proof the destination receiver is the actual FieldManager**, and cannot indicate which was executed during the shot.

## New reader and question

`scripts/audit_p0_field_pin_start_store_provenance_private.py` first delegates to #223 original `run_local` to verify BOTH preserved native 24/64MiB banks, manifests, selected player/hole and Rev1 scene/PPC source chain. It then byte-compares FieldManager source code in both native MEM1 images and requires **four exact getter** plus **six exact candidate-stw** syntactic code words. The script decodes only two source-relative ranges +0x2C80..+0x2D24 and +0x2E70..+0x2F04 (less than 100 instructions total), and produces a safe source-relative two-window opcode/register sketch. Each of six write candidates also shows nearest previous syntactically-recognized definition of its base and value registers in 0xC0 bytes and whether a branch lies in between.

**Critical boundary:** The nearest prior definition is linear source adjacency, NOT complete dataflow/SSA, control-flow, pointer owner, receiver type, callsite or executed guest instruction. Any unrecognized instruction could clobber the register. Branch hazard flag means nearby definitions are especially unsafe to interpret. Source PC is intentionally emitted as **relative offset only**, never raw machine instruction bytes. Operator attestation distinguishes `operator_attested_mem1_mem2_same_paused_frame=true` from `machine_frame_index_independently_verified=false`.

## Review ownership and next observation

S002 #219 traces the real Rev1 code/caller path. Compare two site clusters, identify basic-block entries, prologue and `mr r31,r3` (if any), and prove whether candidate register is the actual FieldManager with source-typed call/constructor evidence. A `stw` through `r3` or `r31` with matching offset is only a candidate until that proof exists. Check target-choice inputs to explain why current-pin and start pointer *values* differ B0 vs flight while FieldManager and selected ball pointer values remain stable. Existing B0/B1/B2/B3 no-shot and three inactive slots provide source controls, but no same-boot B0 vs flight or physical XYZ proof. Training, physics XYZ, power and velocity remain FALSE.

Operator should run the source-only script from a fresh SHA-pinned detached Git worktree after focused CI. Run its one synthetic test module first; then `py -I scripts/audit_p0_field_pin_start_store_provenance_private.py --baseline ... --flight ...` against ORIGINAL private paths. Never upload native banks/ROM, numeric RAM, private manifests or absolute heap addresses. Keep report to source-relative register classes/boolean provenance only. No new Dolphin launch needed.
