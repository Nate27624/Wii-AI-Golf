# S002-FULL-STATE-DISCOVERY-01 — Golf memory-state reverse-engineering pivot

**Status:** preregistration and ownership proposal; NOT an implemented RAM dumper, approved live run or proven power decoder. Owner S002 (game-memory capture & candidate semantics), dependency S001 (single Felk Dolphin bridge/launcher and frame-timed controller), S000 (publication and CLI), S003 (identifiability/modeling).

## Why this replaces blind power sweeps

Verified operator 2026-10-25 evidence: two-cell scene-root probe yielded one stable source-plausible golf scene chain but no verified player/power type. Source-validated 16-child golfer windows [published result](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T034248Z-7c597d65.json) had 4 words changing identically in all idle and aim comparisons, not power. Smaller 4/8/4-child [A1](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T035723Z-4433fcfa.json), [B](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T035744Z-4bfa45ab.json), [A2](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T035802Z-3a4b445e.json) cut max read spans to 6/10/6 frames (NOT impact accuracy), still no aim-responsive signal. S002 null result in Issue #121 found candidate main +0x074 equals emulator-frame delta in 17/17 same-stage pairs including idle, strongly indicating frame-tied nuisance. All 28 first-level pointers were checked in separate batches; late child batches were static. Existing power-only sweeps gave roughly 75% human-read power; off-green 100ft is challenge penalty, NOT carry.

## Evidence-backed external tools

- Wii memory has 24 MiB MEM1 (cached 0x80000000..0x817FFFFF) and 64 MiB MEM2 (cached 0x90000000..0x93FFFFFF), with IOS reservations in MEM2; exclude uncached mirror duplication. Sources: https://www.wiibrew.org/wiki/Memory_map and https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/HW/Memmap.h
- Standard Dolphin Memory debugger supports memory dumps, watches and access breakpoints; implementation https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/DolphinQt/Debugger/MemoryViewWidget.cpp and https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/MemoryWatcher.h . Historical UI guide https://mariokartwii.com/showthread.php?tid=1141 . **Verify Felk Python Scripting Preview 4 capability and exact UI before giving operator instructions.** Do not upgrade/replace their working fork solely for a dump.
- Existing Felk mcp-dolphin bridge memory.read_bytes iterates per byte in Python, making repeated full 24MiB or 64MiB RPC reads too slow and invasive. Prefer paused native debugger export or vetted in-process bulk-copy; DON'T call emulation.pause through frame-polled RPC when it risks a paused-loop deadlock.
- Wii Sports Rev1 decomp: https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt . Source-code ranges RPGolMain 0x8028E098..0x8028E900, RPGolPlayer 0x8029E62C..0x802A2210, RPGolPlayerManager 0x802A2210..0x802A3560; player and player-manager static-data .sbss ranges 0x804BF8C8..0x804BF8D0 and 0x804BF8D0..0x804BF8D8. **These are NOT proven active player, club, or power fields.** Source unit names and PPC object-relative loads/stores serve as investigation leads.

## New two-plane acquisition architecture

1. **Discovery plane — occasional complete RAM checkpoints:** capture local, read-only MEM1 (and MEM2 only when necessary) at safe non-swing checkpoints with known memory base/length, game revision/mode, hole/scene, checkpoint label, frame marker if available, and full-file SHA256. Verify native debugger export on the actual Felk fork first; otherwise stop and build a reviewed read-only native bulk-snapshot mechanism rather than loop over bytes via RPC. Do not confuse a saved savestate with a plain RAM image.
2. **Analysis plane — offline whole-memory differentiation:** byte/page/32-bit u32 and f32 changes between matched checkpoints; filter timer/noise via stationary controls; prioritize small source-backed player/club/ball object graphs. Runtime instance relocation must not be confused with values changing. Use pointer chains, code/vtable provenance and write instruction PCs; visual correlation by itself cannot name a field.
3. **Event plane — tiny synchronized watchers:** after semantic candidate discovery, attach low-overhead, source-gated watches to SAME S001 frame-thread swing controller trace and record actual frame brackets or in-game write events. No second socket writer, bridge replacement, autonomous swing or other change to known A-lead45 behavior. Verify instrumentation impact against uninstrumented contact and observed power.

## First study: FULL-STATE-BASELINE-01 (no shot)

**Stage 0 capability check**: Check whether the operator's CURRENT Felk Dolphin fork supports read-only native debugger RAM dumps. Check actual MEM1 size and address base, what happens when paused, and whether it interferes with current single-session launcher. Do not request raw files over ChatGPT/GitHub. If supported, obtain operator approval of an exact command/UI walkthrough; otherwise report blocker with alternate local read-only native integration proposal.

**Stage 1 four checkpoints, one canonical first-ball session:**
- B0: known first-ball ready, no input.
- B1: after a fixed stationary/idle interval, same scene.
- B2: pointer-only WASD changes, no A and no swing; mark whether human visibly saw movement.
- B3: after release/return to stillness, same scene.

Each snapshot stored only under ignored sibling Wii-AI-Golf-Data directory. Preserve original savestate, never overwrite dump files, no controller reset or new games. At every step record version/mode/scene/hole independently and whether emulator pause/dump actually completed. If any mismatch or partial capture, stop. Repeated checkpoint dumps are *controls*, not independent randomized boots.

**Stage 2** offline differential result by MEM1 pages + candidate source-relative regions: baseline idle changes, aim changes, reversed/stable changes, unknown owners, object lifetimes and pointer changes. Retain raw binaries locally. **No guessed power fields.** Output only capped summary counts and validated relative offsets with S000 typed GitHub auto uploader, after schema review. Full binary memory and raw pointer values are never published.

**Stage 3** debugger write-access traces and source identification: verify actual player/club/ball object owner, the PPC instruction that writes each candidate, value representation and event specificity. Record confidence tier candidate / source-backed / runtime-observed / independent-boot replicated / gameplay-measured. Aim: versioned golf-state dictionary with scenario/hole/score, player pose, club pose, A/input phase, power, ball position/velocity, contact/green status, score/penalty and provenance; unknown items stay unknown.

## Model after state is identified

S003 may begin regression only once a real candidate power variable is same-shot frame-linked to controller input and at least three truly **different human-observed** power levels exist. With validated ball velocity/landing, add held-out clean-boot prediction and intervention checks; 100.0ft off-green is never physical carry. S004/S005 learn from verified game fields, not generic memory diffs.

## Safety and merging

Everything runtime-affecting is opt-in, reviewed by canonical owner and full Windows regression tested. No raw RAM, full binary dumps, ROM/savestates, user data, device identifiers or private pointers uploaded. GitHub receives ONLY schema-reviewed concise sanitized findings; prefer existing credential-based publisher. Do not start more ten-shot score-only sweeps or wide idle-first-level RAM scans; the next milestone is verified snapshot capability and source-semantic object ownership. This document does NOT claim live capture or tests.
