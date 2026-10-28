# P0 — Label-agnostic source-context graph for seven existing captures

**Status:** draft / offline / no model training. Built after the operator warned that one or more of the original human screenshot→capture phase labels may have been wrong. No new snapshots or Dolphin actions are authorized.

## Narrow, independent question

Can we analyze **all seven original numbered private native MEM1/MEM2 snapshot pairs without using the human phase labels as ground truth?**

The earlier #231 checks only selected human-reported pairs, including D1→D2 and W5→W6→W7. #232/#233 test wedge endpoint ordering, #235 scans player record offsets, #240 investigates a distinct source-global ball; those owners' work is untouched.

This study instead makes a source/geometry-equivalence graph of all **21 unordered capture-number pairs**. Numbers are immutable filenames and MUST NOT be interpreted as a frame index, temporal order, shot identity or proven same-boot identity. Any perceived "ascending" number is metadata, not gameplay timing.

## Read-only inputs

Reuse #231 `_check_archive` for original ignored `Wii-AI-Golf-Data/captures/p0-new-cohort-*-PRIVATE` archive (exact 14 bank SHA256 + sizes), `_get` for RSPE01 Rev1 selected scene/player/ball/pin/tee/Config selection. Source owner identity includes record+0x88 ball, selected player, field manager, Config, source pin and start; require valid source+selfref chain. Rehash ALL original banks after each mmap closes, reject any drift.

The graph uses only original source-selected ball+0x30, caches +0xCC/+0xF0/+0xFC, source pin/start bits. It groups snapshots sharing exactly identical source context, including owner pointers, selected slot/hole, stable current geometry and selection fields. A context match permits **bitwise comparison** of these candidates; it cannot prove same shot, correct screenshot mapping, real ball flight, physics dynamics, or time order. Across different source contexts the tool emits null/ABSTAIN for vector changes.

Per-source node output: assigned anonymous context group and 0..3 equality-component counts (selected current vs its own start/CC, CC vs start). Per unordered pair: context match, current/cache changed 0..3 or null. No private pointers, hashes, floats, raw words, dynamic addresses, file paths or human names/labels are emitted.

## Windows PowerShell 5.1 operator command (after owner review)

Use clean **SHA-pinned** detached worktree of this PR to prevent conflicting agents from changing the checkout. From that worktree:

```powershell
& .\scripts\Invoke-P0SevenLabelFreeGraph.ps1 -Archive 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-...-PRIVATE'
```

Replace the archive example with the actual existing canonical folder. The wrapper checks manifest kind, runs fabricated synthetic tests, then calls the read-only Python source interpreter. An alternate `seven-dump-inventory-*-PRIVATE` archive has a different manifest kind; **do not rewrite or rename originals** to force it to pass. No Dolphin is launched.

## Decision logic and scientific stop rules

- If a pair matches source context but selected current differs 3/3 and cache stays equal 3/3, that is evidence of different source-selected memory values across two numbered captures, **NOT** proof of ball movement or cache endpoint.
- If source current equals start in capture 1 while its original label said "airborne," the two competing explanations remain phase label mismatch OR selected-versus-visible-actor/timing difference. This tool does not adjudicate them.
- Changing capture labels only permutes pair identifiers; all unordered equality/count relations are unchanged.
- Real native 7-pair run remains **PENDING** until Windows operator executes reviewed SHA. Hosted tests are synthetic only. No world XYZ, velocity, impact, power, score, renderer identity, frame/shot provenance, training or publication approval.
