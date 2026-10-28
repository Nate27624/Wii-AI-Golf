# S002-MEM1-CONTRAST-01 — offline private memory comparison

**Status: OFFLINE comparator only. No live dump capability confirmed or authorized.** Stacked on coordinator full-memory pivot PR #148. S002 owns memory semantics, S001 runtime, S000 CLI/privacy, S003 modeling.

## Evidence basis

The unique live golf scene root is source-consistent, but no verified player or power type exists. Previously all 28 first-level pointer-shaped children were checked in idle/WASD phases without an aim-specific signal; candidate main +0x074 changes even when idle and matched elapsed frames in 17/17 comparisons in one session. Narrow 4/8/4-child reads took 6/10/6 frames maximum, too coarse for impact timing. Further repeated shallow scans and score-only power tuning are not justified.

External documentation: [WiiBrew memory map](https://www.wiibrew.org/wiki/Memory_map), [Dolphin mainline memory debugger](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/DolphinQt/Debugger/MemoryViewWidget.cpp), [Felk bridge paused-loop risks](https://github.com/dmang-dev/mcp-dolphin/blob/main/CHANGELOG.md). Mainline GUI behavior does NOT establish that the user's specific Felk Preview 4 fork supports native paused MEM1 export. No bulk 24MiB byte-by-byte RPC polling, no RPC pause/resume, no second Dolphin process.

## Proposed experiment: four checkpoints

After S001 confirms the current Felk build's native binary dump capability, explicit operator approval is required for one first-ball session, four separate local 24MiB uncompressed MEM1 dumps:

- B0 stationary first ball, no input.
- B1 later stationary, unchanged scene/hole.
- B2 WASD pointer-only phase, no A or swing; operator labels, NOT proof of 3D camera/golfer motion.
- B3 return to stationary after WASD release.

Track exact file size, order, native memory base, game ID/revision, scene/hole and frame metadata separately in private notes. Preserve all savestates and bridge. Never upload RAM binary, DOL, ROM, local detailed report, screenshots containing memory, user device identifiers or raw pointer values.

## Implemented and conservative

New scripts/audit_mem1_checkpoints_private.py reads four identical-size, 24MiB contiguous raw MEM1 dumps in a 4KiB streaming loop. Each aligned 32-bit word is classified only by equality:

| Comparison | Exploratory interpretation |
| --- | --- |
| B0=B1=B2=B3 | static in this sequence |
| B0 differs B1 | idle-changed or confounded |
| B0=B1=B3 and B2 differs | pointer-phase reverted candidate |
| B0=B1, B2=B3 and differ | pointer-phase persistent candidate |
| B0=B1=B2, B3 differs | changed after pointer |
| Other | ambiguous |

This never proves causality, object class, byte representation, power, club pose or ball position. The private output is exclusively new, named with -PRIVATE.json, and contains ranked page indices, limited word-relative offsets, private per-file SHA256 and cannot-be-published marker. The printed JSON has ONLY aggregate counts/booleans: no runtime address, raw data/bytes, page indices, file paths or file hashes. Private inputs must be within sibling ignored Wii-AI-Golf-Data and cannot be symlinks. If export size is not exactly 24MiB, STOP: it may be a different memory layout or a savestate; do not truncate or bypass the validator.

## Safe offline operator tests: NO Dolphin needed

~~~powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-MEM1-Offline"
if (Test-Path $work) { throw "Worktree exists; preserve it" }
git -C $repo fetch origin agent/research/mem1-private-checkpoint-differential
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_mem1_checkpoint_contrast.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full suite failed" }
~~~

11 new synthetic tests are authored, but have not yet run on operator Windows. They use fake tiny binary pages, no private game files.

## NOT YET AUTHORIZED: real dump offline example

After native format verification, S001/S002/S000 review and operator opt-in only, the intended private filenames under the ignored sibling Data/captures directory are B0-mem1.raw, B1-mem1.raw, B2-mem1.raw, B3-mem1.raw. From the isolated worktree run the following ONE-LINE command (do not execute before approvals):

~~~powershell
$private = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures"
py scripts/audit_mem1_checkpoints_private.py --b0 "$private\B0-mem1.raw" --b1 "$private\B1-mem1.raw" --b2 "$private\B2-mem1.raw" --b3 "$private\B3-mem1.raw" --private-report "$private\mem1-B0-B3-review-PRIVATE.json"
~~~

Only aggregate stdout may eventually be published after strict typed S000 review. **Private detailed report and source binary files must remain local.**

## Coordination and next gate

S001 verify exact currently installed Felk native dump GUI and safe pause behavior (don't swap emulator). S002 validate raw MEM1 base/layout and source/assembly verified candidate member identity; use PR #144 and #146 as complementary source hints, not competing live watchlists. S000 own typed publication and canonical launcher. S003 block ML until confirmed game values, same-shot alignment, and distinct power measurements. No new swing trials are requested by this study.
