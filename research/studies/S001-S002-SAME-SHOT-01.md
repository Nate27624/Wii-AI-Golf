# S001/S002 SAME-SHOT-01 — Frozen V1 controller event manifest

**Status:** OFFLINE S000 implementation for S001 controller scheduler and S002 gameplay-memory acquisition. scripts/plan_swing_memory_events.py derives its phase indices from the EXISTING S001 probe_swing.build_probe forward waveform (12 neutral, 15 back, 20 forward, 30 follow, 12 released) and rejects any departure from the SHA256 of the operator's real A-lead45, speed1.0, backswing1.0 human-contact [trial 20261025T023456Z-15d1c97c12](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T023456Z-15d1c97c12.json). It does not send input, create a second waveform, open Dolphin or read RAM.

**Only commanded sample indices are known; they are NOT proof of game-applied A, elapsed emulator frame indices or actual ball contact.** Frame counters must be obtained in the same existing Felk frame coroutine. Separate 45-frame A lead was frame-observed but still not verified as game-registered button state.

| Phase | Zero-based sample indices inclusive | Proposed pre-dispatch memory markers | Intended A command |
| --- | --- | --- | --- |
| Neutral A-held | 0..11 | 0, 11 | pressed |
| Backswing | 12..26 | 12, 26 | pressed |
| Forward travel | 27..46 | 27, 46 | pressed |
| Neutral follow-through | 47..76 | 47, 76 | pressed |
| Button released | 77..88 | 77, 88 | released |

**S001 implementation request:** integrate bounded, opt-in read-only memory sampling INTO the existing patched Felk frame-thread swing handler, not a concurrently running RPC process. Initially sample S002-verified gameplay owner fields only, with background frame-counter controls retained separately. A read before controller dispatch sees a PRE-DISPATCH snapshot and not a response to the current frame. A read immediately after the dispatcher is still not a proven game-application or contact event. Collect actual frame index, sample index, trace ID, command-request label, source-scene identity consistency and read overhead; avoid unknown memory writes, second launches, resets or waveform edits.

**S002 gate:** inspect source-grounded player/club object fields first (source-only PPC atlas), then select a tiny read-only watchlist. Current main+0x074 is frame-counter-like, having 17/17 within-stage signed modular increments equal observed emulator frame gaps; three other child words change during both idle and aim; NONE is validated as power or pose.

**S000 publication gate:** private RAM numeric words, runtime pointers and local file paths remain local; new same-shot event kinds need exact typed privacy validator + tests before automatic GitHub publication. **S003 modeling gate:** exact same-shot ID, source-validated scene/bridge/trace hashes, actual emulated-frame timestamps, human power labels at at least 3 distinct observed levels, held-out clean starts, and proof instrumentation did not disrupt known-good contact. Off-green 100ft is a capped score, not ball travel.

### Operator command — OFFLINE preflight only

~~~powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Swing-Memory-Plan"
if (Test-Path $work) { throw "Worktree exists; do not overwrite" }
git -C $repo fetch origin pull/NNN/head
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_swing_memory_event_plan.py" -v
if ($LASTEXITCODE -ne 0) { throw "Phase manifest tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full suite failed" }
py scripts/plan_swing_memory_events.py
~~~

This preflight does NOT itself produce a synchronized RAM swing capture. Until S001/S002 code owners implement and validate that feature, **do not request more live shots**. Owner review + full Windows tests required before merge.
