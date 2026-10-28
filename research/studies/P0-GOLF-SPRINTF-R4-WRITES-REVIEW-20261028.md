# P0 review — Golf result `sprintf` source-register semantics

## Why this reviewer is separate from PR #256

The #256 source owner already verified on an original Rev1 B0 native dump that there are **14 direct PPC `sprintf` calls** in `RPGolScene_unsplit.o`. Their bounded 0x80-byte local *syntax-only* audit classified a nearby `r4` producer at each site as `addi_from_r31`, and observed **no FPR operations in the strictly postbarrier window**. Neither observation proves the format literal, rendered Hitting-the-Green distance, backing result variable or any runtime execution.

This reviewer makes **one precise correction**, without changing owner research scope or tracing `r31`: the helper's `_reg_def_class(word, r4)` only recognized `ori/oris` for logical RA-destination writers. A later `xori r4,rX,...`, `rlwinm r4,...`, `lmw r2,d(rX)`, or `stwu rX,d(r4)` could overwrite **r4** after an earlier `addi r4,r31,imm` and before a direct `sprintf`. Missing these writes may let an outdated source `addi_from_r31` appear as the **last syntactic definition**, making false static origin claims easier.

## Tight changed surface

The only modified owner script in this isolated child branch is `scripts/audit_p0_golf_sprintf_arg_origins_private.py` at its **register-write classification function**. The correction conservatively recognizes:

- PPC opcodes 20/21/23 and 24..29 write **rA**, including `rlwimi/rlwinm/rlwnm`, `ori/oris`, `xori/xoris`, `andi./andis.`;
- `lmw` opcode 46 writes the register interval `rT..r31` (so an `rT<=r4` load overwrites r4), while `stmw` opcode 47 is a *store* and does not;
- integer load-update 33/35/41/43 writes the base **rA** as well as loaded **rT**; update-form memory 37/39/45/49/51/53/55 writes base **rA**, including FPR memory operations;
- `addi/addis` with RA=0 is marked **literal zero base**, not a read from GPR r0. The known 14-site `addi_from_r31` spelling remains unchanged when no clobber is identified.

For uncertain instructions the classifier produces a **conservative syntactic overwrite category**, not a value, target register origin, signed/float number, branch dominance or genuine `sprintf` format string.

New **11 fabricated-only tests** are in `tests/test_p0_golf_sprintf_r4_write_review.py`, plus an independent Windows/Ubuntu workflow. Run the existing owner's 12 synthetics too. Source owner #256 retains the original reader, B0 native SHA gate, public 832-unit map and r31/format-pool provenance work. No new real native audit has run on this child; **do not repeat B0 merely to re-count direct sprintf**. Only rerun if reviewed changes materially alter a possible r4 producer at one of the 14 prior callsites. The full repository suite/source owner review and real data gate remain pending.

## Hard scientific limitations

These synthetic cases show the original bounded classifier could be fooled by particular PPC instructions, **not that such an overwrite exists at any real one of the 14 sites**. All previously reported source-only 14 sites, public PPC branch destinations, 0/14 nearby FPR activity, unproven format/string origin and human first-hole-only provenance remain as originally reported. No source-backed Hitting-the-Green numeric result, physical distance/units, ball world XYZ, velocity, contact, power, score or game-frame signal has been established. `training_approved=false` and `allowed_to_publish=false`. Do not merge the isolated review without #256 and #219 owners.
