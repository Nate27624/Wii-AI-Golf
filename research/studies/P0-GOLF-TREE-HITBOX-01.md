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

## Original capture7 direct code linkage (operator, source/SHA gated)

Original operator callgraph result from `p0_tree_hitbox_source_callgraph_private.py`
reported:
- `RPGolMapObjBall -> RPGolMapObjTree`: **3 direct bl** at Ball unit-relative
  `+0x025C,+0x02C0,+0x231C`.
- `RPGolKCol -> RPGolMapObjTree`: **2 direct bl** at GolfKCol
  unit-relative `+0x1FC8,+0x21D4`.
- `RPGolMapObjBall -> RPGolKCol`: 5; `GolfKCol -> Ball`: 7;
  `Simulation -> Ball`: 16.
- Ball unit **34 indirect bctrl**. No direct proof these are
  collision tests or that all of them execute during one ball flight.
  `Tree -> CollisionChecker` did NOT appear in the direct-call report;
  indirect dispatch and GolfKCol ownership remain unexcluded.

**Interpretation:** Tree code is reached from both Ball and GolfKCol in
the original executable. That's considerably stronger than heuristic
collision guesswork, but identifying a shape or bounce/damping response
requires function/receiver and numeric instruction provenance.

## Targeted next static audit: exactly five verified source calls

`scripts/p0_tree_hitbox_five_calls_private.py` is a new read-only,
original seven-capture SHA/scene/84-byte-tree-loop gated script. It
checks all five reported `bl` callsites truly resolve into the public
`RPGolMapObjTree` source module; otherwise it abstains. It prints
**only 21 caller instructions around each site and 18 instructions
at the actual target** with source-unit-relative offsets and local
operator-only original code words. It decodes loads, stores, compares,
branches, floating instructions and frame setup as available, but
unknown instructions retain `undecoded`. It does **not** dump
runtime heap, native model assets, ball positions or private tree
coordinates and never writes original RAM or game state.

```powershell
py -3 -I scripts/p0_tree_hitbox_five_calls_private.py --archive 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE' --capture 7
```

**Evidence gate:** classify target tree methods by their actual PPC data
usage (model getter/position/collision callback/constructor/render etc.),
then search only validated function disassembly for shape math and
ball velocity changes. A constructor call or model getter must not be
misrepresented as collision merely because it targets tree code.

## Original operator five-call disassembly: NO hitbox identified (critical correction)

The exact 5 original calls to executable code compiled inside `RPGolMapObjTree.cpp`
were disassembled from source/SHA-gated capture7. **All 5 are generic math**:

| Caller source-relative BL sites | Callee in `RPGolMapObjTree.cpp` | PPC semantics |
|--|--|--|
| Ball `+0x025C,+0x02C0`, GolfKCol `+0x1FC8` | `Tree+0x0604` | Clamp float f1 to range [f2, f3], via `fcmpo`, `fmr`, and immediate returns |
| Ball `+0x231C`, GolfKCol `+0x21D4` | `Tree+0x0BF8` | Paired-single load/subtract/store vectors from r4/r5 to r3; no tree receiver or hitbox |

The link scanner was correct at native source-module level, but **NOT** evidence
of 5 true *tree-collider* calls. The compilation unit contains utility routines.
The KCol caller `+0x21D4` indexed triangle vertices with `lhz` and
`mulli +12` before generic vector subtraction — further evidence of normal
triangle processing rather than a special tree-object narrowphase.

Do not label `Tree+0x0604` or `Tree+0x0BF8` as tree collision handlers,
or infer collider geometry/velocity response from either.

## Next falsifier: actual Ball <-> GolfKCol cross-module calls

Source operator linkage still shows independent direct `bl`:
`Ball -> GolfKCol` **5** and `GolfKCol -> Ball` **7**. Such calls may
lead into ground collision, obstacle response, or irrelevant utility
math; **these are not proven contact functions**.

New independent read-only
`scripts/p0_ball_kcol_twelve_calls_private.py` scans the source public
`Ball` and `GolfKCol` bounded unit code, requires **exactly** those
original 5+7 linked callsites, and records native target offsets with
ten prior / eight following float access clues. Default prints a compact
JSON summary. `--detail` locally disassembles each source callsite with
ten instructions before, eight after, and 14 target-entry instructions;
it never dumps native RAM data, current tree XYZ, or images and never
changes Dolphin. Real archived capture7 original source 84-byte loop,
SHA and scene gates must all pass or the tool abstains.

```powershell
py -3 -I scripts/p0_ball_kcol_twelve_calls_private.py --archive 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE' --capture 7 --detail
```

Next: source-based receiver provenance, which function actually processes
a *tree* rather than terrain triangles, and any independently verified
collision geometry. No physical tree hitbox or response model is trainable.
