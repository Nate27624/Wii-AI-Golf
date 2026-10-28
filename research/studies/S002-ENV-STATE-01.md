# S002-ENV-STATE-01 — source-constrained golf environment memory inventory

**Research status:** Offline-only pilot, **not** a verified environment decoder or approved GitHub publication kind. **Issue:** S002 #3 / S000+S002+S003 #121. **Operator's new priority:** understand game/environment observations before optimizing swing power.

## What source analysis actually established

Wii Sports RSPE01 USA Rev1 from `kiwi515/ogws_info`, using existing S002 `src/wii_ai_golf/audit/outcome_transition.py` RAM windows:

| Source object and singleton pointer storage | Candidate member offset | Documented type/role | What is NOT established |
|---|---:|---|---|
| `RPGolConfig` static pointer `0x804BF8C4` | `+0x94` | `mGameMode` u32; Hitting the Green mode 4 | This mode says nothing about shot power |
| `RPGolConfig` | `+0x98` | `mCurrentHole` u32 | Indexing vs screen/relative hole is unverified in live captures |
| `RPGolFieldManager` static pointer `0x804BF868` | `+0x3C`, `+0x48` | Pin and player-start object counts | Valid object identity/ownership |
| `RPGolFieldManager` | `+0x44` | `mCurrentPinObj` pointer | Pin coordinates XYZ |
| `RPGolFieldManager` | `+0x50` | `mCurrentStartObj` pointer | Position of ball *after* any shot |
| `RPGolFieldManager` | `+0x54` | `mCupObj` pointer | Cup XYZ or collision radius |
| `RPGolFieldManager` | `+0x68` | `mWindObj` pointer | Numeric wind direction/speed |
| `RPGolFieldManager` | `+0x70` | `mCourseObj` pointer | Surface collision/height/slope |
| `RPGolFieldManager` | `+0x18` | `mMapData` pointer | Terrain grid/material classification |
| `RPGolFieldManager` | `+0x6C`, `+0x7C`, `+0x88` | UI wind-arrow/slope/minimap visible flags | Actual weather or terrain data |
| `RPGolConfig::GetWind` (function `0x8029CE74` in source map) | unknown backing data | May return game wind direction/speed | Safe values from RAM or verified callsite not yet derived |
| `RPGolMapObjBase` | `+0x30` | `mTrans` vector of three floats in base map-object layout | No proof active current pin/start subclasses expose this offset or the live pointer is the right class |

Important: previously changed `golf_field+0x44,+0x50` *in older cohort* are **source-documented pointers**, not a tracked moving ball or a numeric trajectory. Our prior `main+0x074` tick-like word is a nuisance counter; no more static 28-child idle/aim scans.

**Source links:**
- https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolConfig.h
- https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolFieldManager.h
- https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolMapObjBase.h
- https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPSportsSequenceMgr.h

## Offline implementation: zero new Dolphin

New `wii_ai_golf.audit.environment_state_candidate.audit_environment_snapshots` consumes existing **PRIVATE** `outcome-*-RAW-PRIVATE.jsonl` records from S002 `collect_outcome_transition.py`. It requires source/version/mode, stable instance-window bases, bounded nonoverlapping frame brackets, exact game config+field buffer sizes, feasible counts/pointers, and source-known boolean flag bytes. It emits only a fixed sanitized local summary: candidate hole raw index, stable/present/change indicators for pin/start/wind/cup/course/map pointers, counts and display flags, and explicit false flags for ball/pin XYZ, true wind, terrain and game-phase semantics.

No raw values, pointer addresses, images, ROMs, savestates, private paths or source code are echoed in the summary. It has **NO uploader** or networking, performs **NO controller RPC** and **NO emulator launch**. The unchanged S002 live collector remains canonical. A failed hypothesis/format is reported as an unsupported capture, never guessed values.

## Operator offline pilot on prior captured files — only after S002 owner review

```powershell
$root = "D:\Projects\Wii Golf AI"
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Environment-Offline"
$branch = "agent/research/environment-memory-offline-audit"
$captures = "$root\Wii-AI-Golf-Data\captures"

if (Test-Path $work) { throw "Study worktree already exists; preserve it." }
git -C $repo fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }

Set-Location $work
py -m unittest discover -s tests -p "test_environment_state_candidate.py" -v
if ($LASTEXITCODE -ne 0) { throw "Targeted tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full tests failed; stop and report" }

$files = @(Get-ChildItem $captures -Filter "outcome-*-RAW-PRIVATE.jsonl" -File |
    Sort-Object LastWriteTime -Descending)
if ($files.Count -eq 0) { throw "No existing outcome captures" }
# Start with one *existing* capture, not an unreviewed new Dolphin run.
py scripts/audit_environment_private.py --input $files[0].FullName
if ($LASTEXITCODE -ne 0) { throw "Private audit failed; preserve RAW" }
```

Share only the **printed JSON summary**. The tool writes a local `env-candidates-*-summary.json` beside private capture, and never auto-uploads. If the actual capture does not match this strictly specified legacy window shape, STOP and return the error; S002 should review lineage rather than relaxing constraints blindly.

## Next targeted environment observation experiments — S002 owner

1. **Current hole / course scenario:** Compare two independently human-verified first-ball scenarios with different hole/pin visual states, after canonical S001 startup; require source offset `mCurrentHole` match to UI or describe mismatch. Pin pointer identity is not pin XYZ.
2. **Pin and player start XYZ:** Source-disassemble/map the actual `RPGolMapObjPin` and `RPGolMapObjPlayer` layouts, including whether `RPGolMapObjBase::mTrans+0x30` applies. Verify by moving/changing the pin in a controlled alternate scenario and manual image observation; do not dereference arbitrary pointers.
3. **Wind:** Trace `RPGolConfig::GetWind` implementation / its actual backing fields; derive a bounded, source-gated read-only wind direction/speed candidate, compare to displayed wind and repeat across another condition. Do not infer wind values from `mWindObj` pointer.
4. **Ball & terrain:** Find live ball object/collision structures and ground-material/height fields from callsite/source-backed ownership; test pre-shot, in-flight and settled with precise same-shot markers only after S001/S002 agree. Preserve separate *player start* and *current ball*.
5. **Phase/state:** `RPSportsSequenceMgr` source documents `mSequence+0x08` but not an authoritative mode mapping; compare menu/tee/flight/settled before claiming a stable game phase decoder. Avoid treating generic clock fields as a state machine.

**Priority for future agent observation schema:** `game_mode` → `hole_id` → `pin_xyz` and `ball_xyz` → `wind_vector` → `terrain/slope` → `shot_phase`. Keep confidence provenance per field (source-layout / runtime-plausible / human-correlated / verified), no fabricated metric score or speed. No new swing requested by this PR.

## Validation and merge gates

- Pure source-equivalent Linux Python: **11/11 synthetic unit tests pass**, compileall passed; one synthetic CLI invocation on temporary fixture returned a sanitized report. No user private evidence tested.
- **Not run:** canonical full Windows checkout suite, real private outcome captures, Dolphin UI, actual pin/wind/ball decoding.
- S002 approves source offsets and strict private format before promotion. S000 approves any new public observation kind separately (#126/#136).
- PR remains **DRAFT**, non-merged pending S002/S000 owner review, Windows targeted/full suite and input lineage confirmation.
