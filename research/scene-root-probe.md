# S000/S002 — source-gated scene-manager pointer triage

## Grounded static lead

The public Wii Sports US Rev1 decompilation project
[doldecomp/ogws config/RSPE01_01/splits.txt](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt)
assigns \`Pack/RPSystem/RPSysSceneMgr.cpp\` an **8-byte .sbss range**
[0x804BF4D8, 0x804BF4E0). Independently,
[RPSingleton.h](https://github.com/doldecomp/ogws/blob/master/include/Pack/RPSingleton.h)
and [RPSysSceneMgr.cpp](https://github.com/doldecomp/ogws/blob/master/src/Pack/RPSystem/RPSysSceneMgr.cpp)
declare and instantiate the static singleton field \`RPSysSceneMgr::spInstance\`.
The map alone **does not determine** whether either of the two 32-bit words
holds that field, or how the compiler laid out adjacent data. These are
**two candidates**, NOT confirmed pointer storage locations.

Source-verified EGG::SceneManager offsets: current scene +0x0C, scene ID
+0x18; golf scene enum ID 5. kiwi515/ogws_info calls RPGolScene +0x9C an
RPGolMain*, but the newer decomp calls the same member unk9C. The split
map also defines RPGolScene.cpp .data [0x803C7718,0x803C7798),
which offers a weak class/vtable-location plausibility check, not type proof.

The previous operator capture of 28 focused frames (idle/aim-only/idle)
showed **zero changed 32-bit words** across golf_config/golf_field/
sports_sequence, sample read spans 9 frames, no relocations. Inspection of
the private capture shows many *unchanging pointer-shaped* values in the
RPGolFieldManager layout; the documented ones are map/course/minimap
resources, NOT the active golfer. No raw pointer values from that capture
were uploaded or included in this document. The operator's WASD input moved
the Wii pointer; the prior \`camera_moved\` label is a human phase annotation,
not independent validation that the game's 3D camera moved.

## Prototype probe, without gameplay input

\`scripts/probe_golf_scene_root.py\` attaches only to an already running
Felk bridge. It never sends controller commands, loads a save state, starts
Dolphin, writes memory or scans arbitrary addresses.

- Verify RSPE01 **Rev1** disc header and static RPGolConfig Hitting the
  Green mode **4** before reading the candidates.
- Read only the two source-backed static storage cells.
- If the value looks like a valid RAM pointer, read manager +0x18 (scene
  ID), +0x0C (scene address); read scene +0x00 and +0x9C only when game scene
  ID is 5 and scene pointer is bounded. Never dereference the +0x9C value.
- Repeat twice; require **identical private pointer values** and classification
  over passes, monotonically increasing emulator frame counters, and at most
  40 emulated frames per pass.
- Emit only **aggregate counts, slot indices 0/1 and booleans**. Never
  include runtime addresses, pointer values, raw bytes, ROMs, or savestates.
- The \`confirmed_*\` flags remain **false**, even when one candidate
  passes all shape checks. False positives and scene-type ambiguity remain.

## Execution, only after S002 owner review and offline tests

Use the canonical main checkout's existing startup, then run the new
read-only probe from its own tested worktree. Close Dolphin first and
**boot it only once**.

\`\`\`powershell
$root = "D:\Projects\Wii Golf AI"
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Scene-Root-Pilot"
if (Test-Path $work) { throw "Worktree exists; do not overwrite" }
git -C $repo fetch origin pull/NNN/head
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_scene_root_probe.py" -v
if ($LASTEXITCODE -ne 0) { throw "Do not start Dolphin" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Do not start Dolphin" }

# Only with Dolphin closed:
Set-Location $repo
py scripts/launch_golf.py
if ($LASTEXITCODE -ne 0) { throw "Launcher failed" }

# Leave Dolphin running at the verified Hitting the Green ready screen.
Set-Location $work
py scripts/probe_golf_scene_root.py --attach-running
\`\`\`

Replace NNN with this PR number once published; do not use this prototype
against mismatched ROM/revisions or a different game state. This script
intentionally does **not** auto-publish until S000's privacy/provenance
gate (PR #126) explicitly allows this new type of sanitized record.
S000 must integrate it with the canonical uploader after schema review;
never send raw RAM or pointers to GitHub.

## Success versus identification

A stable single candidate with golf ID 5 and a golf-scene-data-region
vtable-like pointer is **evidence of an anchored scene manager**.
It does **not** identify RPGolMain type, golfer pose, power or physics.
S002 should then independently validate singleton storage against Rev1
static callsites and only afterward add a minimal, frame-bracketed,
read-only gameplay-owner watchlist with idle/A-only/camera negative
controls and distinct human-observed power levels. S003 joins data
only with same-shot source-validated frame brackets.
