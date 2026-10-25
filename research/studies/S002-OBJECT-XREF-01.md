# S002-OBJECT-XREF-01 — source-led golfer/player ownership investigation

Status: **offline source audit submitted for S002 review**. Stacked on existing S002 PR #122, not main. No real object, golfer member, or power field is yet identified.

## Research question

Does the Rev1 executable contain direct call relationships between RPGolMain, RPGolPlayerManager and RPGolPlayer code, and which conservatively labelled register-based memory operands deserve a human dataflow review?

All 28 previously surveyed pointer-shaped first-level children showed no aim-enriched changes in idle/WASD controls. The main-relative +0x074 word changed during idle; 17/17 within-stage increments matched elapsed emulator frames in one session. This strongly argues against treating it as an exclusive swing-power signal. Broad static scans are finished.

## Public source extents

Source: [doldecomp/ogws Rev1 splits](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt).

| Module | Executable code .text | Data .data |
| --- | --- | --- |
| RPGolMain | 0x8028E098..0x8028E900 | 0x803C7798..0x803C77C0 |
| RPGolPlayer | 0x8029E62C..0x802A2210 | 0x803C7CC8..0x803C7DD0 |
| RPGolPlayerManager | 0x802A2210..0x802A3560 | 0x803C7DD0..0x803C7DE0 |

These are whole compilation-unit ranges, not named function entrypoints, proven vtables, or a C++ class member layout. The DOL alone does not prove disc revision.

## Implemented instrument

New scripts/audit_golf_object_xrefs.py uses the existing PR #122 safe DOL section parser. It fails if any documented .text or .data range is unmapped or incorrectly typed. It reads no game memory and has no Dolphin, socket, network, GitHub publisher or controller integration.

- Direct relative PPC branch-with-link (bl) crossing between two documented units: a code control-flow edge, **not** proof of an object-to-object call or named function.
- Bounded PPC D-form loads/stores using r3 (the ABI first-argument/return register) with positive offset through +0x1FF: **unverified r3-base operand hints**, not confirmed C++ this/member offsets. The tool separately counts operands near another-unit bl instructions; it does not claim complete register dataflow.
- Aligned .data words pointing into public code intervals: possible code-pointer table entries, **not verified vtables or runtime class identities**.

It emits only bounded code callsite addresses and data-relative offsets, aggregate counts and explicit unverified flags. It never emits file paths, raw DOL instructions/bytes, private heap pointers or RAM values. Game/club/power verification fields remain false.

## Operator procedure — offline, no Dolphin launch

Requires your existing private extracted RSPE01 Rev1 main.dol, stored OUTSIDE all Git worktrees. Do not upload a ROM/DOL to ChatGPT, GitHub, or a public PR.

~~~powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Object-Xref-Study"
$dol  = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\symbols\main.dol"

git -C $repo fetch origin agent/research/golf-object-code-xrefs-s002
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
if (Test-Path $work) { throw "Worktree exists; do not overwrite" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }

Set-Location $work

py -m unittest discover -s tests -p "test_audit_golf_object_xrefs.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused object xref tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full offline suite failed; STOP" }

if (-not (Test-Path -LiteralPath $dol -PathType Leaf)) {
    throw "Expected private extracted Rev1 main.dol not found"
}
py scripts/audit_golf_object_xrefs.py --dol $dol
if ($LASTEXITCODE -ne 0) { throw "Source xref audit failed" }
~~~

The audit runs immediately and prints sanitized JSON. If the private DOL does not exist, stop; do not guess an ISO path or put a game image in Git. No emulator should be started for this study.

## Interpretation and stop rules

1. Require three correct documented code/data section mappings. Missing mapping: stop with a fixed redacted error.
2. If main-to-manager or manager-to-player bl edges appear, S002 must inspect named Rev1 map/callsites and calling register flow to validate the relationship. If zero calls, report zero without inventing a path.
3. A field offset derived solely from r3 or a .data code-pointer-shaped value is a hypothesis, never a verified golfer/club property. No arbitrary child dereference or immediate power field promotion.
4. No new idle/aim scans, off-green 100ft-as-carry regression, hidden uploads, background tasks, or automated swings.
5. After source-backed object member confirmation, S001 and S002 can propose a tiny 1–4 word same-bridge swing-time sampler with immutable A45/89-frame baseline, measured frame overhead and explicit operator opt-in. S003 should abstain from power training until a verified independent target exists.

## Coordination and validation status

- S002 #122: existing DOL source-audit owner; this PR stacks on its head and edits no existing files.
- S002 #129: one canonical live gameplay candidate collector; this study must not produce a competing live reader.
- S001 #112: preserves known-good A-button waveform; any future sampling requires same-shot frame anchors and nonperturbation.
- S000 #126: typed public schema approval before any new gameplay-related publication.
- S003 #123/#125: inference is gated on independently verified same-shot records.
- Complementary frame-counter specificity is already in S002 #138 and should not be duplicated here.

Twelve synthetic tests have been authored. They require operator focused/full Windows execution; no successful real-DOL audit or game power inference is claimed yet.
