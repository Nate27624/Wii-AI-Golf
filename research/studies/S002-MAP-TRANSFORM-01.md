# S002-MAP-TRANSFORM-01 — candidate-only pin/start coordinate evidence

**Status: isolated offline research, no validated world XYZ.** Stacked PR on S002 canonical paired MEM1+MEM2 source verifier #151; does not replace that validator or modify S001/S002 gameplay paths. 0 Dolphin sessions / 0 controller inputs / 0 writes to memory.

## Empirical prerequisites

S002's operator-provided B0 paired native MEM1 (24MiB) + MEM2 (64MiB) was analyzed already (see issue #3). It passed source-backed RSPE01 Rev1 scene-manager ID5, sport2, mode4, config raw hole1, source selected-pin/start pointers in MEM2, 6 pin objects and 31 starting markers. The separately exported banks are **not proven atomic or same emulated frame/boot**. Pin/start pointers each changed in seven existing S002 post-shot/settled captures on the same adjacent snapshot pair, but this is likely selected-object/scene-lifecycle activity, not moving ball location.

## New source leads and contradiction

1. `kiwi515/ogws_info/RP/RPSports/RPGolScene/RPGolFieldManager.h` documents selected pin pointer `RPGolFieldManager+0x44` and selected start pointer `+0x50`; these are in the field manager object, not offsets in the pointed-to map objects.
2. `.../RPGolMapObjBase.h` documents `mMapObj+0x08` pointer and `mTrans+0x30` VEC3. But `mScale+0x3C` VEC3 spans 0x3C..0x47 and **overlaps** separately annotated `mpRotation+0x40` and `mpTrans+0x44` pointers. This **invalidates treating the entire published layout as trustworthy**. Neither selected pin nor start is independently confirmed to inherit Base at offset zero. This probe reads only +0x08 and +0x30 **as unverified hypotheses**, never dereferences supposed +0x40 or +0x44.
3. Independent public PMP resource guide https://jimkatz.github.io/wiimoddingtools.html describes on-disk PMP map object positions as three 32-bit floats at **map-file entry +0x08**, and specifically original Wii Sports Golf (OGWS) starting-position map object Group 1/Object 0 with training-round settings. This file format does **not** prove the runtime `RPUtlMapObject` pointer dereferences straight to a binary PMP entry. The PMP position read is a deliberately falsifiable *second candidate*, not a claimed duplicate.
4. `doldecomp/ogws/config/RSPE01_01/splits.txt` Rev1 `RPGolMapObjBase.cpp .data` 0x803C77E8..0x803C77F8, `RPGolFieldManager.cpp .data` 0x803C77F8..0x803C78E8. First-word membership is a **module-data hint**, not a verified virtual table or derived type.

## Implemented research-only audit

- Reuses **existing S002 #151** `golf_cross_bank_state.audit_pair` and `_Banks`; checks supported Rev1 game/scene/manager/config/field BEFORE any selected-object read, with exact-sized banks in real CLI.
- Reads only two source-labelled selected objects, and for each, first word module-data-range hint, candidate BE f32 triple at object `+0x30`, candidate `mMapObj` at object `+0x08` and hypothetical PMP-format position at that candidate `+0x08`. All reads must remain in a validated bank. No arbitrary pointer graph recursion, writes, scans or side-channel.
- Bounds candidate f32 components to finite absolute <=100000, tracks nonzero flags, tracks two-hypothesis disagreement/agreement within 0.1 *unknown world units*. Produces a **sanitized console JSON of booleans and counts only**; writes optional unverified numeric vectors to a **NEW strictly local `-PRIVATE.json`** under same private-root directory for S002 local inspection. Never upload, paste or Git-commit this private numeric file. No source-derived game unit or meter normalization asserted.
- Output every `pin_world_xyz_verified/start_world_xyz_verified/live_ball_xyz_verified/wind_vector_verified/approved_for_model_training` as false. Real memory may falsify either vector hypothesis; invalid/out-of-bounds source gates must STOP.
- No new public observation kind, publisher, launcher, image, GUI, RPC, controller, or savestate code.

## Owner questions

S002 source owner should reconcile +0x3C/+0x40/+0x44 layout contradiction using actual Rev1 PPC constructor/load sites, confirm derived `RPGolMapObjPin` and `RPGolMapObjPlayer` base location, and inspect `RPUtlMapObject` memory ownership before validating any candidate. S001 owns later independent scene/pin-variant visual correlation; no need for that runtime test until candidate is coherent. S000 #154 evidence ledger accepts only source-layout/finite-plausible as weak evidence; no training. Game-ball position is not source-labelled starting-position marker.

## Guarded operator OFFLINE-only validation (only if B0 local copies exist)

This study branch is stacked on #151 and remains draft. If paired B0 files were already copied under the ignored canonical Data directory, the following validates the code and uses them; **it never launches Dolphin or creates memory dumps.**

```powershell
$root = "D:\Projects\Wii Golf AI"
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Map-Transform-Offline"
$branch = "agent/research/map-transform-candidate-triage"
$private = "$root\Wii-AI-Golf-Data\mem1-checkpoints"

if (Test-Path $work) { throw "Preserve existing worktree; study needs isolated empty path" }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Worktree failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_golf_map_transform_candidates.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full Windows suite failed" }

$mem1 = Join-Path $private "B0-MEM1.bin"
$mem2 = Join-Path $private "B0-MEM2.bin"
if (-not (Test-Path $mem1 -PathType Leaf) -or -not (Test-Path $mem2 -PathType Leaf)) {
    Write-Host "No preserved B0 MEM1+MEM2 pair in private Data root; stop without new dump."
} else {
    $out = Join-Path $private ("map-transform-" + (Get-Date -Format "yyyyMMddTHHmmss") + "-PRIVATE.json")
    py scripts/audit_golf_map_transforms_private.py --private-root $private --mem1 $mem1 --mem2 $mem2 --private-report $out
    if ($LASTEXITCODE -ne 0) { throw "Source-backed offline candidate probe failed" }
}
```

**Share only the printed sanitized console JSON**, not the `-PRIVATE.json` vectors, raw MEM1/MEM2 images, runtime addresses or private paths. If existing B0 files are elsewhere, do not guess filenames/locations; inventory locally and preserve them, or run tests alone. Do not copy older different-boot banks together to satisfy filenames.

## Validation and stop

Ten new synthetic tests (no ROM/data), including invalid revision/mode/selected object, NaN, out-of-range, false data-range hint, PMP discordance, empty map-ref, overlapping misleading +0x40/+0x44 content and no private leakage. They are **authored but require targeted and full Windows execution**; no actual user-native B0 run has occurred in this contributor's session. Draft must NOT merge until S002/S000 owner review, dependency #151 and full tests, source contradiction remains an explicit blocker for any verified XYZ claim.

## CI evidence: first cross-platform synthetic run

GitHub Actions run [40610389713](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40610389713) **SUCCEEDED** on Windows and Ubuntu using Python 3.13; both compile and targeted 10-case synthetic suite passed. This is source/mock validation only, **NOT** the canonical full Windows regression or an actual user's B0 MEM2 candidate-vector result. Upstream #151 remains draft and must not be bypassed.


## Correction: assumed B0 files absent on operator Windows host

The operator ran the guarded study on 2026-10-27 and got "No preserved B0 pair found. No new capture performed." This is a SUCCESSFUL SAFETY STOP, not an emulator or pointer failure. Previous S002 reports refer to privately examined mem1(1).raw and mem2(2).raw, but uploaded ChatGPT attachments do not establish corresponding local Windows paths. The earlier B0-MEM1.bin/B0-MEM2.bin paths were examples, NOT verified. Do NOT ask for another Dolphin dump or rename two different times as proven atomic B0.

Stage 0 (read-only): Inventory likely existing user folders for exact 24MiB MEM1 and 64MiB MEM2 plain binary files. These filenames and local paths are for the operator's eyes only; no raw or directory listing needs posting to GitHub.

~~~powershell
$root = "D:\Projects\Wii Golf AI"
$searchRoots = @(
    (Join-Path $env:APPDATA "Dolphin Emulator\Dump"),
    (Join-Path $env:USERPROFILE "Downloads"),
    (Join-Path $root "Wii-AI-Golf-Data")
)
$candidates = @(
    foreach ($dir in $searchRoots) {
        if (Test-Path -LiteralPath $dir -PathType Container) {
            Get-ChildItem -LiteralPath $dir -File -Recurse -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.Extension.ToLowerInvariant() -in @(".raw", ".bin", ".mem") -and
                    $_.Length -in @(25165824, 67108864)
                } |
                Select-Object @{Name="Bank";Expression={
                    if ($_.Length -eq 25165824) { "MEM1" } else { "MEM2" }
                }}, FullName, Length, LastWriteTime
        }
    }
)
$candidates | Sort-Object Bank, LastWriteTime | Format-Table -AutoSize
if (-not $candidates) { Write-Host "No native images in these folders; STOP." }
~~~

Stage 1 (only after recognizing two originals as the prior source pair): use exact paths displayed locally, check sizes + Rev1 disc header, stage copies in the ignored private Data root under unique neutral candidate labels rather than B0, verify SHA256 copies, then run offline auditor. Never overwrite originals; never presume same-boot/same-frame from mere matching pointers. Time gap of 111 seconds reported for earlier separate GUI exports rules out time-atomic evidence.

