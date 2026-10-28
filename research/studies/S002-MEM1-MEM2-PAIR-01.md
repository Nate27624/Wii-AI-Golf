# S002-MEM1-MEM2-PAIR-01 — Reuse existing native RAM banks

**Status:** draft offline source-root audit; no new dumps, Dolphin control, training, or upload. The user's existing mem1.raw (24 MiB) and mem2.raw (64 MiB) are in the default Dolphin Dump directory.

Earlier uploaded MEM1 analysis verified the RSPE01 Rev1 header and SceneManager scene ID5 in MEM1 but found active scene, golf config and field manager pointers targeting MEM2. This study follows those source-backed pointers across the two existing banks.

**Important temporal limitation:** observed MEM1 and MEM2 file modification times were about 8:23:42 PM and 8:25:33 PM. These are two different banks taken ~112 seconds apart, not a synchronized emulator frame or four B0–B3 timepoints. Structural consistency must not be represented as frame-atomic game telemetry.

## Operator command, offline only

~~~powershell
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-MEM1-MEM2-Pair'
$branch = 'origin/agent/research/paired-mem1-mem2-source-anchors-20261027'
git -C $repo fetch origin
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (Test-Path -LiteralPath $work) { throw 'Worktree exists; preserve it' }
git -C $repo worktree add --detach $work $branch
if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
Set-Location $work
py -m unittest discover -s tests -p 'test_audit_golf_mem1_mem2_pair.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Targeted tests failed' }
py scripts/audit_golf_mem1_mem2_pair.py
if ($LASTEXITCODE -ne 0) { throw 'Offline pair audit failed' }
~~~

The tool reads existing default files at the current user's APPDATA/Dolphin Emulator/Dump directory; optional --mem1 and --mem2 overrides support alternate private paths. It checks exact bank lengths, RSPE01 revision 1, basic pointer bounds and source-scene relationships. It prints no raw memory bytes, absolute heap pointer addresses, file paths, ROMs or secrets. No output file, uploader, emulator launch or RPC.

## Source-backed structural candidates, not physics verification

- RPSysSceneMgr two-cell .sbss static range beginning 0x804BF4D8. EGG::SceneManager current scene pointer +0x0C, current scene ID +0x18 (5).
- EGG::Scene own ID +0x1C (5), backlink +0x20, golf sport ID +0x54 (2), RPGolScene candidate RPGolMain pointer +0x9C.
- RPGolConfig static pointer at 0x804BF8C4; game mode +0x94 expected 4, current hole raw index +0x98.
- RPGolFieldManager static pointer at 0x804BF868; pin/start counts +0x3C/+0x48, pin/start/cup/wind/course/map pointers +0x44/+0x50/+0x54/+0x68/+0x70/+0x18.

Existing S002 source facts: PRs #122 and #129, doldecomp/ogws and ogws_info Rev1 data. Pointer presence is not a proven player transform, ball XYZ, spin, launch velocity, power, wind vector, terrain or gameplay scoring field. No semantic field is training-ready. A broken cross-bank chain may reflect the 112-second snapshot gap.

## Coordination and validation

New-only standalone source, test and study files. No overlapping edits with S000 CLI, S001 bridge/control, S002 capture, S003 model, PR #150 environment audit, PR #151 four-timepoint MEM1 differencer or PR #147 frame markers. Linux isolated synthetic tests 5/5 PASS and compileall PASS; **no real raw files have been analyzed by this author, and full current Windows suite remains unrun on this branch**. S002 domain review + S000 privacy review and operator real-data stdout are required before merging. Preserve existing dumps locally and never publish private RAM or runtime pointers.
