# S002-MEM1-CHECKPOINT-01 — private paused-MEM1 source-gated differences

**Owner:** S002 memory; cross-owner S001 (Felk native dump capability),
S000 (schema/CLI), S003 (event-linked modeling). **Status:** offline
comparator implemented on a draft PR, no operator export performed or
model training permitted. Stacked alongside the docs-only strategy PR #148,
not on top of its branch. No raw uploads, new launcher or network publisher.

## Why

The known first-level child RAM survey was exhausted across 28 pointer-shaped
children with no aim-enriched signal; `RPGolMain +0x74` and three child's
changing words behave like background timing. We need broader candidate
discovery across player/club/ball object families without 6–18-frame RPC
reads of every tiny child or more speed-only golf swings.

## VERIFIED source implementation — Felk fork

Inspected public upstream `Felk/dolphin`:

- `Source/Core/DolphinQt/Debugger/MemoryWidget.cpp`: Memory debugger
  menu **Export → Dump MRAM** calls
  `DumpArray(File::GetUserPath(F_MEM1DUMP_IDX), ...)` and **Export →
  Dump ExRAM** uses `F_MEM2DUMP_IDX`.
- In the same source, `DumpArray` uses `File::IOFile(filename, "wb")`.
  **Every subsequent export may overwrite the same raw file.** Backup
  each checkpoint to a uniquely named PRIVATE path immediately after export.
- `Source/Core/Common/CommonPaths.h` defines
  `MEM1_DUMP "mem1.raw"` and `MEM2_DUMP "mem2.raw"`; `FileUtil.cpp`
  puts them in Dolphin's configured `D_DUMP_IDX` directory.
- The installed Felk Python Scripting Preview 4 UI, exact dump byte count
  and whether GUI pause works **have not yet been confirmed on operator
  Windows**. We must not assert the installed binary shows this feature
  merely because checked source does.

WiiBrew maps cached MEM1 `0x80000000..0x817FFFFF` (24 MiB) and cached
MEM2 `0x90000000..0x93FFFFFF` (64 MiB); Dolphin can back MEM1 with
32 MiB of emulated host allocation. The offline parser accepts **exactly
24 or 32 MiB** native raw files, always analyzes only the first 24 MiB,
and explicitly reports ignored 8 MiB if the export is 32 MiB.
It fails closed on any other size, archive/savestate format or game ID.

Do **NOT** export via 24MiB of `FelkRPC.memory.read_bytes`: the
frame-yielding Python bridge is too slow and might stall when paused.
Do not call `emulation.pause`/`emulation.resume` over its same
frame-polled socket while paused (documented deadlock risk).

## Stage 0 — safe capability audit (NO controller action required)

1. Inspect **the existing installed Felk Dolphin** debugger Memory view.
   Look for its actual `Export → Dump MRAM` action. If not present,
   report that; don't install a different Dolphin version, modify its
   bridge, or infer another UI location.
2. Only if the game is already in a user-approved canonical first-ball
   Hitting the Green session, pause **via Dolphin's own GUI** (not RPC).
   Trigger one `Dump MRAM`. Determine the actual configured Dolphin
   `Dump` path and inspect **only** the filename `mem1.raw`, byte
   length, timestamp and whether the game remains paused. Stop if any
   unexpected behavior. No raw RAM should be pasted into GitHub/ChatGPT.
3. The first dump must be copied to a unique, ignored private sibling
   location before taking another. Full baseline B0–B3 below should
   not begin until this capability is verified and S001/S002 approve
   use of the canonical fresh-boot process.

Example Windows shell (change `$source` to the **actual** full private
path detected in your existing Dolphin installation; no guessed default):

```powershell
$source = Read-Host "Exact private Dolphin Dump\mem1.raw path"
$source = $source.Trim('"')
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
    throw "No native MEM1 export found"
}
$size = (Get-Item -LiteralPath $source).Length
if ($size -notin @((24MB), (32MB))) {
    throw "Unexpected RAM export size. Stop and report size only."
}
Write-Output "Native MEM1 export present; size_bytes=$size"
```

