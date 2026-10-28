# S002 — Source-level effect-field writer triage (read-only Rev1 PPC)

## Existing real data

The operator's original human-confirmed 45-observed-frame-A-lead golf shot has 3 PRE, 2 POST, 3 SETTLED observations and 8 stable PRE-to-SETTLED changed words. The owner re-ran PR #197 source-relative alias auditing against that actual shot: EffectSpacingVerified=True, FourPairsVerified=True, CandidateCount=8, PhysicalVariablesVerified=False. All eight changes were already present in BOTH POST samples. Exactly four candidate pairs at hypothetical effect slots 0–3 have within-slot fields +0x078 and +0x07C; the latter is pointer-like. All values came from overlapping minimap effect windows whose real base pointers are +0x90 apart throughout those eight observations. These are rendering/effect observations, NOT verified ball physics, shot power, or official distance.

## Public source map, actually inspected

The doldecomp/ogws config/RSPE01_01/splits.txt linker map is authoritative for compilation-unit .text bounds in RSPE01 Rev1. Its public src/Pack/RPSports/RPGolScene directory currently exposes only RPGolResourceManager.cpp, not the three target C++ implementations. Therefore source types and field writers must be established from preserved Rev1 PPC text, not guessed from class names.

- RPGolFieldManager.cpp: 0x80290B44..0x80294184 — potential field/effect object pointer setup
- RPGolDrawManager.cpp: 0x80294184..0x8029528C — potential render/effect update
- RPGolMapObjBall.cpp: 0x80296FD8..0x8029B240 — potential link to real ball

These are candidate source AREAS, not observed function bodies or proven owners of any field.

## Implemented offline investigation

New scripts/audit_golf_effect_source_writers_private.py reuses the validated local source-selected record gate, private B0 MEM1/MEM2 manifest bank integrity, and bounded PPC decoder. It scans ONLY these three public .text ranges for D-form +0x78,+0x7C and +0x94,+0x98,+0x9C offsets, and prints source CODE instruction PCs, opcode, input/base registers, plus at most 24 nearby source windows/unit. It never outputs native runtime object addresses, RAW RAM, private values or bytes, never launches Dolphin, never issues a swing. Source +0x94/+0x98/+0x9C entries are only candidate acquisition pointer offsets; not source-proven effect pointer field types.

The source D-form decoder is deliberately conservative: simple literal PPC offset matches do not imply that a base register points to an effect object, do not establish any 0x90-byte native class size, and do not exhaust indexed writes, subobjects or library-copy routines. All owner/type/physics/training flags remain FALSE. Test file tests/test_golf_effect_source_writers_private.py includes signed displacement, wrong opcode, empty scan, exact bounds, overdense scan and no-ownership negative tests. Targeted Windows/Ubuntu CI integrated in .github/workflows/s002-golf-object-windows-offline.yml.

## Operator execution: NO Dolphin, only previously preserved private code

Use the already documented source code branch agent/research/golf-source-object-windows-private-20261027 and the immutable local private session Wii-AI-Golf-Data/ball-study-20261027-212633. Fetch the branch into a NEW isolated detached worktree with the current branch-head short SHA (never reset existing worktrees), run the synthetic test test_golf_effect_source_writers_private.py, then invoke:

    py -I <effect-worktree>/scripts/audit_golf_effect_source_writers_private.py --private-root <existing-private-B0-session>

Filter output to source_unit, matched_dform_count, paired_field_write_count, paired_field_read_count, effect_pointer_offset_hits, and up to 2 nearby 13-instruction source contexts for writes at +0x78/+0x7C per source unit. Do NOT paste raw B0 banks, runtime data values or full JSON source capture. Full PowerShell invocation is in operator chat.

## What to prove next

1. Exact true code PC and instruction type of each store to +0x78/+0x7C.
2. Trace that instruction's base register through same-function entry, loads and calls to an actual effect object receiver (or identify it as a different type); numeric displacement is not enough.
3. Cross-check candidate RPGolField offset loads +0x94/+0x98/+0x9C only if source pointer provenance supports it, then compare with effect-window stride without assuming a 0x90-byte C++ object.
4. Keep raw memory local, publication/training gates false, and avoid new live A-button trials. No full-bank scan is needed for this.

Source map: https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt