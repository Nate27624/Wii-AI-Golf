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