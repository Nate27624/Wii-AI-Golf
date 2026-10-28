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
## Full copy-paste Windows PowerShell procedure (only B0 code, no Dolphin)

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $root = 'D:\Projects\Wii Golf AI'
    $repo = Join-Path $root 'Wii-AI-Golf'
    $private = Join-Path $root 'Wii-AI-Golf-Data\ball-study-20261027-212633'
    $branch = 'agent/research/golf-source-object-windows-private-20261027'
    if (-not (Test-Path -LiteralPath (Join-Path $private 'checkpoint-manifest-PRIVATE.json') -PathType Leaf)) {
        throw 'Original private B0 checkpoint is missing'
    }
    git -C $repo fetch origin "refs/heads/$($branch):refs/remotes/origin/$($branch)"
    if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
    $head = (git -C $repo rev-parse "origin/$branch").Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve exact branch head' }
    $work = Join-Path $root "Wii-AI-Golf-Effect-Writers-$($head.Substring(0,8))"
    if (Test-Path -LiteralPath $work) {
        $actual = (git -C $work rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $actual -ne $head) {
            throw 'Existing worktree is not the approved exact source revision'
        }
    } else {
        git -C $repo worktree add --detach $work "origin/$branch"
        if ($LASTEXITCODE -ne 0) { throw 'Worktree checkout failed' }
    }
    py -m unittest discover -s "$work\tests" -p 'test_golf_effect_source_writers_private.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Source-level synthetic tests failed' }
    $raw = @(py -I "$work\scripts\audit_golf_effect_source_writers_private.py" --private-root "$private")
    if ($LASTEXITCODE -ne 0) { throw 'Preserved B0 PPC scan failed' }
    $result = ($raw -join [Environment]::NewLine) | ConvertFrom-Json

    'SOURCE-BOUNDED PPC COUNTS'
    $result.source_units |
        Select-Object source_unit, matched_dform_count, paired_field_write_count, paired_field_read_count, effect_pointer_offset_hits |
        Format-Table -AutoSize
    foreach ($unit in $result.source_units) {
        "[$($unit.source_unit)] first candidate stores at +0x78 / +0x7C:"
        @($unit.literal_hits | Where-Object {
            $_.kind -eq 'write' -and $_.offset -in @('+0x078', '+0x07C')
        } | Select-Object -First 12) |
            Select-Object pc, offset, mnemonic, base_register, value_register |
            Format-Table -AutoSize
        $shown = 0
        foreach ($entry in $unit.selected_source_contexts) {
            if ($entry.target.kind -eq 'write' -and
                $entry.target.offset -in @('+0x078', '+0x07C')) {
                "Static source context for $($entry.target.pc)"
                $entry.nearby_static_code_only |
                    Select-Object pc, word, approximate_disassembly |
                    Format-Table -AutoSize
                $shown++
                if ($shown -ge 2) { break }
            }
        }
    }
}
~~~

Only return PPC CODE-site tables and small neighborhoods; do not paste native RAM dumps or source private paths. Textual static code offset matches never establish effect receiver identity.

## Real operator read/write PPC results (2026-10-28)

The operator ran the source scanner against existing immutable B0 source-linked native code, and all 5 synthetic tests passed. Exact source-unit summary:

| Compilation unit | D-form target hits | +0x78/+0x7C writes | +0x78/+0x7C reads | +0x94/+0x98/+0x9C hits |
| --- | ---: | ---: | ---: | ---: |
| RPGolFieldManager.cpp | 69 | 12 | 10 | 47 |
| RPGolDrawManager.cpp | 3 | 0 | 0 | 3 |
| RPGolMapObjBall.cpp | 102 | 31 | 19 | 52 |

Two exact code sequences (not guesses) deserve narrower receiver analysis:

- FieldManager at 0x80290E74 calls PPC helper 0x802A3758. At 0x80290E78 it executes `lwz r3,+0x04(r29)` and stores stack f32 values +0x10,+0x14,+0x18 into the destination `stfs f0,+0x78(r3)` (0x80290E80), `+0x7C(r3)` (0x80290E88), and `+0x80(r3)` (0x80290E90). This is consistent with copying a 3-component float vector to a CHILD/INDIRECT recipient, not source-proven RPSysEffect object.
- MapObjBall at 0x802977FC reads `lbz r0,+0x50(r3)`, at 0x8029780C writes `stb r4,+0x5C(r3)`, then executes `stfs f0,+0x78/+0x7C/+0x80(r3)` at 0x80297810/14/18, and another `stfs f0,+0x1A0/+0x1A4/+0x1A8(r3)` at 0x8029781C/20/24. All six float slots are assigned from the same f0 on the observed path, consistent with an initialization/reset. This does not prove source-selected active ball or RPSysEffect receiver.
- DrawManager has no direct D-form stores at +0x78/+0x7C in its mapped .text. This is not evidence it never calls a helper or executes an indexed/copy write.

### Independent Rev1 FieldManager C++ data-layout documentation

Public `kiwi515/ogws_info` original reverse-engineered Rev1 header (https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolFieldManager.h) identifies `RPGolFieldManager` +0x94 `mMapPlayerEff` as RPSysEffect*, +0x98 `mMapShotLineEff` as RPSysEffect*, and +0x9C `mMapBallEff` as RPSysEffect*. It separately identifies FieldManager +0x78 `mMapTreesObj` (RPGolMapObjBase*) and +0x7C `mShowGreenSlope` (bool). **These are offsets within the manager**, NOT the offset within its pointed-to effect object. In particular the FieldManager code sequence at 0x80290E80 targets r3 loaded from +4(r29), so calling it a direct write to the manager's +0x78 is an object-identity error. This secondary C++ layout reference strengthens the origin of the three effect observation window labels but still requires correlating to Rev1 runtime objects, as original B0 data and 0x90 alias layouts are distinct evidence.

### New narrow receiver-source audit (no live action)

Additional script `scripts/audit_golf_effect_vector_receiver_private.py` (with `tests/test_golf_effect_vector_receiver_private.py`) checks exact PPC instruction signatures for the two observed vector-store chains, searches only up to 0x240 preceding bytes in the same linked source unit for plausible `stwu r1,-N(r1)` and `mr r29,r3` instructions, and returns only up to 0xBC narrow code context around each writer. It intentionally does not claim function boundaries, dynamic control-flow or true RPSysEffect ownership from prologue proximity. It reuses existing private B0 SHA and selected-source gates and never launches Dolphin.

Run against the same original saved private B0 session; no new screenshots or game captures are necessary. Review the printed candidate function prologue PCs and exact code disassembly before any pointer-to-effect entry attribution. Training, physical ball XYZ, velocity, meter power and game score remain unverified.
