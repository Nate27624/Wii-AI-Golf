# S002: Source-typed minimap effect handle fields

## Independent primary code evidence

Public RSPE01 Rev1 decomp source, `doldecomp/ogws`:

- [`include/Pack/RPKernel/RPSysEffectBase.h`](https://github.com/doldecomp/ogws/blob/master/include/Pack/RPKernel/RPSysEffectBase.h): the `RPSysEffect` wrapper declares `nw4r::ef::Handle<nw4r::ef::Effect> mHandle; // at 0x78`, after `mTransform` at 0x48. Its effect `mPosition` is at +0x3C, and effect transform matrix begins at +0x48. Therefore +0x78/+0x7C are **NOT** that wrapper's position/velocity vector.
- [`include/nw4r/ef/ef_handle.h`](https://github.com/doldecomp/ogws/blob/master/include/nw4r/ef/ef_handle.h): `nw4r::ef::HandleBase` is a two-field 32-bit layout, `u32 mObjectID` at +0x00, `LinkedObject* mObject` at +0x04; templated Handle inherits it. Combining offsets maps `RPSysEffect+0x78 = mHandle.mObjectID` and `RPSysEffect+0x7C = mHandle.mObject`.
- [`src/nw4r/ef/ef_handle.cpp`](https://github.com/doldecomp/ogws/blob/master/src/nw4r/ef/ef_handle.cpp): copying/assigning a handle stores the ID and pointer; valid means non-null object pointer and matching pointed-to object ID. This is an **effect lifecycle handle**, not physical ball location.
- [`src/Pack/RPKernel/RPSysEffectBase.cpp`](https://github.com/doldecomp/ogws/blob/master/src/Pack/RPKernel/RPSysEffectBase.cpp): create() assigns `createEffect` to `mHandle`; fade()/forceKill()/reset() clear `mHandle` to `INVALID_HANDLE`. The constructor calls reset(). Mutations may occur from lifecycle transitions, including shot-associated visual effects, and need not imply movement.
- [`kiwi515/ogws_info FieldManager.h`](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolFieldManager.h): `mMapPlayerEff +0x94`, `mMapShotLineEff +0x98`, `mMapBallEff +0x9C` all typed as `RPSysEffect*`.

## Correlation with real successful-shot memory, not circular type inference

The operator's already confirmed successful-shot private snapshots had 3 PRE, 2 POST, 3 SETTLED observations; ALL eight stable changing RAM words were already changed in BOTH POST observations. Their source-relative windows are overlapped and 0x90 apart across ALL eight snapshots. Strict four-pair de-aliasing verified four positions per repeated slot: +0x78 has a non-pointer-like word; +0x7C has a pointer-like word. That is exactly what this independently documented RPSysEffect handle struct predicts for an `mObjectID` + `mObject` pair. The observed 0x90 spacing is measured **allocation/window spacing**, not yet proof that sizeof(RPSysEffect) is 0x90 (it is not claimed by the header).

**Evidence levels:** Verified: source-defined class field types and existing observed pair offsets/bit patterns. Strongly source-consistent hypothesis: eight changed words in the 4 observed live wrappers are four handles changing effect IDs and object pointers. NOT yet independently verified: runtime vtables/class identity of all four allocations, semantic cause of each handle transition, actual effect creator/owner, true end-to-end object-pointer ID match, and exact C++ object size/allocator stride.

**Consequence:** Do not treat ANY of the eight words as ball XYZ, velocity, power, aim angle, or a physical shot outcome. The displayed 100.0ft and 75% gauge were human observations only. Previously identified FieldManager 0x80290E80 vector writer (r3 loaded from +4(r29)) and MapObjBall 0x80297810 float resets are NOT needed to explain these changes and do not become effect writers by numeric offset matching. Instead trace `RPSysEffect::create/fade/forceKill/reset` handle lifecycle and the underlying `nw4r::ef::HandleBase` code, preserving raw data privacy and no extra live swing.

## Next verification without another swing

Source: independently locate the precise RSPE01 Rev1 PPC store sites for `RPSysEffect::mHandle` (the source unit `RPSysEffectBase.cpp` in public link split) and the invoking minimap FieldManager functions; connect callers to +0x94/98/9C effect pointers. Data: use the saved PRE/POST/SETTLED windows to check handle ID/pointer paired transitions and test pointer-target ID only when both target and ownership are available; do not dereference arbitrary guessed addresses or publish raw words. Validity needs a same-phase pointer-target ID check, not merely pointer-shaped bits. No physical ball/training promotion.

State: `effect_handle_source_layout_identified=true`; `effect_runtime_wrapper_identity_verified=false`; `effect_handle_pointer_target_identity_verified=false`; `ball_world_xyz_verified=false`; `training_allowed=false`; `allowed_to_publish=false`.
## One-command source follow-up (read-only, no new captures)

Run this whole PowerShell block from any working directory to examine the existing source code for handle writer PCs and FieldManager r31 origin candidates, without exporting private data. It does NOT prove runtime RPSysEffect identity.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $root = 'D:\Projects\Wii Golf AI'
    $repo = Join-Path $root 'Wii-AI-Golf'
    $private = Join-Path $root 'Wii-AI-Golf-Data\ball-study-20261027-212633'
    $branch = 'agent/research/golf-source-object-windows-private-20261027'
    if (-not (Test-Path -LiteralPath (Join-Path $private 'checkpoint-manifest-PRIVATE.json') -PathType Leaf)) { throw 'B0 checkpoint missing' }
    git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
    if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
    $sha = (git -C $repo rev-parse "origin/$branch").Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve code revision' }
    $work = Join-Path $root "Wii-AI-Golf-Handle-Source-$($sha.Substring(0,8))"
    if (Test-Path -LiteralPath $work) {
        $current = (git -C $work rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $current -ne $sha) { throw 'Existing worktree is not exact revision' }
    } else {
        git -C $repo worktree add --detach $work "origin/$branch"
        if ($LASTEXITCODE -ne 0) { throw 'Cannot create safe worktree' }
    }
    py -m unittest discover -s "$work\tests" -p 'test_golf_effect_handle_source_private.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic source tests failed' }
    $raw = @(py -I "$work\scripts\audit_golf_effect_handle_source_private.py" --private-root $private)
    if ($LASTEXITCODE -ne 0) { throw 'Private B0 source audit failed' }
    $result = ($raw -join [Environment]::NewLine) | ConvertFrom-Json
    Write-Host 'SOURCE HANDLE MEMBERS'
    $result.expected_effect_handle_members | Format-Table -AutoSize
    Write-Host 'RPGolFieldManager r31 SOURCE DEF CANDIDATES'
    $result.field_manager_r31_candidate_defs | Select-Object -Last 15 | Format-Table -AutoSize
    Write-Host 'RPSysEffectBase PPC HANDLE OFFSET WRITES'
    $result.RPSysEffectBase_literal_handle_hits | Where-Object { $_.access -eq 'write' } |
        Select-Object -First 25 pc,offset,mnemonic,base_register,value_register | Format-Table -AutoSize
    $contexts = @($result.RPSysEffectBase_contexts | Where-Object { $_.candidate.access -eq 'write' } | Select-Object -First 2)
    foreach ($context in $contexts) {
        Write-Host "SOURCE CONTEXT $($context.candidate.pc)"
        $context.code | Select-Object pc,word,approximate_disassembly | Format-Table -AutoSize
    }
}
```

## Owner-run PPC result: known function assignments resolve the apparent +0x7C writers

The operator fetched B0 code at `90a5a559` and ran the six `test_golf_effect_handle_source_private.py` unit tests successfully. The actual gated source scan reported exactly ONE recognized `r31` definition candidate, `0x80290DD0 mr r31,r3`, and exactly TWO D-form writes at `+0x7C` in the compilation unit `RPSysEffectBase.cpp`:

| Exact PC | PPC opcode | Source-defined containing function | True typed target |
| --- | --- | --- | --- |
| `0x80194FCC` | `0xD003007C stfs f0,+0x7C(r3)` | `RPSysEffect::setPowerSpecDirAdd` at `0x80194F48..0x80195000` | `nw4r::ef::Emitter::mParameter.mVelPowerSpecDir` (f32) |
| `0x80195064` | `0xD3E3007C stfs f31,+0x7C(r3)` | `RPSysEffect::setPowerSpecDir` at `0x80195000..0x80195094` | `nw4r::ef::Emitter::mParameter.mVelPowerSpecDir` (f32) |

Independent primary decomp evidence: `doldecomp/ogws config/RSPE01_01/symbols.txt` identifies the exact PPC function boundaries; `src/Pack/RPKernel/RPSysEffectBase.cpp` shows that both routines modify particle-emission power (one adds a base value from an emitter-resource descriptor, one sets the supplied scalar) via `pEmitter->mParameter.mVelPowerSpecDir`; `include/nw4r/ef/ef_emitter.h` gives Emitter `mParameter` at **+0x20**, its internal `mVelPowerSpecDir` at **+0x5C**, hence Emitter `+0x7C`. These float stores therefore **DO NOT** write `RPSysEffect::mHandle.mObject` (LinkedObject* at wrapper +0x7C), and they are **NOT** golf-club swing-power fields. `RPSysEffectBase.cpp` may still mutate handles via inlined calls or other stores, which this narrow D-form scan does not exhaust.

FieldManager symbol map independently bounds `fn_80290DB0` to `0x80290DB0..0x80290F78`. The operator's PPC reported `0x80290DD0 mr r31,r3`; the earlier operator trace included `0x80290E4C mr r29,r31`, `0x80290E78/0x80290E98 lwz r3,+0x04(r29)`, and `0x80290EB8 addi r29,r29,4`. These are in ONE named function, and the known idiom establishes static `r3(at DD0) -> r31 -> r29 -> +4 child-pointer walk` with no recognized r31 redefinition. It does **not** independently prove that r3 at DD0 equals the method's incoming this pointer: the code from its prologue at DB0 through the DD0 assignment needs inspection for calls/reassignments and path reachability. Equally it does not prove that any child points into the observed minimap effects.

Follow-up code update: `scripts/audit_golf_effect_handle_source_private.py` now distinguishes D-form offset hits from **opcode-type-compatible** direct HandleBase word stores and explicitly labels these two `stfs` sites as typed Emitter power writes and not HandleBase pointer writes. It displays the bounded function-prologue-to-r31 source context without asserting CFG/method-this identity; synthetic negatives include a fake intervening r31 definition and both exact float words. No user raw RAM, pointer value, private path, running emulator, or new shot is needed.

**Status:** Source effect HANDLE field typing = established; source particle-emission-power float-store typing = established; FieldManager r31 static source chain = source-supported; actual observed runtime effect-wrapper identity, pointed-to ID check, shot dynamics, ball XYZ/velocity, and model training = UNVERIFIED. This is a documentation and static-code result, not a new live acquisition.