No copy/rename/delete of the only native dump until its location and
size are confirmed.

## Stage 1 — preregistered 4-checkpoint controlled baseline

One approved, source-identical first-ball boot; **zero shots** and
no controller program changes. At each stage pause with GUI, export
MRAM once, immediately COPY `mem1.raw` into unique files under
`Wii-AI-Golf-Data/mem1-checkpoints` named `B0.raw` through
`B3.raw` and verify copied file size and SHA256 against original.
Do not request a second boot or load new savestates between stages.
Record human action annotations separately, NOT inside RAM files.

- **B0:** ready at tee, all controls still.
- **B1:** after an idle interval with no controls.
- **B2:** WASD pointer-only movement (human confirms visible change);
  never press A or trigger swing.
- **B3:** after releasing WASD/returning to stillness.

A B2-only changed page is *not* automatically a camera, aim, club, or
power variable. B0/B1 drift pages are explicit negative controls;
single sequential checkpoint sets are NOT independent sessions.

## Stage 2 — private offline audit

After the four source-verified plain RAM dumps exist:

```powershell
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-MEM1-Test"
$private = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\mem1-checkpoints"

py "$work\scripts\audit_golf_mem1_checkpoints.py" `
  --b0 "$private\B0.raw" --b1 "$private\B1.raw" `
  --b2 "$private\B2.raw" --b3 "$private\B3.raw" `
  --top-pages 24
```

The source-gated parser requires all four dumps have the exact
`RSPE01` Rev1 header, golf config mode 4, stable manager static-slot
pointer and current scene ID5, source scene owner ID5/backlink manager,
sport ID2, and stable scene+0x9C RAM-shaped candidate pointer in MEM1.
If these gates don't hold, it fails; no guessed offset dereference.
It emits only aggregate 4KiB page-relative indices and word
comparison counts, plus explicit unverified fields. It does NOT
print source file names, paths, RAM values, code bytes, live absolute
heap pointers or full memory dumps. No automatic Git publication
until S000 approves a typed summary schema.

**Analysis method:** scan static MEM1 pages, compare big-endian 32-bit
units across B0 vs B1 idle drift, B1 vs B2 pointer interval,
B2 vs B3 post-pointer interval; count B2-only values where
B0=B1=B3 and persistent post-pointer words where B0=B1 and B2=B3.
Prioritize *hypotheses*, not confirmed source members. No raw values
are retained by the report.

**Next after successful offline audit:** S002 reconciles coarse changed
page indices to source-backed RPGolMain/Player/PlayerManager code and
runtime pointer-graph provenance; S001 verifies any write-watchpoint
under a paused debug session, then adds tiny same-shot bridge-thread
observations ONLY after timing/observer-effect gates. S003 cannot
train on these page counts or treat off-green 100ft penalty as carry.

## Stop/validation criteria

- Missing native Export control, unsupported dump length, mismatched
  header/mode/scene or pointers, heap relocation between checkpoints,
  game switching, unpaused capture, failed SHA256 copy, or any
  unexpected Dolphin behavior → **stop without publishing**.
- Only synthetic snapshots are committed. Private raw memory stays
  in ignored sibling Data folder, never GitHub, even if user
  explicitly enables the existing sanitized-results publisher.
- Require targeted and full Windows tests and S001/S002/S000
  owner review before merging or encouraging four new captures.
- Source links:
  https://github.com/Felk/dolphin/blob/master/Source/Core/DolphinQt/Debugger/MemoryWidget.cpp
  https://github.com/Felk/dolphin/blob/master/Source/Core/Common/CommonPaths.h
  https://www.wiibrew.org/wiki/Memory_map
  https://github.com/doldecomp/ogws
