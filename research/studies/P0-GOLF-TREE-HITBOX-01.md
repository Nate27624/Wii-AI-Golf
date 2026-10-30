# P0: Source-backed tree hitbox research — original Wii Sports Golf

Date: 2026-10-30. Research-only, no Dolphin, controller actions, game RAM
writes, private code/coordinates in Git, or trainable physics labels.

## Operator-proven inputs

Operator original RSPE01 Rev1 seven-phase SHA/source-gated archive:
- `RPGolFieldManager +0x1C`: **94** tree objects, `+0x20` bounded MEM2
  contiguous array; source PPC code verifies **0x54/84-byte stride**.
- Original PPC iteration `lwz array; add element index; bl RPGolMapObjTree;
  addi step,+84; read count; cmpw; blt`. Original phase 1/5/7 tree
  `RPGolMapObjBase.mTrans +0x30` positions are 94 finite/distinct and
  word-bitwise-stable across captures.
- Private source candidate position file already successfully created by
  operator: `Wii-AI-Golf-Data/derived/golf-tree-positions-source-94-PRIVATE.json`.
  Never move into Git/Drive or share raw object vectors.
- Original terrain candidate source KCL 2498 full prism slots; exact original
  flags `1 fairway=208,2 rough=585,3 bunker=301,4 OOB=508,
  5 camera-lock=44,6 green=478,7 water=7,9 fringe=99,C cliff=268`.
  This KCL candidate **contains no separately labeled tree/leaf triangles**,
  but active octree ownership is not proven, and **this does not establish
  the absence of separate tree collision**.
- Original Wii Sports Resort KCL enum `KCL_WS2_TREE=0x0011` and
  `KCL_WS2_LEAVES=0x0012` is NOT the original Golf KCL enum.
  Source [kiwi515/Resort2OG/src/core/RPGame/RPGolFieldManager.h](https://github.com/kiwi515/Resort2OG/blob/master/src/core/RPGame/RPGolFieldManager.h).
  Do not import Resort physics/response parameters as if OGWS.

## What constitutes a verified hitbox?

A known tree center and a pretty 3D tree model are **not** a collision shape.
Need one of:
1. **Native collision path:** trace `RPGolMapObjBall` / `RPGolSimulateManager`
   to object or `RPGolKCol` collision query; prove its receiver and
   object identity and identify native geometry (model-embedded triangles,
   capsules, spheres, cylinders or leaf volumes).
2. **Native numeric geometry:** recover radius/height/shape parameters and
   coordinate transforms, associate with both active tree variants, and
   verify actual code uses them in ball collision.
3. **Outcome-based falsification**: designed ball trajectories traversing
   known tree center/height ranges, matched phase and result-first
   snapshots; compare predicted non-contact/contact and observed
   deflection, with source timing. Never infer precise shape from one hit.

If tree and leaves are handled by different response branches, identify
their target routines and coefficients separately (reflect/restitute,
momentum drag/velocity damping, stochastic deflection, or other).
Do NOT assume trunk cylinders or canopy spheres merely for UI display.
The exact collision hitbox, bounce behavior, occlusion and whether foliage
collides are **all currently UNVERIFIED**.

## Next read-only native code census

Public, bounded Rev1 .text unit intervals
[source](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt),
mirrored in project's
`research/source_maps/RSPE01_01_public_text_units.json`:

| Unit | Executable interval |
|--|--|
| RPGolMapObjTree.cpp | 0x80296238–0x80296EA8 |
| RPGolMapObjTreeWater.cpp | 0x80296EA8–0x80296F50 |
| RPGolMapObjBall.cpp | 0x80296FD8–0x8029B240 |
| RPGolSimulateManager.cpp | 0x8029B240–0x8029BBB4 |
| RPGolKCol.cpp | 0x802A3DE4–0x802A7444 |
| RPGolFieldManager.cpp | 0x80290B44–0x80294184 |
| RPUtlCollisionChecker.cpp | 0x801BC418–0x801BD51C |
| RPUtlCollisionModel.cpp | 0x801BB9B8–0x801BC384 |

`scripts/p0_tree_hitbox_source_callgraph_private.py` makes a
bounded read-only census of source-unit-to-source-unit PPC direct
`bl` calls, indirect `bctrl/bclrl` counts, candidate
`lfs/stfs` member displacement counts (only non-stack bases),
and first 15 floating compares. It emits **public code-unit
relative** callsites, not native code bytes or runtime memory addresses.
This can prioritize a follow-up bounded disassembly of a **real relevant
function** once identified. Direct calls may be absent even if
runtime collision is processed through vtable callbacks:
**no direct edge is not evidence of no hitbox**.

Run against original existing archive from an isolated code worktree:

```powershell
$archive = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE'
py -3 -I scripts/p0_tree_hitbox_source_callgraph_private.py --archive "$archive" --capture 7
```

The complete JSON is expected to be larger than tree-position status;
operator has authorized detailed raw memory outputs if useful, but
this first pass returns **code-linkage metadata only**, no RAM bytes.

## Next checkpoint

1. Categorize actual direct `Ball/Simulation/GolfKCol -> Tree` and
   `Tree -> collision utility` calls and dominant float member offsets.
2. Bound exact target function and register provenance around promising
   cross-object calls. Repeat over a second archive capture only if
   native source pointers or byte epoch differ unexpectedly.
3. Export private numeric tree hitbox only when native code + actual
   collision/visual fit agree; otherwise keep candidate centers in
   inspector as **non-physical markers**.
4. Separate restitution/friction/leaf-contact coefficients and
   trajectory response from shape; preserve source-versus-result
   identity and 100-ft censored outcomes in future gameplay experiments.

Training approved: FALSE. Physics semantics approved: FALSE.