~~~powershell
$private = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\mem1-checkpoints"
$src1 = (Read-Host "Existing MEM1 filename from inventory").Trim('"')
$src2 = (Read-Host "Existing MEM2 filename from inventory").Trim('"')
if (-not (Test-Path -LiteralPath $src1 -PathType Leaf) -or
    -not (Test-Path -LiteralPath $src2 -PathType Leaf)) { throw "Missing originals" }
$a = Get-Item -LiteralPath $src1
$b = Get-Item -LiteralPath $src2
if ($a.Length -ne 25165824 -or $b.Length -ne 67108864) { throw "Invalid sizes" }
$stream = [System.IO.File]::OpenRead($a.FullName)
try {
    $header = [byte[]]::new(8)
    if ($stream.Read($header, 0, 8) -ne 8 -or
        [Text.Encoding]::ASCII.GetString($header, 0, 6) -ne "RSPE01" -or
        $header[6] -ne 0 -or $header[7] -ne 1) { throw "Not Wii Sports Rev1" }
} finally { $stream.Dispose() }
New-Item -ItemType Directory -Force -Path $private | Out-Null
$tag = (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + [guid]::NewGuid().ToString("N").Substring(0,8)
$mem1 = Join-Path $private ("candidate-" + $tag + "-MEM1.raw")
$mem2 = Join-Path $private ("candidate-" + $tag + "-MEM2.raw")
if ((Test-Path -LiteralPath $mem1) -or (Test-Path -LiteralPath $mem2)) { throw "Output exists" }
Copy-Item -LiteralPath $a.FullName -Destination $mem1 -ErrorAction Stop
Copy-Item -LiteralPath $b.FullName -Destination $mem2 -ErrorAction Stop
if ((Get-FileHash -LiteralPath $mem1).Hash -ne (Get-FileHash -LiteralPath $a.FullName).Hash -or
    (Get-FileHash -LiteralPath $mem2).Hash -ne (Get-FileHash -LiteralPath $b.FullName).Hash) {
    throw "Staged copy hash mismatch"
}
Write-Warning "Unverified same-boot/frame status: candidate pair only."
$report = Join-Path $private ("map-transform-" + $tag + "-PRIVATE.json")
py scripts/audit_golf_map_transforms_private.py --private-root $private --mem1 $mem1 --mem2 $mem2 --private-report $report
if ($LASTEXITCODE -ne 0) { throw "Offline source gate rejected pair" }
~~~

Share only the console's sanitized boolean report; never upload native banks, raw pointers, or numeric PRIVATE report. No new Dolphin actions are required. The #159 targeted Windows/Linux CI was green; full Windows regression and S002 class-layout review remain outstanding.

## Operator native-file inventory and updated PPC constructor source evidence

Operator found native 24MiB MEM1 + 64MiB MEM2 files in three places: current Dolphin Dump directory and two preserved subfolders under the ignored sibling Wii-AI-Golf-Data/mem-checkpoints directory, named roster-existing and unclassified-20261027-203338. The historical example filenames B0-MEM1.bin and B0-MEM2.bin do NOT exist in the earlier assumed folder. This was a safe stop, not a failed analysis.

Use the preserved pair in each folder DIRECTLY by passing that folder as --private-root, and its mem1.raw and mem2.raw as --mem1/--mem2. Write an exclusive new -PRIVATE.json output in the same folder. No copying, Dolphin, input, savestate, network or upload is needed. Compare local SHA256 pair identities to avoid analyzing duplicate images as independent scenes; do NOT publish hashes. Different file content does not prove a different boot, game phase or observed coordinate variant.

Other agent's *actual Rev1 DOL* inspection identified RPGolMapObjBase constructor at 0x80290A48: BE f32 translation at object +0x30/+0x34/+0x38, scale at +0x3C/+0x40/+0x44, rotation self-pointer at +0x48 points to obj+0x0C, translation self-pointer at +0x4C points to obj+0x30. Published header erroneously labels last pointers +0x40/+0x44. New audit checks exact equality of the two bounded self-reference slots WITHOUT following either pointer and returns constructor_layout_consistent_candidate, rotation selfref match and translation selfref match. Neither numerical finiteness nor these selfref matches proves the selected pin or player-start object's dynamic type, map units, current ball XYZ, or genuine world-space location. Real user B0 pair already had horizontal start-to-pin separation 216.551 unknown game units, pin/cup horizontal coincidence and +3 vertical offset as independently reported by S002. Treat as one historical scene.

Windows+Ubuntu Python 3.13 targeted synthetic CI run 40611438500 passed following the self-reference additions. Operator Windows FULL suite and real #159 console candidate flags are NOT yet available. S002 owners must confirm derived class base pointer alignment and field semantics before promoting any vector in S000 field ledger.
