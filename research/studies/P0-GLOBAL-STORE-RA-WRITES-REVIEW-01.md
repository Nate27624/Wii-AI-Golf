# P0 support — conservative RA-writing PowerPC correction for global-slot store

## Owner and scope

Source #240 owns the bounded PPC CFG of its one source-global-pointer-slot stw at public MapObjBall+0x3084. This child review stacks on **exact #240 code** `0fd7505c2dc0e105240e63b4246dd83fe19152a2`, changes only the **r3 write-effect detector** in the source-only helper and its targeted fabricated tests, and adds dedicated cross-platform CI. Do not self-merge or run real private captures from this review branch without S002 owner review.

## Reproducible bug

At source helper `_r3_written`, opcodes 20 (rlwimi), 21 (rlwinm), 23 (rlwnm), and logical immediate opcodes 24..29 (ori/oris/xori/xoris/andi./andis.) write **rA**, bits 16..20; bits 21..25 name source rS. Previous logic ignored opcode 24 entirely, did not explicitly check rA for those instructions, and used a generic rT-like test on others.

Synthetic `addi r3,r0,1` followed by `ori r3,r4,0` could previously be reported as `addi_literal_nonzero` still reaching the global pointer stw. But the `ori` wrote r3 afterward; this last-r3 candidate was incorrectly attributed. Conversely `xori r4,r3,1` **reads** r3 and does NOT overwrite it. The previous generic rS==3 fallback could produce a false overwrite candidate for that shape.

## Narrow correction

Explicitly distinguish rA destination for precisely these nine primary opcodes and return conservative `ra_form_r3_assignment_unknown` if rA==3; return no write if rA!=3, even if source rS==3. Do NOT claim a computed constant or runtime pointer. Four adversarial tests cover logical/rotate destinations, source-only uses and conditional branch bypass. Existing local-window CFG, public source offsets, output privacy and all flags for whole-function proof, active execution, real ball, physics and model training remain FALSE.

This is syntactic code-review hardening, **not new native evidence**, not a fifth-object creation proof and not a replacement for #240 / #254 / #255's separate provenance work.
