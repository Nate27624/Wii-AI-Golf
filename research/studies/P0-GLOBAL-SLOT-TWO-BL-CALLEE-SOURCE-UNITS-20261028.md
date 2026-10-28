# S002 P0 — Two public source callee units at global-slot writer

## Distinct source question

S002 #240's *real* original seven-bank investigation has source-backed evidence that a **fifth global ball-like object** differs from all 4 player-roster ball objects 7/7 and its candidate translation equals selected cache CC in W5/W6/W7. The **single direct global r13-slot store** in six Golf source units is `RPGolMapObjBall` +0x3084, PPC Rev1 PC 0x8029A05C, `stw r3, disp(r13)`.

Source review found a **preceding plain blr** at +0x305C, a positive literal loaded to r3 at +0x3068, `bl` at +0x3070, conditional `bc` to store at +0x3078, optional `bl` at +0x3080, and store at +0x3084. An earlier CFG starting *before* the blr falsely framed the store as unreachable from that start. **Hypothesis**: one call could allocate and an optional one initialize an object, with r3 stored afterward. Neither callee's public owner/function, entry, value, actual runtime execution or constructor role has been established.

## Contribution (new-only source-unit mapping)

`scripts/audit_p0_global_store_two_bl_public_units_private.py` does **not repeat #240 CFG**, and does not implement another arbitrary memory search. It uses #219's published **832-unit Rev1 compiled text object source index** `research/source_maps/RSPE01_01_public_text_units.json` and original private **B0** SHA-gated reader. It checks the exact return/literal/two BL/branch-to-store/global r13 load+store forms and source field anchor, then resolves **each BL destination** to the public compiled **source object unit + relative offset**, or `unknown` if not uniquely mapped. It intentionally refuses to label a function entry, allocation routine, constructor, dynamic receiver, physics ball, or shot impact.

The Python script accepts the original local B0 session via `--baseline`, default sibling data root from the trusted checkout's path; the user can run `py -I scripts/audit_p0_global_store_two_bl_public_units_private.py --baseline <PRIVATE-ORIGINAL-B0-FOLDER>`. It uses #219's original B0 `checkpoint-manifest-PRIVATE.json` and hash identity **before and after** fixed-code reads. No Dolphin, controller, game-memory write, new capture, network, ROM upload or GitHub publication. Output includes only source code PCs and public source unit-relative offsets: no PPC words, RAM bytes, heap addresses, ball floats or bank SHA.

**Key caveat**: `doldecomp/ogws` object-file source splits only map *compiled units*. They do not name exact target C++ functions and cannot establish actual `operator new`, constructor, register reaching-definition, or executed call path. This source lookup can suggest which source owner should inspect the target next. The original B0 is an idle baseline, not a verified ball-flight frame. All seven human shot phase labels remain unverified, all past shots hole 1 only, and no training approvals.

## Test/approval gate

New-only 13 fabricated adversarial tests and Windows+Ubuntu CI. Preserve existing source #219 ownership, source-global #240 writer CFG, receiver #254/#255, UI result #256, and registry #205. Draft until focused CI, native owner review, operator original private B0 run and full suite. Do not merge automatically or ask operator for new shots. If B0 code check fails, abstain rather than weakening exact instructions.

After the real result, #219/#240 owners can compare both destination public source units to known allocation and initialization functions in the published source index, *without* inventing names from proximity.
