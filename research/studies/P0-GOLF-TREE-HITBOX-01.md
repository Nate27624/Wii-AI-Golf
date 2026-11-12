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

## Operator original 12-call PPC evidence: KCL query chain, not tree hitbox yet

The operator ran the original-capture 7 `p0_ball_kcol_twelve_calls_private.py
--detail` with strict native SHA/source gates. Returned 5 Ball -> GolfKCol
BL and 7 GolfKCol -> Ball BL. Actual source-relative PPC results:

- **Ball+0x05C0, +0x14D0, +0x27B0 -> GolfKCol+0x0000**:
  caller passes likely position/segment vectors through stack/args,
  then on first two paths compares returned `r3` against 0 and uses
  conditional branches. Native `GolfKCol+0x0000` is a function prologue
  and immediately calls `GolfKCol+0x1540` at `+0x0034`. **Likely KCL
  collision query path**, but still unproven whether it includes trees,
  the active course mesh, or only terrain/other intersections.
- **Ball+0x0B60 -> GolfKCol+0x1AC4**: native caller repeatedly queries
  based on return `r3` and a returned halfword `+0x0A(r1)`.
  `GolfKCol+0x1AC4` reads float `+0x54(r3)`, arranges pointers
  (including `r3+0x40`) and unconditional branches at `+0x1AE4` to
  **GolfKCol+0x2090**. This is an especially promising collision-query
  wrapper but **`+0x54` must not yet be labeled radius** without
  receiver field documentation and comparisons. Nearby
  `GolfKCol+0x21D4` indexes actual KCL triangle vertices by 12-byte
  coordinate vectors and calls a generic subtraction helper.
- **Ball+0x0AFC -> GolfKCol+0x1BB8**: KCL callee calls its own
  `+0x31F0` and loads a 3-float vector from argument `r4`;
  likely source-world/physics initialization but no contact proof.
- **Seven GolfKCol -> Ball direct BL** at GolfKCol `+0x1ED0,
  +0x24C8,+0x24D8,+0x251C,+0x252C,+0x2570,+0x2580`
  ALL target **Ball+0x15C4**. Native source PPC uses paired-single
  loads, multiplications, and paired-single stores: a *generic vector
  scaling helper*, not itself a physics response mutation. Do not
  classify as bounce/velocity update merely from code-unit name.

**Interpretation:** The KCL engine has demonstrable Ball caller links
that implement conditional geometric queries and contains indexed
triangle processing. But there is **still no source proof that the
94 tree objects are included in the KCL geometry**. Terrain has 2498
typed prisms with no explicit tree flag; that alone does not exclude
tree-containing triangles with other flags or other collision resources.
No leaf/trunk split, hitbox size, restitution or attenuation proven.

New purpose-built narrow source audit:
`scripts/p0_golf_kcol_collision_windows_private.py` verifies
source-native code fingerprints `GolfKCol+0x0034 -> +0x1540`,
`GolfKCol+0x1AE4 -> +0x2090`, and the `+0x21D4` vertex math helper
call, against original phase7 RAM SHA/scene and 84-byte source tree loop.
It then prints five **bounded** source-relative code windows:
`+0x0000..+0x00AC`, `+0x1540..+0x161C`,
`+0x1AC4..+0x1B3C`, `+0x2090..+0x21F4`,
`+0x31F0..+0x326C`, totaling **253** annotated words.
Outputs no RAM geometry, tree coordinates or code bytes to Git;
operator can invoke `--detail` to see private native words locally.

Next code review should establish caller r3 object class, KCL header/prism
pointer and active collision-geometry resource owner, and whether
tree positions participate in that source. If no provenance to tree
structures, avoid generalizing terrain KCL collision into tree hitboxes.
Training false.

## Original PPC KCL query/narrowphase receipt, 2026-11-10

Original SHA/scene-gated phase7 `p0_golf_kcol_collision_windows_private.py`
output identified:
- `GolfKCol+0x0000` query entry calls `+0x1540`, manages
  return `r3` and best-result numeric comparisons. This is a
  credible collision query, but no tree owner proven.
- `GolfKCol+0x1540` initializes KCL query state and cached output
  `r3+0x027C/0x0284`, writes a VEC3-like query position at
  `r3+0x0294/0x0298/0x029C` and stores `f1` at `+0x54`.
  Do not label the last float radius until correlated with KCL source
  struct and geometric usage.
- `GolfKCol+0x1AC4` loads `f1` at `+0x54(r3)`,
  points r4 at `r3+0x40`, and tail-calls `+0x2090`.
- `GolfKCol+0x2090` uses `r3+0x58` and vertex/prism pointers
  at `r3+0x04/+0x08/+0x0C`, caching leaf/candidate state
  `r3+0x027C`, then at `+0x21B8..+0x21D4` reads a
  16-byte indexed primitive and points to 12-byte float vertices.
  This is solid evidence of triangle geometry calculations, not
  evidence of 94 tree collision objects in the same dataset.
- `GolfKCol+0x31F0` subtracts three float components and converts
  results to integer bit operations, consistent with spatial
  octree/index or bounds filters. Exact purpose requires following
  remaining branches.

**Critical open question:** native `RPGolKCol` accesses what active
KCL resource? Is it solely the terrain surface KCL, or are tree
colliders a second KCL resource or separate object callbacks? The
previous 5 Ball/KCol calls into Tree source were proven generic math,
not tree collision. No trunk/canopy hitboxes or restitution verified.

### Independent test of the known 94 tree objects (next)

Added `scripts/p0_tree_hitbox_object_dispatch_private.py` to classify
the **first word** of each source-proven 0x54 tree object and see if
it plausibly indexes common runtime method dispatch slots leading
into public Tree/Ball/Sim/KCol code. It also reports source
`mModel+0x04`, `mMapObj+0x08`, and self-pointer checks at
`mpRotation+0x40`, `mpTrans+0x44`, and exact `mulli/addi 84`
instruction locations in Ball/Tree/Sim/FieldManager sources.
**No private firstword pointers, game code bytes or any XYZ are
published**. A common vtable or source-code stride use is a lead,
not a proven collision interface; the actual native method and
receiver must be traced before inferring geometry or response.

## Original operator 94-tree object-dispatch audit: mixed results / critical +0x40 pointer bug

Operator's source/SHA/scene-qualified capture7 result from
`p0_tree_hitbox_object_dispatch_private.py` returned:
- 94 native source tree objects, all sharing **one firstword value**
  in the MEM1 memory region; 20 candidate method-table slots
  included public FieldManager and Ball code-relative targets.
  This is a **possible shared vtable**, not verified: the
  pointed-to word/table identity and actual virtual call sites
  still need source-level provenance. Some Ball source module
  functions may be general-purpose utilities (known from prior
  disassembly), not tree physics!
- `mModel+0x04` and `mMapObj+0x08` raw words classified as
  `other_nonzero` in all 94 records by strict MEM1/MEM2 *aligned*
  pointer checker. This does NOT establish model/map object is
  absent. They might use non-address word representations, tagged
  pointers, stale header offsets, or unrecognized address regions.
- **The original tool had a confirmed logical layout error:** it
  checked candidate `mpRotation` at +0x40 and `mpTrans` at +0x44
  and found 0 selfreferences. But these offsets fall INSIDE the
  source documented `mScale:VEC3` at +0x3C–+0x47. Public
  `RPGolMapObjBase.h` annotations claim +0x40/+0x44 pointers,
  which overlaps scale and is internally inconsistent. Under
  normal NW4R `MTX33` (36 bytes) and `VEC3` (12 bytes) struct
  sizes, candidate pointer fields MUST instead be **+0x48/+0x4C**
  after scale. Confirm against real original record words and PPC,
  not just header comments. The old 0 selfreference report was
  invalid as an inference about the actual pointers.
- Ball executable source unit contains **one `addi +84` site**
  at public Ball relative **+0x0738**. Tree source module also
  has one at **+0x002C**. FieldManager has many known +84
  allocation/iteration sites. A naked addi immediate +84 does
  **not** prove Ball iterates the tree array: source register
  provenance must connect to `FieldManager.mTreeObjs` and
  loop counter/count.

**Corrective code:** `p0_tree_hitbox_object_dispatch_private.py`
now counts original source records' candidate pointer classifications
at +0x48/+0x4C, selfreference matches against native in-object
rotation(+0x0C) and translation(+0x30), source scale(+0x3C)
finite/spans, and aggregate nonpointer word hints. It remains
read-only, with no raw pointer or per-tree values published.
Also added `p0_tree_ball_84byte_context_private.py`, a
read-only source disassembly of **Ball+0x0640..+0x081C** and
**Tree+0x0000..+0x00BC**, strictly anchored to native
+84 ADDI instructions and original SHA/scene/tree PPC loop.
This can reveal whether Ball's +84 iteration actually accesses
the known 94 trees or unrelated structures. No tree collision
shape/branch/velocity response approved. Do not conflate
source-unit ownership and semantic method identity.

## Original +0x48 tree proximity flag and +84 shared-global offset (not tree stride)

The operator supplied an original source-qualified capture7 report and bounded
`Ball+0x0640..+0x081C` and `Tree+0x0000..+0x00BC` native disassembly.
Independently checked the call targets against public
[`RSPE_r1.map.csv`](https://github.com/kiwi515/ogws_info/blob/main/RSPE_r1.map.csv):

- Public symbol **`PSVECSquareDistance` at `0x800E86D0`**.
  `Tree+0x0030`, `Ball+0x0750` and `Ball+0x0760`
  all BL to exactly this function.
- **`Tree+0x000C`** takes source tree `mTrans +0x30`,
  passes `r4 = (global context->+0x334)+0x54` as other VEC3,
  calls `PSVECSquareDistance`, compares squared distance `f1`
  with native static small-data float `lfs f0,-14912(r2)`, and
  stores a one-bit result with **`stb r0,+0x48(r31)`** at
  `Tree+0x0044`. FieldManager's known 94-tree loop invokes the
  function at `Tree+0x000C`. This is **native source-proven
  per-tree squared-distance threshold flag computation**, but NOT
  evidence that the threshold means physical collision. It could
  indicate proximity/LOD/rendering/other state. The comparison
  constant's numeric value remains unresolved without validated r2
  small-data-base provenance.
- The `addi +84` at `Ball+0x0738` is NOT the same as the verified
  FieldManager tree-array stride. `Ball` reads a global context
  `+0x334` pointer and adds an internal **byte offset +84** before
  calling the same squared-distance function. `Tree+0x002C`
  also takes the shared-global `+0x334` and adds 84 before its call.
  Neither source module shows a 94-tree array iteration here.
- Corrected native `+0x3C/+0x40/+0x44` VEC3 scale reports **94
  finite vectors**, component ranges **1.0..2.64**. Therefore neither
  `+0x40/+0x44` (old header comments) nor guessed
  `+0x48/+0x4C` are verified transform-pointer pair fields:
  actual **+0x48 is a byte flag**, and was 0/94 for capture7
  in original full-word check. `+0x4C` remains 94 distinct raw
  words in source capture7, unknown type; the old selfref test
  was 0/94. The 94 common firstwords may point to a method table,
  but no native virtual dispatch or hitbox method is proven.
- `+0x04 mModel` and `+0x08 mMapObj` each had **2 distinct raw
  word patterns** across 94 objects, despite strict aligned pointer
  validator classifying both as other nonzero. These may correlate
  with different tree variants or memory layout; **do not claim
  model types until source object ownership is verified**.

New standalone `scripts/p0_tree_proximity_flag_private.py`
requires original exact 7-pair SHA and scene, 94x84 source array,
native squared-distance/tree-flag PPC instruction fingerprint.
It reports only aggregate (no raw XYZ/pointers/code words) source
byte+0x48 flag histograms across original captures 1,5,7,
`mScale` axis equality, +0x4C raw-word float/pointer pattern
counts, distinct pair groups of +0x04/+0x08 and public-source
code relative *syntactic* candidates reading +0x48.
**Any code reading +0x48 at a matching displacement may refer
to other object classes**: receiver identity must be proven.
No tree contact, native foliage/trunk hitboxes or bounce response
has been derived. Training false.

## Operator real phase1/5/7 source proximity flag results

Operator original SHA/scene-gated `p0_tree_proximity_flag_private.py` at
exact tested commit `6aa8aaed56eeaeefefc1154ca52eab717b3616f3`:
- `Tree obj byte +0x48` histogram **{0:94}** in **each of captures 1,
  5, 7**. This does not imply branch is unused or collision absent:
  the three captures did not observe a nonzero transition.
- `mScale VEC3+0x3C` components equal within tolerance in **76/94**
  tree objects and nonuniform in **18/94**.
- `mModel+0x04` and `mMapObj+0x08` each partition the objects
  into **72/22 groups** and paired joint group sizes **72/22**;
  compatible with two variants, but could be other resource categories
  or tagged representations. **Do not label species or hitboxes.**
- Unknown tree field `+0x4C` has **94 distinct raw words** across
  each source capture; no MEM1/MEM2 aligned pointer candidate, no
  nontrivial finite float in captures 1,5 and just one candidate in 7.
  Meaning/receiver type unresolved; do not infer a pointer or float.
- Syntactic PPC source scan (offset-only, no receiver CFG) sees
  `Tree+0x0044:stb +0x48(r31)` producer, **`Tree+0x0504:lbz
  +0x48(r30)`** candidate reader and **`FieldManager+0x0788:lbz
  +0x48(r3)`** candidate reader. The latter two are not yet proven
  to access the same class: `r30` and `r3` identities require
  native register-flow tracking. Other +0x48 hits in Ball/FieldManager
  are often **word accesses to entirely unrelated objects**.

New narrowly scoped, read-only source code reader
`scripts/p0_tree_flag_consumer_trace_private.py` prints **145 native
source-relative PPC instructions** in three bounded windows:
`Tree+0x000C..+0x0058` producer (20),
`Tree+0x0450..+0x05BC` candidate consumer (92),
`FieldManager+0x073C..+0x07BC` candidate consumer (33).
Validates original SHA/scene, source 94x84 tree owner, original
`PSVECSquareDistance` BL fingerprints, exact source producer word and
both source `lbz+0x48` receiving base registers. If anything changed,
abstains instead of guessing. Prints code words only to operator local
console, no heap/RAM coordinates/ROM blobs in Git.

**Priority:** classify actual r30/r3 receivers, conditional branches and
callee targets around `Tree+0x0504` and `FieldManager+0x0788`, then
decide whether flag is LOD/visibility vs collision candidate.
Even if the flag controls visibility, tree collisions could use an
independent KCL or object pathway. No tree collision semantics proven;
training remains false.

## Original operator 145-word +0x48 consumer trace — strong FALSE RECEIVER warning

Original SHA/scene/94-tree-gated capture7 `p0_tree_flag_consumer_trace_private.py
--detail` showed that both previously suggested native +0x48 byte
**readers require object identity verification** before attributing
them to the 94-tree source objects. In fact, the code now points toward
**different receiver types**:

- `Tree+0x047C` establishes `mr r30,r3` at +0x049C. It then
  reads `+0x24(r3)` as integer, passes `lwz +0x1C(r3)`,
  `lwz +0x20(r30)`, `lwz +0x28(r30)` as pointer-like arguments
  to the **same `RPGolMapObjBase.cpp+0x0B84` routine** at
  `Tree+0x04B0,+0x04B8,+0x04C0`. It calls
  `RPGolCamera.cpp+0x028C` at `Tree+0x04CC,+0x04EC`;
  writes two resulting floats into `r30+0x4C` and `r30+0x50`,
  then at `Tree+0x0504` loads byte `+0x48(r30)`.
  The source tree 0x54-byte records have the +0x1C/+0x20/+0x24/
  +0x28 space allocated to rotation matrix floats and +0x4C
  consists of 94 mostly nonfinite raw-word float candidates.
  **This receiver does not match the confirmed 94-tree structure**;
  do not claim Tree+0x0504 reads the true per-tree proximity byte.
  Its nonzero branch changes a shared global state and writes
  another object byte (+0x02). This is compatible with camera/
  animation/effect control, NOT proof of a collider.
- `FieldManager+0x0768` saves its original r3 receiver to r31,
  at +0x0784 **calls `RPGolCameraManager.cpp+0x02B0`**, then
  at +0x0788 loads `lbz +0x48(r3)` from the **callee return
  value**. There is NO source evidence that this r3 return points
  to a source tree record. Again **NOT a proven per-tree flag reader**.
- **The only definitively sourced per-tree byte +0x48 access remains
  `Tree+0x0044: stb r0,+0x48(r31)` after
  `PSVECSquareDistance` and a threshold comparison**, invoked by
  FieldManager for the 94 tree records. No verified same-object
  consumer. All 94 byte flags stayed zero in source phases 1/5/7.
- Source code attribution to `RPGolMapObjTree.cpp` **does not
  establish the class identity of r3/r30**, as previously demonstrated
  with generic clamp/vector-sub helpers in that code unit.

To falsify the alternative-struct interpretation using actual original
memory, new read-only `scripts/p0_tree_flag_receiver_disambiguation_private.py`
strictly fingerprints native code including these 6 BL target exact
public units, and uses the 94x84 source records to count valid aligned
MEM1/MEM2 pointers versus plausible 32-bit floats at
`+0x1C,+0x20,+0x24,+0x28,+0x4C,+0x50`.
It also inventories **direct callers** of true per-tree writer
`Tree+0x000C`, the separate candidate reader
`Tree+0x047C` and `FieldManager+0x0768` across seven
source units. No native pointers/individual XYZ/instruction words
are emitted, no live Dolphin or game writes. If the record fields do
not resemble the consumer's expected pointer/float layout, the
hypothesis is disfavored. All native tree collider radii, height,
canopy response and contact physics remain unverified. Training false.

## Native capture7 +0x48 flag receiver disambiguation: negative evidence

Operator executed `p0_tree_flag_receiver_disambiguation_private.py`
original SHA/scene/94x84-source-qualified at `f55f83db3e8c5a0a2015ecc9627d63ff38cdef08`:

- Native direct calls to the 94-tree distance writer `Tree+0x000C`:
  **FieldManager+0x2BB4** (the verified 94-tree source array loop).
- A separate native direct call to the candidate reader
  `Tree+0x047C`: **FieldManager+0x230C**. It is NOT the same
  callsite or loop as the source 94-tree writer. Common compiled
  source-unit name does not prove same receiver.
- No direct caller of `FieldManager+0x0768` within the scanned
  relevant units; this is NOT evidence the function cannot execute
  via indirect or out-of-unit dispatch.
- 94 native tree records at `+0x1C,+0x20,+0x24,+0x28` each
  qualify as both **94/94 aligned bounded MEM2 pointer words**
  and **94/94 loosely plausible float32 words**. These categories
  overlap numerically; a pointer can decode as a tiny finite
  floating-point value, so classification is **ambiguous** and
  should not be interpreted as verified rotation matrix values
  or actual pointers without native dereference provenance.
- The same records at `+0x4C` and `+0x50` each have **only
  1/94 loosely plausible finite float32**, and neither holds
  qualified aligned MEM1/MEM2 pointers. Yet the reader routine
  `Tree+0x047C` explicitly **writes float32 to these two fields**.
  This is strong evidence the receiver belongs to a **different
  object type** (or a different lifecycle layout). It makes the
  earlier proposed 94-tree producer -> same-object reader
  relationship unsupported and unlikely for these captures.
- The reader function calls `MapObjBase+0x0B84` and
  `Camera+0x028C`; the other source `FieldManager+0x0788`
  reads byte `+0x48` from the **return of CameraManager+0x02B0**,
  not from an identified tree pointer.
- No tree hitbox, trunk/foliage geometry or bounce/velocity contact
  coefficients have been recovered. The source tree proximity flag
  is not shown to participate in collision. Keep rendering markers
  without any physical shape inference; training not approved.

Follow-up source-gated, read-only
`scripts/p0_fieldmanager_tree_caller_receivers_private.py` resolves
and disassembles both exact **FieldManager+0x230C -> Tree+0x047C**
and **FieldManager+0x2BB4 -> Tree+0x000C** code paths. It prints
four bounded caller/callee windows totaling 169 PPC instructions,
only to the operator's own terminal. Validates original seven-pair
SHA, scene, 94 source trees, original 84-byte PPC tree loop, exact
native flag writer/camera-helper fingerprints and both native call
targets. A positive result should identify where the receiver r3
comes from in the two different FieldManager contexts and establish
whether the two call receivers could be the same object type. No
native RAM, positions or model art is emitted to Git; no game writes.

## CRITICAL correction: FieldManager+0x230C also loops 0x54-byte source objects

Operator provided original capture7 SHA/scene/source-bounded native PPC code for
both FieldManager callers. **This REFUTES the earlier conclusion that
`Tree+0x047C` almost certainly receives some other object type.** The
actual caller's iteration is directly aligned with the known 94-tree source
array:

```asm
FieldManager+0x22EC lwz  r3, -23328(r13) ; shared global object
FieldManager+0x22F8 lwz  r29, +12(r3)    ; second argument pointer
FieldManager+0x2300 lwz  r0, +32(r31)    ; +0x20 candidate tree array
FieldManager+0x2304 mr   r4, r29        ; additional argument
FieldManager+0x2308 add  r3, r0, r26    ; current 84-byte element
FieldManager+0x230C bl   Tree+0x047C   ; calls source method on element
FieldManager+0x2310 addi r26,r26,+84
FieldManager+0x2314 addi r30,r30,+1
FieldManager+0x2318 lwz  r0,+28(r31)    ; +0x1C candidate count
FieldManager+0x231C cmpw r30,r0
FieldManager+0x2320 blt  FieldManager+0x2300
```

Known per-tree distance flag writer:

```asm
FieldManager+0x2BAC lwz  r0, +32(r28)  ; +0x20 source array
FieldManager+0x2BB0 add  r3, r0, r31   ; current 84-byte element
FieldManager+0x2BB4 bl   Tree+0x000C
FieldManager+0x2BB8 addi r31,r31,+84
FieldManager+0x2BBC addi r30,r30,+1
FieldManager+0x2BC0 lwz  r0,+28(r28)   ; +0x1C source count
FieldManager+0x2BC4 cmpw r30,r0
FieldManager+0x2BC8 blt  FieldManager+0x2BAC
```

**Evidence ranking:** both use the same +0x20 pointer field, +0x1C
count, and +84-byte elements. The earlier original code established
source FieldManager fields as 94x0x54 tree array. Writer's receiver
`r28` is explicitly saved from `r3` at `FieldManager+0x2B80`.
The second loop uses `r31`, whose actual reaching definition has not
yet been examined. **Same array is highly likely, not yet 100% proven
without tracing r31's provenance and seeing that it is the same
FieldManager class/instance.**

The second routine `Tree+0x047C` writes floats to element +0x4C and
+0x50 and reads flag byte +0x48, after calling MapObjBase functions and
a camera-compiled helper with the element position +0x30.
The previous 94-record captures had almost no sane float candidates
at +0x4C/+0x50; that observation may reflect *before update*,
uninitialized values or different state epoch, rather than a different
receiver class. It is **NOT valid** to use snapshot-field values alone
to exclude the second loop's source object identity.

The global second argument originates at `lwz global,-23328(r13)`,
then `lwz +0x0C(global)` (r29). Its semantic class, camera vs ball
vs another entity, is **unproven**. The callee called from the tree
method is compiled in RPGolCamera.cpp, but source-unit attribution
alone does not establish its purpose (we previously debunked the
source-unit name heuristic for generic clamp/vector-sub math).

**Now highest-priority next research:** Read-only bounded original
archive PPC routine `scripts/p0_tree_second_loop_geometry_private.py`
traces (1) prologue candidates for r31's FieldManager receiver,
(2) exact +0x230C/+0x2BB4 loops,
(3) full Tree+0x047C..+0x0620 branch and response code,
(4) first instructions of the MapObjBase+0x0B84 and
Camera+0x028C callees. Strict source SHA/scene/94x84/BL anchors,
no RAM/coords or native code committed. Does not infer a trunk radius,
canopy hitbox or physical response merely from these calls. Training
still false.

## Original phase7 second tree-loop + camera math native receipt

Operator ran original SHA/scene-qualified `p0_tree_second_loop_geometry_private.py --detail`
and supplied **both** loops and full `Tree+0x047C..+0x0620`
body, native Camera+0x028C and MapObjBase+0x0B84 targets:

- `FieldManager+0x2300` loads `+0x20(r31)`, forms
  `r3=base+r26`; `+0x230C` calls `Tree+0x047C`; `+0x2310`
  increments element by 84; `+0x2318` reads
  `+0x1C(r31)` as count. This **directly agrees** with the
  known writer `FieldManager+0x2BAC..+0x2BC8` which iterates
  same +0x20-array,+0x1C-count, +84 stride using r28. This
  *corrects and supersedes* an earlier false conclusion that
  the +0x48 reader had to target another struct because
  its +0x4C/+0x50 values were mostly nonfinite in the captured
  records. Those fields are explicitly overwritten as float
  values during this tree-update routine and may be uninitialized
  or stale in static capture. Still need confirm owner register.
- Source `FieldManager+0x22EC` loads a shared global pointer and
  `+0x22F8` takes its `+0x0C` member as additional argument
  `r29`; `+0x2304` passes it via `r4` on every tree iteration.
  Actual dynamic type/role not proven.
- `Tree+0x047C` receives `r3` element and `r4` additional
  pointer. It first conditionally exits based on element
  `+0x24`, obtains 3 source objects from `+0x1C,+0x20,+0x28`
  and passes each through `RPGolMapObjBase+0x0B84`, which
  loads a pointer at **+0x04 of each resource object** and
  tail-jumps to an external helper. This gives **source-code
  evidence that at least some of these offsets behave as
  pointer-like model/resource handles in this routine**, rather
  than matrix coefficients. It does not identify collision
  vs visual geometry.
- `Tree+0x04C4..+0x04D8` calls
  `RPGolCamera+0x028C` with extra argument and
  `element+0x30` tree position; stores a resulting float
  to tree `+0x4C`. Code compares a floating-point result
  to a source constant; if admitted, repeats this function,
  storing another float at `+0x50`. `Camera+0x028C`
  reads `r3+0x40` as a pointer to a reference vector,
  `r3+0x38` as a float and loads two horizontal
  components from the reference point and tree location.
  It computes horizontal positional differences and
  floating-point math. This is compatible with camera
  effects/proximity; **NOT a verified ball collision test**.
- `Tree+0x0504` now plausibly reads the SAME tree object's
  native `+0x48` distance flag, then conditionally updates
  a global timer/counter with source maximum 180 and writes a
  byte to a referenced object. Later branches use `+0x50`
  float, clamp values through `Tree+0x0604` (known generic
  clamp), and update another global value. Source-native
  geometry and state updates, but NO observed ball receiver,
  ball velocity write, tree collider radius or canopy split.
  Do not name the updated byte or global value a hit indicator
  without its owner class or gameplay state source.
- Source `r31` receiver origin: bounded original scan finds
  `mr r31,r3` at `FieldManager+0x214C` and only one
  stack prologue at `+0x2138` in the upstream relevant
  function span. This **strongly supports** second-loop
  receiver being FieldManager method's `this` pointer.
  New tightened native audit adds exact +0x214C source
  register anchor, prologue structural check, scan for
  unexpected intervening new stack frame and prints
  +0x2130..+0x215C entry disassembly. It does not falsely
  claim complete CFG proof or collision semantics.

**Key distinction:** The second routine almost certainly belongs to
*tree update / visibility / effect state*, not yet identified as
tree hitbox physics. Further direct evidence would require a
ball contact query traversing the tree-owned structures or KCL
geometry associated with source tree positions and ball-velocity
response. A camera-relative scalar used for visual/effect
thresholds must never be treated as physical collision radius.

## Source-owner recovery: RPGol tree second 84-byte loop is graphics/model update evidence, not contact response

Public `research/source_maps/RSPE01_01_public_text_units.json` original
Rev1 source map was used to resolve PPC relative targets from real
operator disassembly:

| Call | Original native destination source owner |
|--|--|
| `Tree+0x04B0/0x04B8/0x04C0 -> MapObjBase+0x0B84` | Helper loads `+4` from object and tail-branches to `RPGrpModel.cpp+0x02B0` (native `0x801A9B10`) |
| `Tree+0x04CC/0x04EC -> Camera+0x028C` | `RPGolCamera.cpp+0x028C`; horizontal source position arithmetic (X/Z) using camera-owned reference pointer and float |
| `Tree+0x0560` | `nw4r/math/math_arithmetic.cpp+0x0118` |
| `MapObjBase+0x0BC4` (nearby separate model animation helper) | `RPGrpModelAnm.cpp+0x04A8`; indirect vtable dispatch also present in helper |

The second `FieldManager+0x230C` loop's `Tree+0x047C`
routine operates on three graphics/model objects from
`tree+0x1C,+0x20,+0x28`; it accesses the tree location
`+0x30`, calls camera-owned horizontal geometry math twice,
stores scalar state at `tree+0x4C,+0x50`, conditionally
checks byte flag `tree+0x48`, modifies a global timer-like
state and writes a byte through another model/resource pointer.
The larger evidence set now **strongly favors tree visual/update
and effect/LOD state, NOT a ball-contact solver**. This does NOT
prove the tree graphics never contribute to collision elsewhere
or rule out a separate obstacle KCL resource/collider.

**Implications for OGWS hitbox research:** Do not treat camera
distance scalar `+0x4C/+0x50` as trunk radius, collision
attenuation or foliage size. No code shown reads ball position,
returns collision penetration, uses a geometric collider shape,
or writes ball velocity in the `Tree+0x047C` path. The
`Tree+0x000C` squared-distance flag producer is native source
confirmed and the next reader now strongly source-linked to 94
tree objects, but the flag's gameplay effect is visual/unknown,
not a verified hitbox.

**Next distinct direction:** source-proven ball→KCol query,
KCL octree/triangle resource ownership and whether original
candidate 2,498 KCL prisms include vertical/obstacle triangles
spatially aligned with source-known 94 tree centres. If no
evidence of tree triangles, inspect alternate collision
resources rather than invent cylindrical hitbox proxies.
Keep nonphysical inspector tree markers and training false.

## Independent original-KCL-vs-tree geometry broadspatial falsification

After source-resolving `Tree+0x047C` to graphics-model and
camera processing (not a proven ball contact solver), a separate
read-only source audit is needed to test whether the *candidate*
2,498-face course KCL mesh contains obstacle-like geometry near
the 94 native source tree positions.

Added `scripts/p0_tree_kcl_spatial_broadphase_private.py`:
- Source-qualified original RSPE01 Rev1 seven-pair archive
  SHA, selected scene, **94x0x54 tree objects**, and exact
  source PPC original tree stride.
- Scans source MEM1/MEM2 for a **unique** original candidate
  KCL header, parses and validates all **2,498** 16-byte
  prism records, original indexed vertices/normals,
  `height` reconstruction, finite geometry and cross
  product area. Requires **exact original 9-flag histogram**
  `{1:208,2:585,3:301,4:508,5:44,6:478,7:7,9:99,C:268}`.
  Any missing/ambiguous source KCL candidate abstains.
- Reconstructs candidate 3D triangles, selects relatively
  vertical faces by `abs(face normal y)<=0.40`, and examines
  only aggregate projected **XZ axis-aligned triangle BBOX
  LOWER-BOUND distances** from known 94 tree centres under
  independent 25,50,100,200 SOURCE-UNIT windows and
  `max face height above tree origin>=0,25,75` SOURCE-UNIT
  thresholds. This is NOT a geometric collision test;
  the chosen windows are explicit **search regions**, not
  guessed game hitbox radii or gameplay ranges. XZ AABB can
  overstate proximity to a triangle. It also counts results
  at **source tee and pin** as two non-tree control points.
- Reports per-window number of trees with any / >=5
  candidate elevated vertical faces, median/max face count,
  source-flag histogram, and tee/pin controls. Does not
  publish any tree XYZ, triangle vertices, native RAM
  addresses, original executable code bytes, object records,
  or any private 3D assets. No Dolphin or game writes.
- This test cannot establish *active KCL octree ownership*
  or prove that a nearby vertical face belongs to tree
  collision rather than cliff/terrain geometry. It also
  cannot rule out a separate tree collision resource.
  **Only use its outcome to prioritize native collision
  ownership/radius investigations.** Keep all physics
  and training approvals false.

User can run after exact-head offline CI passes, with
`py -3 -I scripts/p0_tree_kcl_spatial_broadphase_private.py
--archive <ORIGINAL_PRIVATE_SEVEN_PHASE_ARCHIVE> --capture 7`.
All original positions/geometry stay local. The outcome
is *candidate collision mesh overlap*, not a tree-hitbox
reconstruction.

## Original capture7 94 tree / candidate 2498 KCL near-vertical broadphase: ALL ZERO

Original operator ran SHA/scene/source-PPC-qualified
`p0_tree_kcl_spatial_broadphase_private.py` at exact
`1753d7edd5f6573131b60ebfc67066a43e045f37` against
private seven-phase 2026-10-28 archive. Returned:
- 94 verified tree objects, 2,498 original source-typed KCL
  prism triangles, **128 near-vertical faces** with
  `abs(original face normal Y)<=0.40`.
- Across all 12 combinations of **XZ triangle bounding-box
  distance lower bound <=25,50,100,200 source units** and
  height condition max triangle Y >= tree centre Y
  +0, +25, +75 source units:
  **0/94 trees** had ANY qualifying candidate face,
  median/max qualifying faces per tree **0**; the source
  tee and pin controls also each had **0** qualifying
  faces. No native tree hitbox identified; training false.

**Do NOT interpret the negative result as verified independent
tree collision shapes.** The test expressly did not validate
that the 2,498-prism KCL and the source tree object array
are in the same *active world coordinate frame*, nor that
the KCL octree is used by the ball query. A normal-Y
threshold, the "face above tree centre" gate and the 200-unit
window could all exclude relevant geometry.
The tee/pin controls were filtered to **near-vertical faces
too**: zero control counts do not demonstrate tree/KCL
world alignment, especially if tee and green are horizontal.

Follow-up **KCL frame/filter diagnostic**, with independent
original archive SHA/scene and 94x84 PPC source gates and
exact unique 2498-prism typed KCL ownership still unverified:
`scripts/p0_tree_kcl_frame_diagnostics_private.py`.
It computes aggregate tree vs mesh **axis AABB ranges/spans
and coordinate gaps**, nearest **XZ and 3D triangle AABB
distance LOWER BOUNDS** for (i) all 2498 prisms (ii)
near-vertical subset, **no elevation gate** (iii)
near-horizontal subset, plus **tee/pin each** as
positive-control reference points. It explicitly measures
the cascade near-vertical vs +0 source-centre height gate
at 50/200/500 source-unit *search windows*. It does
not report per-point XYZ or triangle vertices. Synthetic
tests cover positive controls, artificial frame shifts,
elevation-filter false negatives and noncontact disclaimer.
All distance outputs are source geometry hypotheses,
NOT collision radii or hitbox dimensions.

Interpretation plan:
1. If tee/pin are far from **all** KCL triangles, immediately
   investigate active course mesh origin/transform/scene
   ownership; the zero near-tree finding is not meaningful.
2. If tee/pin align with ordinary course terrain but tree
   centres align only with horizontal ground triangles and
   none of 128 vertical faces even without elevation gate,
   candidate KCL appears **terrain-specific**; then seek
   other tree collision/graphics geometry source and
   native ball contact dispatch.
3. If many near-vertical faces become nearby after dropping
   the height gate, earlier test was a false negative and
   must be recalibrated before branching into independent
   colliders.

All training approvals remain false and inspector trees
should remain explicit nonphysical markers.

## Real original phase7: all-face KCL aligns strongly with tee/pin and trees, but AABB caveat

The operator ran source+SHA+scene+94x84 tree-loop and exact original
2498-prism KCL source-gated
`p0_tree_kcl_frame_diagnostics_private.py` from validated
`1a9673ca3a82fbf6c7302bb527a326aa6e434124`:

- Original 94 tree locations, tee and pin control positions and
  reconstructed 2498-prism mesh occupy **overlapping X/Y/Z
  aggregate coordinate ranges** (axis gap 0 for all 3).
- Using **ALL 2498 faces without elevation/normal filters**:
  tee, pin and all **94/94 source trees** have nearest
  projected XZ **triangle AABB LOWER BOUND 0**. Tee/pin
  3D triangle AABB lower bound 0; source trees'
  nearest 3D triangle AABB bounds minimum 0, median 0,
  maximum **1.9 source units**. This is strong aggregate
  evidence of a compatible terrain coordinate frame,
  but **AABB overlap is not actual triangle contact**.
- Source face categories: **2363** near-horizontal
  faces (abs face normal Y >=0.80), **128** near-vertical
  faces (abs face normal Y <=0.40), 7 intermediate.
  Near-horizontal subset alone gives exactly the same
  tee/pin/tree aggregate 3D AABB minima as *all* faces.
- Nearest **near-vertical face** from tree locations:
  projected XZ AABB lower bound min **76.77**,
  median **668.05**, max **1581.24** source units.
  3D AABB lower bound min **77.97**, median **669.45**,
  max **1581.27**. **0/94** source trees are within
  50 units of a near-vertical bounding box.
  At <=100 units: 1/94; <=200: 10/94; <=500:
  32/94 XZ (31/94 3D); <=1000: 75/94.
  Tee/pin nearest vertical-face 3D AABB lower bounds:
  **293.19** and **209.01** source units.
- Original strict elevated-face filter made all-tree
  vertical proximity counts zero <=200. Removing
  elevation check yields **10/94 within 200 source units**
  and **32/94 within 500** (versus 8/94 elevated).
  Prior all-zero conclusion was at least partly
  caused by the elevation gate. Do NOT infer absence
  of vertical geometry from that filtered result.

**Interpretation:** compatible course terrain coordinate frames
are strongly supported by all 94 tree centres + tee/pin controls,
but the existing reconstructed candidate mesh looks dominated
by horizontal course terrain, with only 128 vertical faces
not clustered tightly around the trees at these search scales.
This is **negative evidence for this candidate KCL being a
high-detail trunk/leaf collider mesh**, not evidence that
trees are physically absent or that a second collider
resource is already proven. Active Ball KCL octree
and separate model collision logic remain unresolved.

### New exact triangle tests (unfiltered and positive controls)

Added `scripts/p0_tree_kcl_exact_triangle_distance_private.py`
and synthetic tests. The original source-gated KCL parser now
has backwards-compatible `include_vertices=True` option
to retain reconstructable **operator-private triangle vertex
triplets in memory** instead of only AABBs. The new script
computes the exact distance to those reconstructed triangles
(in 3D and their XZ projection) for each source tree/tee/pin.
It also counts XZ-projected actual near-horizontal face
coverage and signed source Y clearance to projected faces
at tree/tee/pin points. The latter helps detect whether
the parser creates correctly oriented triangles vs
overly large bounding boxes. It reports *only aggregate
counts/min/median/max and source flag summaries*; no
individual XYZ, vertices, KCL objects, RAM addresses,
original instruction words, model assets or other private
values are published or committed. Tests explicitly
cover AABB overlap when true triangle distance is
positive, projected vertical degenerate lines,
true surface barycentric coverage, synthetic frame
controls and fail closed on mismatch.

**No hitbox inference permitted:** exact Euclidean
point-to-KCL-triangle distance is still NOT
a tree collision contact test; active game
octree ownership and physics reaction remain
unverified. No physical trunk radius, foliage
height or restitution inferred. Keep training
unapproved and visual tree markers nonphysical.

## Original phase7 **exact** 3D/XZ triangle reconstruction proves 94 tree origins follow terrain

Operator source- and SHA-gated real capture 7 using
`p0_tree_kcl_exact_triangle_distance_private.py` at exact
`cdb09279c48967f1281805210e0fe84abc5835eb`
confirmed actual original 2498-prism vertex reconstruction:
- **94 of 94** tree locations project **inside the footprint of an
  actual, not only AABB, near-horizontal course KCL triangle**.
  Same is true for tee and pin.
- Tree nearest *actual* source KCL 3D triangle distance:
  **min 0.004, median 0.649, max 4.743** source units;
  signed Y clearance tree origin above nearest ground-like
  triangle: **min -4.842, median -0.657, max +0.473**;
  all 94 under 5 absolute vertical units from some course
  triangle with XZ footprint coverage.
- Tee actual 3D triangle distance **0.503** (flag
  `0x0001` FAIRWAY); pin actual 3D triangle distance
  **0.047** (flag `0x0006` GREEN). Tee/pin XZ projections
  also inside actual horizontal triangles.
- Tree nearest actual 3D KCL material flags:
  **22 ROUGH `0x0002`**, **72 OUT-OF-BOUNDS `0x0004`**.
  This 72/22 surface split coincides in MARGINAL totals
  with the original tree-object raw +0x04/+0x08 word
  group partition **72/22**. It is **NOT yet proven
  that the same 72 individual trees form the same
  resource group**: needs per-tree PRIVATE cross-tab.
- Original KCL **128 near-vertical** triangles have
  actual tree-origin 3D distances **min 99.536,
  median 676.515, max 1588.122** source units.
  Exact projected XZ min **98.472**, median
  **675.970**, max **1588.088**. **0/94** tree
  centres are within 50 units in actual 3D or XZ
  triangle distance; **1/94 <=100**, **9/94 <=200**,
  **30/94 <=500** source units.
  Nearest near-vertical surface for each tree
  has flag **`0x000C` CLIFF** (94 of 94).
  Tee/pin nearest vertical faces also `0x000C`,
  at 309.613 / 213.433 units actual 3D
  respectively.
- KCL contains **2363 near-horizontal** faces;
  for tee, pin and every tree, nearest actual KCL
  point comes from a near-horizontal face.
- The earlier AABB-only premise is now independently
  validated as compatible terrain alignment by
  exact barycentric XZ coverage and actual small
  signed Y/3D distances. **This strongly supports
  candidate KCL as ground/terrain geometry, not
  detailed obstacle trunk/foliage surfaces.**
  Caveat: the recovered 2498 source prism KCL's
  **octree membership in the native ball collision
  query remains unproven**, and no separate
  actual tree collider has been identified.

**Do not misinterpret:**
1. The 72/22 marginal match is *not* per-tree
   resource/ground correlation proof.
2. A tree origin on OOB or rough ground is
   *not* proof of no actual collision with
   leaves or trunk, nor proof of a distinct
   tree hitbox resource.
3. “99.536 units to nearest vertical cliff”
   is NOT a collision radius; many other
   collision mechanisms may exist.
4. No native ball-tree contact, tree geometry
   shape, canopy damping, restitution or
   learning labels have been proven.

Added read-only original `scripts/p0_tree_kcl_surface_group_join_private.py`,
strictly requires same SHA/scene/94x84 source tree PPC
and unique 2498 typed KCL prism source. It builds a
PRIVATE per-tree join of source raw object `+0x04/+0x08`
word-pair group membership with the nearest exact
3D KCL terrain flag and reports ONLY an anonymous
2x2 group-vs-`ROUGH/OOB` aggregate contingency
table, scale anisotropy and median ground distances.
Synthetic tests deliberately include **equal
72/22 marginal counts but an imperfect cross-tab**,
to prevent claiming agreement from totals alone.
No game memory addresses, original tree XYZ,
individual records or private triangle vertices
are ever emitted to repo or console; source
values stay local. Tree hitboxes and training false.

## Original capture7 94-tree terrain-group joint result and native ball contact pivot

Operator ran original SHA/scene/native 94x84 source-gated
`p0_tree_kcl_surface_group_join_private.py` and supplied the
private aggregate result:

| Original tree raw +0x04/+0x08 resource-word pair | Rough 0x0002 | OOB 0x0004 | Count | Nonuniform scale |
|---|---:|---:|---:|---:|
| Larger anonymous word group | 22 | 50 | 72 | 16 |
| Smaller anonymous word group | 0 | 22 | 22 | 2 |
| Total | 22 | 72 | 94 | 18 |

**The 72/22 resource-vs-terrain marginal match is NOT a per-tree
categorical mapping.** Both groups contain OOB trees; the
72 group also has all 22 rough trees. Neither group is a
verified tree species or collider type. The 2498 candidate
KCL faces reproduce terrain under all 94 tree origins but
none of the 128 near-vertical faces come within 50
source units of the tree centres on actual triangle
geometry. The candidate KCL looks terrain-focused,
but absent independent active KCL octree membership,
this does not prove there is a separate tree collision
resource or that trees have physical collision at all.

**Focus shifted to NATIVE Ball → GolfKCol postcall
semantics**, separate from the other agent's
[visual-only tree inspector issue #431](https://github.com/Nate27624/Wii-AI-Golf/issues/431).
Earlier operator native source+SHA gated
`p0_ball_kcol_twelve_calls_private.py --detail` verified
5 + 7 cross-compiled-unit calls; the 7 GolfKCol→Ball
calls are all to the generic vector scaling helper
`Ball+0x15C4`, NOT proof of ball mutation.
Exact five original Ball→GolfKCol BL pairs recovered
from operator's recorded source receipt:

| Ball source-relative BL site | Original KCol source-relative target |
|---|---|
| +0x05C0 | +0x0000 |
| +0x0AFC | +0x1BB8 |
| +0x0B60 | +0x1AC4 |
| +0x14D0 | +0x0000 |
| +0x27B0 | +0x0000 |

`GolfKCol+0x0000` had native query dispatcher
`+0x1540`; `+0x1AC4` reads source `+0x54(r3)`
and tail branches to `+0x2090` indexed triangle
processing. `+0x1BB8` reaches a source
`+0x31F0` spatial helper. These are real source
graph edges but do NOT yet establish that a
specific game KCL octree is the active ball
resource, or that a return means tree hit.

New read-only `scripts/p0_ball_kcol_postcall_context_private.py`
requires the original seven-pair SHA, scene and
94x84 FieldManager loop; **exact 5+7 source calls AND
all five precise BL caller/target offset pairs**
before printing up to 15 pre-call + 36 post-call
Ball instructions and 34 KCol target instructions
for each. Reports syntactic compare, branch and
store sites near the calls separately from
verified receiver/return dataflow. Native PPC
opcodes printed locally only with `--detail`;
no private heap/positions/triangle mesh/source bytes
committed. No inferred ball velocity mutation,
tree collision geometry or trainable labels.

Primary next falsifiable question: for each Ball
BL to KCol, what native function data/geometry
is passed, which return/status is tested,
and where (if anywhere) a collision result causes
a write to the ball's velocity/position?
Tree contact remains UNVERIFIED, training false.

## Original phase7 source-qualified Ball→GolfKCol return/flag and vector stores

Operator executed `scripts/p0_ball_kcol_postcall_context_private.py
--detail` on exact original source/SHA/scene/94x84 PPC-gated
capture7, and supplied all five native caller/target windows.
These refine **actual ball→KCL query flow**, NOT tree hitboxes:

- `Ball+0x05C0 -> GolfKCol+0x0000` passes stack
  query/output pointers via r4/r5/r7 and zeros via r6/r8.
  **`Ball+0x05C4 cmpwi r3,0`** immediately
  branches to `Ball+0x06A4` if zero. In the other
  branch, it loads query coordinates from stack and
  records 3-component float values in a shared global
  12-byte-stride ring buffer; the pointer and counts
  at `r13-23296` require source owner proof. No
  hitbox or ball-velocity write demonstrated here.
- `Ball+0x0AFC -> GolfKCol+0x1BB8` is a source
  **query-object configuration** call, not a
  post-return hit handler:
  `GolfKCol+0x1BB8` invokes its own
  `+0x31F0` spatial helper; stores a 3-component
  stack-supplied vector into source receiver
  `+0x40,+0x44,+0x48`, pointer/state at
  `+0x58`, and float `+0x54`.
- `Ball+0x0B60 -> GolfKCol+0x1AC4` enters
  the wrapper that forwards to original
  KCL triangle processor `+0x2090`. Caller
  **tests r3 for zero** at `+0x0B64`, and
  if nonzero reads a **u16 classification
  from stack+0x0A** at `+0x0B6C`.
  If zero, it repeats query at `+0x0B4C`.
  If nonzero, `Ball+0x0B78` is source
  PPC `slw r0,r30,r3` and `+0x0B7C`
  is `and. r0,r0,r28` (branch to
  `+0x0C1C` when mask matches);
  other branches explicitly compare the same
  halfword against **13** (`+0x0B84`) and
  **7** (`+0x0B90`). These are **control
  flow classification values, not yet proven
  to be the native KCL primitive flag itself**,
  nor evidence for a dedicated tree collision
  class. Existing candidate course KCL 2498
  prism histogram has no literal 13, but a
  source category 13 may be synthetic/sentinel
  or belong to separate collision logic.
  Require the native producer/consumer path
  through KCol before assigning semantics.
- `Ball+0x14D0 -> GolfKCol+0x0000` immediately
  tests **return r3 != 0** at `+0x14D4`;
  then reads a **different stack u16 at
  +0x08** and compares to **7** and **12**
  at `Ball+0x14F4/+0x14FC`. When neither
  excluded class matches, it copies the
  three floats from stack+0x4C,+0x50,+0x54
  into **`r23+0xAC,+0xB0,+0xB4`** by
  native `stfs` at `+0x1508/+0x1510/+0x1518`.
  This is a source-proven Ball-unit
  object-member **three-component vector
  store**, NOT yet a proven velocity field.
  Other code elsewhere may read these members
  as contact normal, reference location, or
  cached collision geometry. Read
  reaching definitions and consumers before
  naming the vector.
- `Ball+0x27B0 -> GolfKCol+0x0000` has
  **no immediate r3 result check** in
  the supplied 36-word postcall window.
  It copies stack/output vectors into
  separate objects accessed from
  `r31+0x19C` and `r31+0x198`,
  indicating source state propagation,
  not by itself ball contact.

All five direct Ball→KCol sites and seven
reverse calls match original. The seven
GolfKCol→Ball calls earlier were verified
to target a **generic vector-scaling helper**,
not physics response as the caller unit name
alone would suggest.

### Next targeted native source falsification

`scripts/p0_ball_kcol_material_branch_private.py`
source-gates the original archive, exact five
callsite/target pairs, 94x84 source array,
and exact native PPC anchors for material
halfwords, mask/branch, checks 7/12/13,
three stores `r23+0xAC/+0xB0/+0xB4`.
With `--detail`, locally prints bounded
original Ball branch targets
`+0x0BF4`, `+0x0C1C`, `+0x0E68`,
event helper `+0x01B8`, KCol result
handler `+0x0120..+0x024C` and
narrowphase `+0x2090..+0x223C`.
Also reports syntactic Ball-unit
accesses to +0xAC/+0xB0/+0xB4,
without falsely attaching same-offset
accesses to the same object.
Original private code words are emitted
to operator terminal **only**;
repository includes static-source
decoder and synthetic-only tests.
No claimed tree-specific collision
class, trunk/canopy dimensions,
object contact, or ball velocity
impulse. `training_approved=false`.


## Original phase7 Ball-KCL prism type producer and state-copy falsification

Operator ran the exact source-gated `p0_ball_kcol_result_provenance_private.py
--capture 7 --detail` from commit
`26a1fee208a5270640547d30834e53b0120a63f9`
on the **original** private seven-pair archive; 94x84 tree loop,
scene/SHA, prior 5+7 Ball/GolfKCol exact direct edges and original
PPC source anchors all PASSED. The 592 bounded code words
were observed **locally only**, not committed. This provides new
positive classifications **and** a useful velocity hypothesis
falsification:

1. **Main KCol result classification is sourced from an indexed
   16-byte primitive record's 16-bit offset +0x0E.**
   At `GolfKCol+0x002C` the caller's r7 is retained
   as r28. `GolfKCol+0x0104..+0x011C` selects the
   current indexed primitive, loads `lhz +0x0E`,
   and stores the halfword into `0(r28)`.
   At the exact `Ball+0x14D0` call site r7
   is `stack+0x08` (`Ball+0x14C4`),
   and `Ball+0x14F0` reads **that exact stack+0x08**.
   This is a concrete original native
   `prism record+0x0E -> query output -> Ball class u16` route;
   the physical meaning of the field and active KCL resource
   are **not** yet independently established.
2. **Triangle narrowphase likewise exports primitive +0x0E.**
   At `GolfKCol+0x22EC` it loads `lhz
   +0x0E(r27)`; at `+0x22F4` stores it to a
   local stack halfword; `+0x2684/+0x2688`
   reload and copy that value through the r22
   output pointer (r9 entry in `GolfKCol+0x2114`).
   This establishes another concrete producer/output link.
   However, the `Ball+0x0B60` call enters the
   **`GolfKCol+0x1AC4` wrapper**, not +0x2090 directly.
   We still must trace wrapper register forwarding to
   show that **Ball stack+0x0A** obtains exactly this
   field from the active resource in that path.
3. **Class 13 remains a special Ball event, not a tree.**
   The previous `Ball+0x0B84..+0x0C14`
   dispatch passes explicit 13 to the
   `Ball+0x01B8` handler. Its deeper path
   may call a routine attributed to public compiler
   unit `Tree+0x0604` at `Ball+0x025C/+0x02C0`,
   but **source-unit ownership is not a tree-instance
   receiver or tree hitbox proof**. This is
   another generic-helper confounder requiring
   register/callee owner tracing.
   Original candidate course KCL's 2498 prisms
   contain no literal 13; source-relative code
   alone does not establish whether 13 originates
   in another KCL resource, special result, or
   separate runtime environment.
4. **The three-component Ball +0xAC/B0/B4 reader is a
   *structural copy*, not an observed velocity use.**
   At `Ball+0x3568/+0x356C/+0x3570`,
   the fields are loaded from **r30**, followed by
   `Ball+0x358C/+0x3590/+0x3594` stores to
   **r29**. Nearby code copies +0xA8,
   +0xB8/+0xBC/+0xC0/+0xC4/+0xC8,
   counters and other state; previous
   `+0x34F0..+0x3518` similarly updates
   contiguous state members. This is source-proven
   whole-object/state copying, **not a simulation
   integration read nor velocity evidence**.
   The actual meaning of the Ball+0x14D0
   collision-conditioned stored vector is UNKNOWN.
5. The Ball hit-loop code `+0x0C98..+0x0F3C`
   performs floating-point and vector math,
   clamps and repeated query operations.
   PS paired-single operations are partly undecoded
   in the lightweight tracer. **No exact ball
   impulse, rebound coefficient, tree contact,
   foliage/trunk geometry or velocity update
   is established by this alone.**

**New follow-up** `scripts/p0_ball_kcol_prism_type_origin_private.py`
and `tests/test_p0_ball_kcol_prism_type_origin_private.py`
reuse the existing full source/scene/SHA/PPC gates,
require precise D-form field register/offset
producer and state-copy assignments, and print
only **322 bounded source words** in six as-yet
unexamined contexts: Ball query resource owner,
KCol wrapper/narrowphase forwarding, a secondary
KCol callback, and Ball bulk copy entry/tail.
The CLI strictly refuses to infer class 13=tree,
an active resource identity or velocity. Original
memory contents and code words remain local,
`training_approved=false`; no inspector or tree
visualization files are modified.

**Next falsifiers:** trace `Ball+0x0B60`
r27 KCol pointer to actual KCL backing resource;
trace `GolfKCol+0x1AC4` output register
mapping to the narrowphase r9 recipient;
test class-13 presence against any independently
verified active collision resources. Do not infer
a tree hitbox from label/class alone.


## Original phase7 wrapper classification and r13 global owner provenance

**Operator result**: `p0_ball_kcol_prism_type_origin_private.py
--capture 7 --detail` was run on original RSPE01 Rev1
seven-pair capture7 at exact source/worktree commit
`fcc48ebfd073295d9321d6157768655d3d12c54b`.
All original capture SHA/scene gates, source-proven
94×0x54 tree loop and earlier five Ball→KCol plus
seven inverse call anchors pass. Source-only private
PPC words were inspected locally and were not
committed as a native dump.

**Classification producer/return provenance:**
- `Ball+0x0A80: lwz r27,-23160(r13)` establishes
  the **global-source load** of the Ball collision
  query object candidate. The true runtime
  **r13 SDA base** and source global's actual
  captured pointer are not yet independently
  read in this pass. Do **not** equate the
  global to any guessed field/mesh pointer.
- `Ball+0x0B4C` moves r27 into r3. For the
  `Ball+0x0B60` call, `Ball+0x0B58`
  passes r6 = **stack+0x0A** and r7 = 1.
  This call is a **direct** `bl` to
  `GolfKCol+0x1AC4`.
- The wrapper forwards `mr r9,r6` at
  `GolfKCol+0x1ACC`, sets other
  call arguments at +0x1AD4..+0x1AE0
  (notably r5=0 and r6=-1), and **tail-branches**
  `GolfKCol+0x1AE4 -> GolfKCol+0x2090`.
- Narrowphase `GolfKCol+0x2114`
  retains r9 in r22; KCol loads halfword
  at **prism+0x0E** into r3 at +0x22EC,
  stores that halfword to local stack+0x08
  at +0x22F4, then on the qualifying
  successful result path reloads at +0x2684
  and stores it at `0(r22)` at +0x2688.
  `Ball+0x0B6C` then reads
  **exactly stack+0x0A**.
  This completes the previously open
  **KCL primitive +0x0E → wrapper r9 →
  narrowphase output r22 → Ball stack+0x0A
  material/status halfword** path.
  The native result path is conditional on
  success and output flags: this evidence
  does not prove every call returns a prism,
  nor which specific primitive underlies any
  particular gameplay event.
- `Ball+0x0B84` compares that returned halfword
  to **13**, which selects a separate
  handler `Ball+0x01B8` via
  `Ball+0x0BF4..+0x0C14`.
  Thus, if native class 13 is returned
  through that success path, it is sourced
  from the 16-bit KCol prism field, **not
  necessarily a tree hitbox**.
  The recovered 2,498-prism *candidate
  terrain KCL* contains no 13. Whether
  some other KCL resource, a copied/alternate
  primitive set or other source is active
  remains **unresolved**.
- `Ball+0x3568..+0x3594` is a further
  bulk copy of the +0xAC/+0xB0/+0xB4
  float triplet from object pointer r30
  to r29. Adjacent state fields, counters
  and flags are copied as well. No native
  integration/velocity consumer was
  established. The Ball+0x14D0 KCL success
  path still writes those floats; their
  **semantic field name stays UNKNOWN**.

### Next falsifiable source+memory comparison

A new isolated, **read-only** script
`scripts/p0_ball_kcol_active_resource_private.py`
and `tests/test_p0_ball_kcol_active_resource_private.py`
follow the qualified `Ball+0x0A80` SDA
source-global pointer only when the original
Rev1 startup symbol `__init_registers`
at `0x80006290` contains a uniquely
decodable **r13 lis + ori/addi initializer**.
No guessed hardcoded r13 base is permitted.
On a qualified original capture, the script
dereferences that global into a candidate
KCol instance and checks pointers at
+0x04, +0x08, +0x0C against the known
**unique** 2498-prism terrain KCL's vertex,
normal and 16-byte prism arrays. Both exact
pointer equality and complete byte equality
are reported as booleans only. No source
addresses, contents, capture values, type
13 guessed scans, private asset/geometry or
training labels are emitted. Failure to
recover original r13 or a valid object
**abstains rather than fabricating a mesh**.
Even all-three-array byte equality would
prove *this captured resource identity*,
not tree collision geometry or velocity.

Research isolation remains intact: only
#422 source-only scripts/tests/study/workflow
are changed; #431/#432 tree visualization
is independently owned. No trainable tree
collision label or geometry is approved.


## Original phase7: active KCL vertex+normal identity, prism offset discrepancy

The operator ran `p0_ball_kcol_active_resource_private.py
--capture 7 --detail` from exact commit
`dd78c5a383eacf148af8d567abba552e4bdb7d64`
against the original private archive; the original
seven-bank-pair SHA/scene/94x84 tree/PPC, five
Ball→KCol and seven inverse calls all passed.
Public Rev1 `__init_registers` symbol native
startup instructions at offsets +0x84/+0x88
uniquely establish the `r13` SDA base;
`Ball+0x0A80` loads r27 from the validated
`-23160(r13)` global. This leads to a
captured MEM2 KCol candidate instance whose
+0x04/+0x08/+0x0C fields all point into
captured MEM2.

The result was:
- **Active vertex buffer = original recovered 2498-prism
  terrain KCL vertex buffer**: exact source
  address AND complete byte equality TRUE.
- **Active normal buffer = terrain KCL normals**:
  exact address AND complete byte equality TRUE.
- **Active +0x0C prism pointer** did **not** match
  the prior comparison target, and neither did
  its full 2498×16-byte byte comparison.
- The original known terrain candidate has no
  literal classification 13. Neither another
  collision source nor a tree-specific hitbox is
  established by this one negative comparison.
  `training_approved=false`.

**Possible 16-byte comparator alignment mistake:**
The terrain KCL parser explicitly uses
`prism_offset + 16` as its first valid
primitive, skipping a 16-byte leading slot.
The earlier active comparator assumed
`KCol obj+0x0C` points at that **first usable
primitive**. However, native KCol indexes
prisms as `obj+0x0C + (u16 index * 16)`.
Its object pointer could legitimately point
to the **start of the prism table including
the leading dummy**, not the first usable
primitive. Thus the previous FALSE/FALSE
prism comparison **cannot on its own
establish a second prism dataset**. We must
test that exact off-by-one-record alternative
before following any suspected tree resource.

New bounded, read-only
`scripts/p0_ball_kcol_prism_dummy_layout_private.py`
and synthetic-only test file
`tests/test_p0_ball_kcol_prism_dummy_layout_private.py`
reuse the full original qualified source/SDA
gates, exact KCol vertex/normal pointers and
unique original terrain-header histogram.
The probe checks both exact conventions:
`header+pr` as dummy-inclusive base,
and `header+pr+16` as first usable prism,
then compares the **full** 2498-prism
payload at the corresponding active pointer
offset without printing RAM addresses, bytes,
per-prism classifications or game assets.
The only conditional class-13 outcome is
`0` when all active 2498 prism bytes
are independently verified identical to
the original known terrain candidate;
otherwise it is **null/unknown**.
No pointer searches or guesses over private
memory. No training labels, ball velocity
or collision geometry promoted.

**Next operator experiment:** run the new
dummy-16 alignment probe on original capture7.
If the alignment matches, the active Ball
KCol object **uses the existing known
2498-prism terrain primitive data in this
snapshot**, leaving class 13 a native
special branch without evidence of
a reachable class-13 primitive in that resource.
If it does not match, investigate source-qualified
active prism-table identity and length
rather than claiming a new tree mesh.


## Original capture7: dummy-prism alignment correction confirmed

The operator ran the source/SHA/scene/94-tree-gated
`p0_ball_kcol_prism_dummy_layout_private.py --capture 7`
at validated commit
`8e2982e94677ee6f9b05d7eb6e4f04b0febe423a`.
Result: `ACTIVE_KCL_PRISM_LAYOUT_COMPARED`,
`active_prism_pointer_equals_terrain_dummy_base=true`,
`active_prism_data_equal_after_dummy_16_byte_skip=true`,
`active_2498_prism_bytes_match_known_terrain=true`,
and `original_active_vertices_exact_pointer_equal=true`,
`original_active_normals_exact_pointer_equal=true`.
The active KCol instance's prism pointer is
**at the beginning of the 16-byte dummy-inclusive
KCL prism table**, not the first usable prism.
All 2498 usable records are **byte-identical**
to the previously independently recovered
and SHA-qualified 2498-prism *terrain* resource.
There are **zero class-13 attributes among
these verified usable records**. This fully
explains the previous active prism negative
pointer/byte comparison: its offset was wrong.
The mismatch is **NOT** evidence of another
collider or alternative resource.

The concrete successful native code path remains:
`Ball+0x0A80` r13 source global -> KCol
object -> `Ball+0x0B60` wrapper ->
narrowphase prism record +0x0E -> stack
classification output -> `Ball+0x0B6C`
classification consumer. `13` exists as a
special native Ball branch, but **is not a
value present in this snapshot's verified
active 2498 usable terrain prisms**.
This does **not** rule out different courses,
other active or auxiliary resources, non-KCL
obstacles/tree mechanisms, or future
contact states. No native tree radius,
canopy behavior, speed/velocity semantics
or force response is proven. Keep
`training_approved=false`.

### Expanded original seven-phase memory inspection

User offered deeper memory inspection. The
first step uses already archived source data,
not new Dolphin capture. Added **read-only**
`scripts/p0_ball_kcol_seven_capture_active_kcl_private.py`
and **synthetic-only** unit tests
`tests/test_p0_ball_kcol_seven_capture_active_kcl_private.py`.
For EACH of seven original numbered, SHA
verified paired snapshots, it independently:
- checks scene, 94×0x54 source tree array,
  exact native field-loop and 5+7
  Ball/KCol primitive-return PPC gates;
- source-derives `r13` from original
  `__init_registers`, reads only native
  `r13-23160` KCol global, and checks
  the active KCol object/buffer banks;
- requires exact vertex/normal alias
  and correctly aligned 16-byte dummy
  inclusive active prism alias against
  that phase's independently located
  unique terrain KCL candidate, with
  **complete 2498×16-byte comparison**;
- counts original active usable prism
  16-bit classification halfwords from
  record offset +0x0E, and checks the
  original expected source histogram;
- emits phase number, type histogram,
  zero/positive class-13 count, object
  and prism-address temporal equality
  booleans only. NO RAM pointers, source
  bytes, coordinates or native code are
  exported. If any phase lacks the exact
  source gates or candidate, the command
  **abstains** rather than representing
  incomplete coverage as a 7-phase proof.

This establishes whether the capture7
result persists across the **original
seven observed phases**. Even a positive
seven-phase result does not prove
all game courses, tree collision geometry,
or that an unobserved class 13 is a tree.
The separate inspector PR #431/#432
remains untouched.


## Original all-seven active terrain KCL audit passed

The operator executed `p0_ball_kcol_seven_capture_active_kcl_private.py`
at the pinned `42c0d4f5d7f02eba9118e968c9c2ad38c6bb2155`
head against the original seven-pair archived private
RSPE01 Rev1 captures; all seven independently passed
original RAM SHA, selected scene, source 94×0x54 trees
and native PPC 5+7 Ball/GolfKCol, primitive+0x0E and
SDA global identity gates. For **each capture 1 through 7**:
- exactly **2498 usable active KCL prisms** with the native
  dummy-inclusive +0x0C index-base convention;
- **active vertices, normals, and full usable prism bytes
  exactly equal the same unique recovered terrain resource**;
- all seven native active KCL primitive class histograms
  equal the original histogram:
  `1:208,2:585,3:301,4:508,5:44,6:478,7:7,9:99,12:268`;
- **class 13 count = 0** in every verified active usable
  prism array;
- same KCol collision object pointer and same native
  prism table pointer as phase 1 (temporal equality, NOT
  evidence of velocity/physics stability).

`all_seven_active_kcl_same_2498_terrain_resource=true`;
`all_seven_active_prism_class13_counts_zero=true`;
`all_seven_native_classification_histograms_match_known_terrain=true`;
`same_collision_object_address_in_all_captures=true`.
All other potentially-active resources globally, tree
colliders, other courses, indirect object callbacks and
non-KCL geometric mechanisms remain UNEXCLUDED.
The native Ball class-13 event branch exists, but
this capture cohort contains no original active
terrain prism capable of supplying it directly.

**Do not search for a second KCL on the basis of
the old 16-byte prism comparison mistake.** The
original first-word 94-tree record candidate
method-table and Ball/FieldManager indirect
call targets are the next falsifiable source
path; native object table membership alone does
not establish collision semantics.

No original native bytes, heap addresses,
tree XYZ, per-object values or assets
were added to the repository. No
training or physical tree geometry approved.


### Source-qualified indirect Ball–Tree candidate audit

With all seven *active terrain* KCL buffers validated
and no native class-13 terrain prism, the next
discriminator is **non-KCL object dispatch** rather
than scanning for another prism mesh without an owner.

`scripts/p0_tree_ball_indirect_dispatch_private.py`
and synthetic-only
`tests/test_p0_tree_ball_indirect_dispatch_private.py`
use the original SHA/scene/94×84 source tree array,
full 5+7 native Ball/KCol and +0x0E primitive
producer gates. The audit follows the shared
first word across **all 94 original tree objects**
as a candidate MEM1 method table, reporting
only public-source-unit-relative candidate
targets for its first 64 entries. Separately,
it enumerates native PPC indirect bctrl/bclrl
sites in **Ball, FieldManager, Simulation, Tree,
CollisionChecker and CollisionModel**,
distinguishes branch-to-CTR vs branch-to-LR,
and marks only the **syntactic** proximity of
`mtctr` before indirect calls. With `--detail`,
at most 30 callsite contexts of 12 original
instructions are locally printed to the
operator; the default compact JSON contains
no ROM words. No native executable bytes,
memory pointers, tree XYZ or models are
committed or posted.

**Strict evidentiary separation:** a shared
object first-word pointing into MEM1 may be
a vtable or another object header structure;
an apparent code pointer in a table slot
does not prove it is a *tree* method; an
indirect bctrl site in the Ball unit does
not establish that it invokes a candidate
table slot without proving its CTR reaching
definition and the call's receiver.
A positive result is only a map of likely
next original PPC code windows for static
receiver provenance. A negative result does
not exclude inlined tree collision or
nonvirtual callbacks.

**Next evaluation:** if any original Ball
indirect call source context demonstrably
loads a field/tree object table, follow its
actual indirect target, native geometry
inputs, and before/after ball state. If none
does, shift to controlled *actual tree contact*
Dolphin capture pairs rather than invent
a collision shape. Maintain
`training_approved=false`, and keep
separate visualization PRs unchanged.


## Operator capture7: 94-object firstword table and indirect Ball dispatch

Operator executed the original source-gated
`p0_tree_ball_indirect_dispatch_private.py --capture 7 --detail`
on the private RSPE01 Rev1 archive, pinned to
`9a5fe16c1e54b4b1aba21bb71b252050366c156f`.
It passed the original scene/SHA, 94×0x54 source tree
loop, native KCol 5+7 source calls, and original
primitive+0x0E producer gates.

**Positive source-only facts**:
- All **94** contiguous tree records' first word
  contains the **same bounded MEM1 table pointer**.
  Among its first **64** slots, **20** code-like
  entries point into the public Ball unit and
  **2** into FieldManager; the remaining **42**
  are outside the **selected subset** of source
  unit intervals (NOT proven non-code).
  Many slots target the same `Ball+0x1394`
  address, with a few others
  `Ball+0x1134/+0x11F0/+0x12AC/+0x1108`
  and `FieldManager+0x1394/+0x1298`.
  This may be an object virtual table or another
  shared structure; its dynamic type and methods
  are not yet established.
- Original executable source has **34**
  Ball, **50** FieldManager and **1**
  Simulation indirect `bcctr LK` calls;
  zero in the scanned Tree, CollisionChecker,
  or CollisionModel units. These are static
  candidate callsites; no Ball→Tree
  receiver or contact path is proven.
- **Concrete candidate reaching definitions**:
  `Ball+0x03BC/+0x03C4/+0x03C8` load
  child pointer `BallCandidate+0x144` (via
  r31), a table at child `+0x78`,
  and method at table `+0x48`,
  followed by `mtspr CTR` and
  `bcctr LK` at +0x03CC/+0x03D0.
  `Ball+0x0484..+0x04C0` has
  source-local repeated child pointers
  `+0x140/+0x13C`, whose **first word**
  is read as a table and dispatch slots
  `+0x7C/+0x88` called through CTR.
  The memory identities of these **Ball child
  tables vs tree shared firstword** have
  not yet been compared; source code
  shows only a possible dispatch mechanism,
  not a physics handler.
- Some Ball indirect calls access a stack
  object's own table (e.g. `Ball+0x1180`);
  these must not be conflated with an actual
  94-tree object. The 17 locally printed
  call contexts preserve this distinction.

**New focused falsifier**:
`scripts/p0_tree_ball_runtime_table_alias_private.py`
with synthetic tests
`tests/test_p0_tree_ball_runtime_table_alias_private.py`
reuses the fully verified original native
tree and Ball/KCol source gates and requires
precise native D-form/CTR/BCTRL instructions
at the callsites above. It follows ONLY the
previously source-correlated, four-slot
PlayerManager **candidate** Ball objects
(undetermined dynamic activity); examines
each candidate's +0x13C/+0x140 children
at table +0 and +0x144 child table at
+0x78. It reports source-relative
field names, table-bounded booleans,
and equality against the 94 tree
objects' common firstword pointer.
No pointer values, native instruction bytes,
positions, model or KCL data are output.
An equality would be an alias lead, NOT
a tree collider; a non-equality cannot
exclude other virtual dispatch paths,
different ball objects, or inlined physics.

Native tree collision/leaf damping/trunk
dimensions and ball response unverified.
No visualization modifications and
`training_approved=false`.


## Capture7 Ball child dispatch alias falsifier: 0/12

Operator ran `p0_tree_ball_runtime_table_alias_private.py
--capture 7` from pinned SHA
`72ec42f3c10d5104a6062509d260665ef50d50b4`;
all original 7-pair archive SHA/scene, 94 tree source loop,
five Ball→KCol and seven inverse native source gates,
and exact Ball indirect-call register instructions
passed. The four source-correlated but still
**not gameplay-identity-verified** Ball candidates
each had three bounded child table pointers, so
this is a complete **12/12** identity comparison
for the selected child paths, not an incomplete
pointer test.

**Observed result:** none of the four Ball
candidates' `+0x13C` child-firstword
tables, `+0x140` child-firstword tables,
or `+0x144` child's `+0x78`
dispatch-table fields equals the shared
firstword address of the original 94 trees.
Exact alias counts for the three child
members: `0,0,0`. This **disfavors** the
limited hypothesis that the previously
inspected `Ball+0x03D0/+0x0498/+0x04AC/
+0x04C0` indirect sites dispatch through
the **same memory table as the 94 trees**.
It does NOT prove these are the active Ball
instance receivers at contact, nor exclude
other callbacks, colliders, or alternative
native dispatch paths. Physical tree
geometry, ball collision response, impulse
and training semantics remain unverified.

### Final bounded static check before contact experiment

The initial 64-slot shared tree-firstword
inventory only mapped **8 manually selected
source units**. It left 42 table entries
"outside selected source units"; these
have NOT been proven outside game code.
Rather than repeating broad indirect-call
enumerations, added
`scripts/p0_tree_full_public_table_targets_private.py`
and synthetic-only
`tests/test_p0_tree_full_public_table_targets_private.py`.
This focused read-only audit qualifies
original archive, scene, 94×0x54 trees,
verified KCol primitive producer, and
the **complete retained public
`RSPE01_01_public_text_units.json`**
against its original public source blob
SHA. It classifies exactly 64 values from
the existing 94-tree shared-firstword
table by **all** public Rev1 compilation
units, returning a source-relative
target label or a distinctly marked
`not_in_retained_public_text` value;
neither means a callable tree method
until actual receiver and method dataflow
are established.

This is a **terminal static triage**:
if no credible shape/physics source
method appears, prioritize designed
tree-strike vs matched near-miss
Dolphin observations, with operator
visual verification, controlled initial
ball/aim/club/wind state, and source-gated
before/after MEM1/MEM2 capture snapshots.
No automatic swing, Dolphin actions
or live memory writes are part of this
read-only script. Separate #431/#432
visualization work remains untouched.
`training_approved=false`.


## Source-complete tree-table triage and controlled tree-contact trial

**Operator correction:** there is **no previously captured or visually
verified ball/tree contact observation** in this project. No existing
captured flight may be labeled `tree_hit` or used to fit a physical
tree collider. A new operator-controlled observation must first be
produced, or this research stays at source-only UNKNOWN.

The operator executed `p0_tree_full_public_table_targets_private.py
--capture 7` pinned to exact commit
`1fdc8de8b1158a86ee38de62d902b77637e78854`.
All original source SHA/scene/94x84 field tree loop and native
Ball/KCol 5+7/primitive-producer gates passed, as did the retained
public Rev1 complete `.text` source-map provenance.
Of the 64 four-byte entries read starting at the shared
firstword pointer common to all 94 tree records:
- **20** fall into `RPGolMapObjBall.cpp`;
- **2** fall into `RPGolFieldManager.cpp`;
- **28** fall into the public **Tennis**
  `RPTnsScene_unsplit.o` code unit;
- **14** are outside the retained public `.text` map.

The last 42 were only "outside *selected* units" in
the previous audit; the complete map now resolves
28 of those 42 to Tennis code and leaves 14
outside the retained text map. The source pointer
is shared by 94 tree objects, but the arbitrarily
read 64 slots were only a **bounded inspection
window, never a proven vtable length**.
A long run of nearby Tennis-code targets is
consistent with scanning beyond one short
method-table region into adjacent tables,
but without data-boundary/source ownership
proof even that interpretation is a
**hypothesis**. There are **no verified
Tree-specific virtual methods, tree-collider
callbacks, ball impact responses or velocity
instructions** from this table audit.
Do not use the 64-entry results as a 64-method
tree vtable, and do not conflate public
compilation-unit source ownership with object
receiver semantics. The previous Ball child
table alias comparison was **0/12**, and the
active 2498 usable terrain KCL class-13 count
was **zero in each of seven captures**.

### Next controlled operator test — no existing tree-hit label

Use an unmodified Wii Sports Rev1 game,
no native memory modification or inferred
tree collision coordinates.

1. **Prepare a reproducible starting checkpoint.**
   Choose a tee/ball-at-rest position with a
   visibly reachable tree. Record game/course/
   hole, club, wind as displayed, current aim,
   camera view and operator-observed state.
   Preserve the same exact pre-shot Dolphin
   savestate or independently verified reset.
   Reusing a savestate preserves more hidden
   state than manually resetting a shot.
2. **Attempt deliberate contact, operator visible.**
   Aim at a clearly visible trunk or foliage,
   strike once, and inspect the actual trajectory.
   The attempted aim itself is **not** evidence
   of contact. Record the sequence as
   `confirmed_contact`, `confirmed_clear_miss`,
   or `unknown` only after viewing the
   pre-/at-/post-approach behavior.
   Keep `trunk`, `foliage`, `unclear`
   as *operator visual categories*, not
   native collision shape labels.
3. **Matched near-miss negative control.**
   Load the same pre-shot checkpoint,
   same club/power/pose/intended input profile,
   camera and wind; change ONLY
   the aim/yaw needed to pass visibly beside
   the same tree. Record this as a separate
   attempt, with no automatic equivalence
   inferred if launch power is different.
4. **Capture pre/approach/post observations.**
   If safely available through the existing
   private recording workflow, collect
   visual screenshots or video time markers
   and paired MEM1/MEM2 read-only snapshots
   near ball–tree approach, potential contact,
   and immediately after. Mark each snapshot
   `same_physics_frame_verified=false`
   unless atomic capture is actually
   established. Never use a screen transition,
   angle change, or moving camera as
   proof of collision. Keep all raw files
   under the ignored `Wii-AI-Golf-Data`
   tree and never Git commit them.
5. **Evaluate before physics fitting.**
   Require both visible behavior and the
   original source-selected Ball object
   tracking to support a contact candidate.
   Use matched near-miss to eliminate
   normal flight and terrain bounce as
   alternative explanations. Actual collision
   event and exact collision geometry still
   need original native receiver/source
   verification. Do not fit tree radii,
   leaf drag, restitution, velocities or
   obstacle policy from one anecdotal shot.

The first actionable input is an operator
screenshot/video of a prospective tree-lined
shot or **one** visually confirmed contact
attempt. No preexisting tree-contact
dataset is assumed. A source-only result
may remain `UNKNOWN` indefinitely without
physical observations. PR remains research-only
and `training_approved=false`.


## Enter-to-record live wood, leaves and near-miss protocol

Per operator request, prepared
`scripts/p0_tree_contact_record_private.py` and a Windows
PowerShell wrapper `scripts/run_p0_tree_contact_record.ps1`.
These are **new live, read-only** operator-controlled
trial collectors and must NOT be conflated with
the archived seven-pair original SHA-verified capture.
They do not load a savestate, press A, swing, alter
game memory, set aim, score a shot or identify a
collision themselves. Use only an already running
Wii Sports USA Rev1 Golf scene with the existing
localhost Felk bridge on port 55355, plus the
source-owned selected Ball candidate / record / 94
trees. The tool performs exact scene/owner, game
revision, source player manager, selected record,
nested ball pointer and 94 identical tree-firstword
checks before every recording.

The wrapper runs three separate human-operated
trials in this order:
- `wood`: human aims at visible **trunk/wood**
  and swings manually;
- `leaves`: human aims at **foliage/canopy**
  at appropriate observed height;
- `near_miss`: human aims **adjacent to the
  same tree** as a negative control.

For each trial, the operator prepares Dolphin,
presses ENTER to authorize START, gets a 3-second
focus countdown, swings manually, and can
return to the terminal to press ENTER to STOP.
Each trial also auto-stops at 50 seconds by
default (5..180 seconds supported). The tool
captures approximately 4 non-atomic bridge
read packets per second:
source-correlated selected Ball `+0..+0x1BF`,
selected player record `+0..+0xCB`,
nested Ball translation candidate `+0..+0x0B`;
every 8th packet also captures the complete
94×84 tree-record array (including candidate
proximity byte `+0x48`). Every packet carries
host UTC, monotonic timestamps, and a bridge
frame-count start/end bracket. These bridge
ticks are **NOT established guest physics frames**
and the multi-RPC snapshots are **NOT atomic**;
a transient frame-exact impact can be missed.
Pointer, hole and tree array root controls
are checked periodically, and the stream
abstains on root changes.

When FFmpeg is available on the Windows PATH
and exactly one visible Dolphin window is
identified, a **Dolphin-window-only** MP4
is attempted automatically. Otherwise
Pillow, if installed, may save sampled
screenshots **only while Dolphin is the
foreground window**. If neither is
available, the recorder saves memory only,
and the operator must independently take
screen video (e.g. OBS). Never silently
record the entire desktop. Raw event JSONL,
screenshots and video all stay under a
unique ignored sibling `Wii-AI-Golf-Data/captures/
tree-contact-*-PRIVATE` directory; never
commit any native RAM / private visuals.

After each trial, the operator separately
reports the **visually observed** region
`wood/leaves/none/uncertain`, whether
the trajectory visibly changed and optional
conditions. The intended trial `wood`
or `leaves` does not certify a collision.
Human observations remain unverified by
native contact code; special cases include
foliage occlusion, ground contact and
ball traveling behind the tree. A safe
`operator-summary-SAFE.json` holds counts
and user annotations without native words.
No tree shape, canopy drag, impulse or
ball velocity field may be trained solely
from these samples; native source contact
event and independent timestamp/visual
corroboration remain prerequisites.

**Next step:** collect paired wood and
foliage attempts plus near-miss using a
single restored pre-shot state as closely
as possible. Analyze source-selected Ball
candidate and tree-proximity changes against
screen imagery, then trace any uniquely
discriminating game code. Mark
`training_approved=false` throughout.


## First live operator tree approaches — all three recordings saved, final summary crash

Operator executed the pinned original research recorder at
`ccfa53c45048bb2baa1298ffe3fd98ebb5ae0947`
on a running **RSPE01 USA Rev1 Golf, raw mode 4,
hole raw index 1**, with the source-selected Ball
and the 94 source-owned 84-byte tree records
qualifying before each trial. It produced unique
private trial folders below the session
`tree-contact-20261111T042646Z-64fb3def-PRIVATE`.

**The operator observed**, in capture order:
- Trial intent `wood`: **45** Ball candidate packets,
  **6** 94-tree-record snapshots; human reported
  **foliage/leaves contacted** and visible
  trajectory change. Actual observation differs
  from intended target. No club/power/wind note.
- Trial intent `leaves`: **39** packets,
  **5** 94-tree snapshots; human reported
  **wood/trunk contacted** and visible trajectory
  change. Club note: `driver`. Again, the
  observed target differs from intended target.
- Trial intent `near_miss`: **26** packets,
  **4** 94-tree snapshots; human reported
  **no tree contact**, **no trajectory change**.
  Club note: `driver`.

**Total 110 source-candidate packets, 15 periodic
94-tree snapshots.** The logger printed each
`trial-summary-PRIVATE.json` path and saved
the raw sample stream before failing with
`KeyError: 'kind'` while generating the
**combined** `operator-summary-SAFE.json`.
The per-trial payload includes `trial_intent`,
not `kind`. This is a summary-construction
bug; it is **not** evidence the recorded native
data were absent. The transcript does not
independently prove their integrity: recover
only after checking each saved raw file's
original SHA, size and packet count. No
repeat gameplay shots are warranted solely
because the aggregate summary failed.

**Repair**: the original recorder now calls
`summarize_trials`, which accepts the
original `trial_intent` field (and `kind`
for deliberately skipped trials), preserves
human-reported leaf/wood swap, and computes
counts while never labeling native contact.
A dedicated **offline-only**
`scripts/recover_p0_tree_contact_record_private.py`
recovers the safe summary from the original
`trial-summary-PRIVATE.json` files, verifying
raw candidate SHA-256s, sequential sample
indices, recorded source-identity digests,
counts and non-atomic bridge-frame brackets.
It does **not** connect to Dolphin or perform
any memory reads, controller inputs,
savestate resets, code/asset exports or
training label assignments. It creates
`operator-summary-SAFE.json` exclusively
(no overwrite) in the existing private
session; the original trials remain untouched.
A new synthetic-only test module
`tests/test_recover_p0_tree_contact_record_private.py`
includes a regression for the exact
`45/39/26`, `6/5/4`, and
wood-intent/leaves-observed vs
leaves-intent/wood-observed labels, plus
tampered hashes, altered counts, wrong
scene identity and refusal of rewrites.

**Evidence remains human-reported only.**
The operator has supplied neither the
actual raw data files nor an independently
reviewed impact video in this chat. The
non-atomic memory sampling may skip
momentary collision effects. No game
contact instruction, physical tree
geometry, ball velocity or leaf drag has
been established or approved for training.
The next step is to recover and inspect
the sanitized per-trial summary, then
perform a bounded, source-qualified
offline difference of the original
candidate windows against the negative
control, with optional visual review
if a video was actually recorded.
`training_approved=false`.


## Deep offline original live trial RAM differential — no new swings required

Operator successfully recovered the **original** source-selected Ball/trees
session `tree-contact-20261111T042646Z-64fb3def-PRIVATE`
with original recorded raw SHA/packet validation:
**45/39/26** Ball candidate packets for target intents
`wood/leaves/near_miss`, **6/5/4** snapshots of the
94×84-byte tree array, **110** and **15** total respectively.
The source-selected Ball identity and raw hole index match
across all trials. Operator-observed contacts are **LEAVES
in wood-intent trial**, **WOOD in leaves-intent trial**, and
**NO CONTACT in near-miss**; user reported changed flight
in first two, unchanged flight in the control.
Same savestate, launch power or pose has **not** been proven
across trials. All three optional FFmpeg videos are
reported created, but their frame content has not been
inspected independently; reported video_created does not
prove the recording shows actual trajectory.

Created **read-only, offline-only** bounded study:
`scripts/analyze_p0_tree_contact_memory_private.py`,
synthetic tests `tests/test_analyze_p0_tree_contact_memory_private.py`.
It calls `recover_p0_tree_contact_record_private.recover`
to independently SHA-verify original source-selected
recordings, their 110 packet schemas/counts,
source-identity digests, and 94-tree metadata.
It neither calls Felk RPC nor launches Dolphin, nor
writes any RAM/savestate, nor modifies the original
raw logs or their manifests. It writes a new
`tree-contact-deep-memory-SAFE.json` **exclusively**
in the already-private source session folder. Repeated
execution refuses to overwrite a prior result.

Methods:
- **Non-atomic temporal coverage**: within each trial
  validates monotonic host nanosecond timestamps
  and Dolphin RPC frame-count brackets (NOT guest
  physics frames). Summarizes sample cadence,
  median/max read duration, and total observed
  capture interval; explicitly denies impact-frame
  synchronization or comparable swing timing.
- **Object-by-object big-endian word transitions**:
  for source-selected `Ball+0x000..0x1BF`,
  selected player record `+0x000..0x0CB`,
  and Ball nested translation candidate 12-byte
  window, enumerates exact successive word-bit
  changes, first/last differences and source
  object-relative offsets. No memory addresses or
  native word values are exported.
- **Source-bound field windows (candidate ONLY)**:
  `Ball+0x30` (12 bytes), `Ball+0xAC` structural
  copy triad **NOT velocity**, cache candidates
  `Ball+0xCC,+0xF0,+0xFC`; selected record aim
  `+0x3C`, start/initial candidate triplets
  `+0x54,+0x60`, selected Ball pointer `+0x88`;
  nested Ball 12-byte translation candidate.
  Emits distinct raw bit-pattern counts and
  transition sample indices, **NOT** guessed XYZ,
  velocity, frame-exact physics changes or
  decoded f32 coordinates.
- **Tree-by-tree temporal source audit**:
  for each periodic original 94×84 source-tree
  snapshot, compares all **21** native big-endian
  words per tree and tallies changing source
  tree-array indices and record-relative offsets.
  Records candidate `Tree+0x48` flag word
  changes separately; that flag has an original
  **source-proven proximity/visibility** code
  path but **no proven collision-handler meaning**
  (prior camera receiver ambiguity). Likewise
  tree position-like `+0x30..+0x38`
  are observed source geometry, not verified
  physical collision hulls.
- **Negative-control comparison, no false
  impact inference**: identifies words whose
  bit-patterns transition in **both** operator
  contact-intent trials but **never** in the
  near-miss trial, also those only one trial
  changes, and ordinary changes in all three.
  Tests equal-baseline exact memory words/tree
  arrays across trials but does not equate
  equal bytes to an identical savestate.
  Unequal trial lengths/launch parameters,
  animation and unrelated state changes
  remain confounders. Candidate enrichment is
  a search prioritization, NOT a collision
  classifier or statistical proof.
- **Optional FFmpeg metadata only**: uses local
  `ffprobe` when available to report aggregate
  video existence/duration/size, but does NOT
  watch frames or time-align frames to RAM
  without an authoritative shared clock.

The new report contains no native words/bytes,
MEM1/MEM2 heap addresses, source code, private
tree coordinates or local file paths. Findings
are source-candidate dynamics only; a true
wood-vs-leaf physics branch and response
remain unverified. The report is meant to be
shared privately here alongside short
human-reviewed Dolphin-window clips before
further original PPC dispatch tracing.
No tree hitbox, canopy drag or impulse policy
should be fit solely to this dataset;
`training_approved=false`.


## Operator deep-memory report reviewed — no unique Ball contact word

User provided original `tree-contact-deep-memory-SAFE.json`
from the SHA-validated original 110 source Ball packets,
15 snapshots across three trials. Its key findings are:

- **Every one of 60 dynamic Ball candidate words** changes in
  all three original trials. There are **zero** words changing
  only in both claimed contacts but static in the no-contact
  trial, and **zero** words changing in exactly one contact
  while static in the control. The nested 12-byte candidate has
  all **3** words dynamic in all three, and the selected player
  record has all **29** dynamic words in all three. This rules out
  an *obvious exclusive changing field* in these short recorded
  windows, not a code/path-specific collision effect.
- The candidate Ball `+0x30` triplet (and nested triplet)
  starts changing at consecutive source-packet indices
  **25..** for both reported contacts; the negative-control
  first contiguous run begins around source index **10**.
  The ~0.263s packet cadence and different manual swing start
  times make raw sample indices **not aligned impact times**.
  `Ball+0xAC` is an original structural-state copy, **not
  independently proven velocity**. The game is updating
  multiple triads during the observed flight.
- Source tree `+0x48` flag word has **zero recorded changes**
  across all 94 trees in all three trials. This does not
  disprove a tree impact: it might be a noncontact proximity
  / camera flag or change faster than the ~2-second all-tree
  snapshot cadence.
- Broad **tree+0x4C and tree+0x50** word updates hit essentially
  all 94 trees throughout **all** trials, including the near-miss:
  **470 each** in `wood` intent (operator saw leaves),
  **303 each** in `leaves` intent (operator saw wood),
  **188 each** in `near_miss`. This is widespread
  per-tree runtime/animation state, NOT an exclusive collider
  signature.
- Exactly **six** source tree-record word sites were dynamic
  in both human-reported contact trials and static in the
  near-miss: source tree **11, 38, 40**, each at member
  offsets `+0x24` and `+0x2C`. These are **candidate-only**:
  their native class/field meaning, relation to the visibly
  contacted tree, and impact-time correlation have NOT been
  verified. These could be actor-camera/model lifecycle changes
  synchronized with start times rather than collisions.
- At the first packet, original selected Ball and nested
  bytes are bit-identical across all three trials, but the
  selected player record and full 94-tree arrays are **not**.
  Exact preshot savestate equality and same launch power/
  swing pose/wind remain unverified. This is a control-quality
  limitation; first Ball equality alone is not a full reset.
- Source packet read spans median ~0.038s, max ~0.2s,
  and native bridge frame brackets can span up to 23 counts.
  These are **multi-RPC non-atomic samples**, not single
  verified impact-frame snapshots. Video durations were
  **9.5s, 10.42s, 6.83s** for wood-intent,
  leaves-intent, miss; clips exist but were not
  visually reviewed/time-aligned to RAM.

**Actionable next narrowed forensic audit**:
`scripts/p0_tree_contact_source_phase_triage_private.py`
and synthetic tests
`tests/test_p0_tree_contact_source_phase_triage_private.py`
use SHA-gated original source candidate records to:
- align all three trials by **longest contiguous candidate
  Ball+0x30 12-byte change run**, not operator launch clock;
- test **exact bit equality** between the source-selected
  nested translation triplet and every aligned 12-byte
  Ball-object window, especially `+0x30` and `+0xAC`;
- interpret only **bounded finite f32 candidate triplets**
  to rank abrupt *dimensionless turning angles* and
  adjacent displacement-length ratios; DO NOT call these
  native velocities, impulses, verified world XYZ or
  contact timestamps;
- find exact coarse tree snapshot *intervals* in which
  source indices 11/38/40 member `+0x24/+0x2C`
  change, and compare with the 94-object widespread
  `+0x4C/+0x50` change pattern;
- enumerate which **initial source tree/player word offsets**
  differ between original starts rather than simply
  reporting whole-record baseline mismatches.

The tool runs **offline** on the existing three original
private source snapshots, writes only a new safe report
under the private local session, does not connect to
Dolphin, and never modifies the original data. Original
native contact receiver, separate wood/leaves physical
response, tree-specific hitbox radii and Ball velocity
remain UNPROVEN; `training_approved=false`.


The source-phase triage also tests a *strictly tentative*
geometric hypothesis: decode finite source `Ball+0x30`
12-byte candidate triplets and each of the 94 original
tree `+0x30` centres, requiring each source tree triplet
to be **unchanged across the original trial snapshots**.
For the sustained movement run, it ranks source tree
array indices by assumed XZ and XYZ component-wise
squared distance, without outputting any original
XYZ or distance. It reports whether the six
`11/38/40 × (+0x24/+0x2C)` memory-change candidates
were among nearby source tree records under these
**unproven common-coordinate-space assumptions**.
A near rank by itself is a **spatial-coincidence
hypothesis**, not proof of a trunk/canopy hitbox
or native Ball→Tree collision. If any tree origin
changes, the spatial rank **abstains**.


## Original 110-packet source-phase SAFE report — tree updates align with launch

The operator uploaded and we inspected the original
`tree-contact-source-phase-triage-SAFE.json`, generated from
the private SHA-verified 110 Ball candidate packets / 15
94-tree snapshots. This result is **from this original
three-trial dataset**, not a new execution of Dolphin.
The recorded intent labels are **not** the actual human
observations: `wood` intent was observed *leaves*;
`leaves` intent was observed *wood*; `near_miss`
was observed *none*.

### Ball candidate direction changes after manual launch

- Human observed **leaves** (`wood` intent):
  original sustained `Ball+0x30` triplet change
  after samples **25..33**, 9 transitions;
  largest adjacent-sampled displacement turn
  **66.06 degrees at sample 27**, two
  transitions after run start, displacement
  size ratio **1.128**. Other notable candidate
  changes **34.30 degrees at 29**,
  **29.43 degrees at 26**. The reported
  652.473× length ratio at sample 33
  accompanies only a ~1-degree turn and
  must not be interpreted as a physical
  impulse/restitution.
- Human observed **wood** (`leaves` intent):
  sustained run **25..30**, 6 transitions;
  largest turn **59.79 degrees at sample 28**,
  three transitions after onset, length
  ratio **3.986**; next turns **12.74 at 29**
  and **12.03 at 27**.
- Human observed **none** (`near_miss`):
  sustained run **10..17**, 8 transitions;
  largest turn **14.74 degrees at sample 11**,
  one transition after onset, length ratio
  **1.112**. Next turn **8.97 at 12**.

These angles are solely based on candidate
BE-f32 triples and *coarsely timed* sequential
sampling; original world-space/rendered-ball
identity, contact time, native collision cause,
and physics-frame alignment all remain
unverified. They support prioritizing the
two observed contact shots for video review,
but **do not support fitting wood/canopy
coefficients**.

### Tree array fields: apparent contact-selective subset is likely confounded by launch phase

All-94-tree periodic snapshots were at
original packet indices 0,8,16,..., so
each native tree update is only bounded
to an **8-packet interval**. More
precisely than the first 6-word enrichment:

| Operator observation | Candidate Ball starts changing | Full-array tree `+0x24/+0x2C` co-updates | Source indices 11,38,40 `+0x24/+0x2C` |
| --- | --- | --- | --- |
| Leaves | 25 | 23 trees in [24,32], 21 in [32,40] | changed in both [24,32] and [32,40] |
| Wood | 25 | 14 trees in [24,32] | changed in [24,32] |
| Near miss | 10 | 11 trees in [8,16], 9 in [16,24] | did NOT change |

**Key interpretation:** the **first** broad
`+0x24/+0x2C` change interval occurs
at the initial Ball candidate movement in
**all three** trials, including the
near-miss. Thus **grouped tree record updates
are not specific to tree impact**; they
are plausibly actor movement, camera/model
visibility or object lifecycle. Tree indices
11,38,40 happened to change only in the
two contact trials, but their transitions
are part of larger simultaneously updating
tree groups rather than isolated impact
events. A prior original PPC source gate
in `p0_tree_flag_receiver_disambiguation_private.py`
shows the **Tree compilation unit**
function has an integer **`lwz +0x24(r3)`**
at public `Tree+0x04A0`, plus
`stfs +0x4C/+0x50` in related code.
**Receiver identity as the 94 native tree
records is still unproven**, so do not
promote this alone to field type
documentation. No original PPC source
proof for `+0x2C` as a collider/handle.

The near-miss showed widespread 94-tree
`+0x4C/+0x50` co-updates in [8,16] and
[16,24]. Contact trials showed the same
broad co-updates at multiple intervals,
including at Ball movement. The
tree `+0x48` flag remained unchanged
in all three. No verified native
tree impact latch.

### Tentative nearest-tree index — strongly disfavors tree 11/38/40 as localized impact evidence

Assuming (NOT proving) that source-selected
`Ball+0x30` candidate values and each
tree `+0x30` are in the same native
coordinate frame, original finite source
triplet ranks yielded:
- Leaves contact intent source `wood`:
  nearest source tree #3 for 5/9 moving
  packets, #21 for 2/9, #63 for 2/9.
- Wood contact intent source `leaves`:
  #63 nearest for all 6/6 moving packets.
- Near-miss: #63 nearest for all 8/8
  moving packets.

These rankings agree between assumed
XZ and XYZ comparisons, but they are
not verified world-aligned coordinates.
The trio #11/#38/#40 are **never**
among the closest three on the
sampled moving Ball candidate in
**any** trial. Even a closest tree
can be *missed* (#63 in near-miss),
so ranking is not a contact classifier.

### Position/cache copy evidence and non-atomic read caveat

The nested 12-byte triplet matched
the captured `Ball+0x30` exact bytes in
**37/45** foliage, **34/39** wood and
**18/26** near-miss samples. It also
matched `Ball+0xCC` in the **same**
sample counts, indicating source candidate
copies at `+0x30`/`+0xCC`
merit original PPC writer tracing. Note
that **no 12-byte Ball span was an exact
match across *all* packets**, and the
nested triplet matched `Ball+0xAC` in
**0** packets. Given the non-atomic
RPC sequence and observed read spans,
this is consistent with potential
update-between-reads or cached state,
not proof of a rendered-ball XYZ
or physics velocity mapping.

Both other trials had identical **entire
first Ball candidate/nested window** to
the initial foliage trial, but selected
player records differed at 20 initial
word offsets and all 94 initial tree
records differed only in `+0x4C/+0x50`.
The initial native savestate, exact
swing power/pose, visual collision time
and source receiver dispatch still are
not established.

**Research decision:** deprioritize
`Tree[11/38/40]+0x24/+0x2C` as tree-hit
latches and *do not train*. Prioritize
review of the three already-recorded
Dolphin-window MP4s, especially around
the source candidate trajectory bends,
then inspect original PPC source writer
dataflow and focused tree-nearest
collision candidates only with
visual timing corroboration. An
additional broad native RAM scan or
uncontrolled swing series would not
currently be evidence efficient.
`training_approved=false`.


## Memory-only follow-up: directed response and moving-only aliases

The user explicitly requested that **no gameplay video be
uploaded** and that research instead continue using the
existing three original private read-only source-captured
RAM logs. Respect this: do NOT ask the operator to
upload the videos again. No additional Dolphin run,
savestate change, user swing or new recording is
needed for the present investigation.

One outstanding analytical weakness of the prior
`source-phase-triage-SAFE.json` report was that
`adjacent_displacement_length_ratio` equals
`max(previous_length,next_length) /
min(previous_length,next_length)`. Its **unsigned**
ratios of 1.128 (leaves observed at turn 66.06°)
and 3.986 (wood observed at 59.79°) do **NOT**
indicate whether the sampled Ball candidate's
displacement got larger or smaller after the
turn. Inferring that the wood contact slowed
the ball more from the 3.986 ratio alone
would be unsound. Likewise, 37/45, 34/39,
and 18/26 exact nested-to-`Ball+0x30`
packet matches occur over trials that
contain many stationary pre-shot and
post-shot samples; **whole-recording percentages
are not motion-specific agreement**.
The original source `+0x24/+0x2C`
tree-field updates were not independently
typed as integer, pointer, float or
collision state.

Created the **offline-memory-only**
`scripts/p0_tree_contact_memory_response_private.py`
and synthetic regression tests
`tests/test_p0_tree_contact_memory_response_private.py`.
It reuses the original 110-packet/15-tree-array
SHA/checksum/schema validator, does not
load Dolphin, fetch footage, call Felk,
read/write game process memory or
modify existing source captures, and
does not output native pointer/value/XYZ.
It creates only a new exclusive
`tree-contact-memory-response-SAFE.json`
under the same original private session.
The new fields describe:

- **Signed after/before ratios**, both
  raw displacement size and per-host-second
  normalized, at every sustained
  source `Ball+0x30` triplet direction
  turn. This allows candidate
  decreasing vs increasing displacement
  to be distinguished, but is **not a
  guest physics velocity, restitution
  coefficient or impact timestamp**:
  4 Hz non-atomic host samples cannot
  verify same interval in guest frames,
  and the coordinate frame is unproven.
- **Moving-only byte aliases**:
  classify each source packet by whether
  Ball `+0x30` changed vs preceding packet,
  then count exact same-packet and one-packet
  lead/lag matches of nested triplet with
  Ball `+0x30,+0xCC,+0xF0,+0xFC,+0xAC`.
  Separately count exact `+0x30`
  versus `+0xCC` copying while actually
  dynamic, so idle equality cannot create
  a false confidence of active-frame
  source equivalence.
- **Native tree-word category audit**
  of all 94 records at `+0x24,+0x2C,
  +0x48,+0x4C,+0x50`, for every original
  full-array snapshot. Labels distinguish
  zero, aligned MEM1-range/MEM2-range
  pointer-like bit patterns, small integer
  bits, plausible BE-f32 bits and
  remaining. These are categories,
  **not proven native C++ field types**.
  Also tests exact `+0x24` vs
  `+0x2C` equality.
- **Launch-aligned tree-update overlap**:
  for each trial, find the first 8-packet
  tree-snapshot interval bracketing the
  beginning of its longest Ball candidate
  motion run. Count `+0x24/+0x2C`
  changes and overlaps across **both
  reported contact trials AND the near-miss**,
  separately from widespread
  `+0x4C/+0x50` updates. This tests
  a more precise background-update
  explanation of the previously suspected
  six tree-contact-only member sites.

The test and report deliberately avoid
assigning a collision time, impacted tree
identity, wood/foliage handler, physically
meaningful ball velocity or impulse.
The previously observed high turns
(66.06° leaves; 59.79° wood; 14.74°
no-contact) remain **candidate-level**
until original native source/receiver
provenance can establish physics
semantics. No public code, ROM words,
tree coordinates, private raw RAM,
game assets or personal data are
included in Git. Draft PR stays
`training_approved=false`.


## Operator signed-response report and original Ball self-reference correction

The operator shared original **`tree-contact-memory-response-SAFE.json`**
generated at `ea46eef6c89869fcbafead00b45a96eff42fcf1f`,
using the already SHA-verified **110 live source-selected Ball
packets / 15 tree-array snapshots**. No new gameplay
or video has been used; the user explicitly wants
**memory-only analysis**.

### Signed candidate displacement, not true collision physics

The strongest Ball+0x30 BE-f32 candidate direction turn
and the newly computed **after/before per-host-second
displacement ratio** in each trial are:

| Operator actually observed | Original intent | Turn | Original sample | After/before ratio | Interpretation |
| --- | --- | ---: | ---: | ---: | --- |
| **Wood** | `leaves` | **59.79°** | **28** | **0.2511** | candidate displacement rate fell by ~74.89% |
| **Leaves/foliage** | `wood` | **66.06°** | **27** | **0.8841** | candidate displacement rate fell by ~11.59% |
| **No contact** | `near_miss` | **14.74°** | **11** | **0.8993** | candidate displacement rate fell by ~10.07% |

These are strongly distinguishable observed **candidate
trajectory profiles**, and the wood event merits the
highest priority for native response tracing. However,
each shot differs in input profile and candidate
movement duration; sparse ~4 Hz non-atomic RPC
reads are not physics-frame-synchronized, and
`Ball+0x30` is not independently proven to
be the rendered ball's world-space position.
**Do not interpret the ratio as an actual physical
velocity/restitution/energy coefficient**.
Later near-stop intervals (wood source sample 30
ratio 0.0447 and foliage sample 33 ratio
0.0015) may reflect ordinary game-state
transitions/landing, not collision damping.

### Stationary copy agreement was misleading

The earlier high overall nested-to-Ball and
Ball-to-cache equality was driven by a majority
of **stationary** samples. Across all three:
- **Ball+0x30 vs Ball+0xCC**:
  exact bytes in **84/84** Ball-stationary
  samples, but only **6/26** Ball-moving
  samples (**2/7 wood**, **2/10 leaves**,
  **2/9 near-miss**).
- **Nested source triplet vs Ball+0x30**:
  same-packet exact match in **83/84**
  Ball-stationary samples but **6/26**
  Ball-moving. Nested `+0xAC` matching
  zero across moving and idle samples.
- Motion-only same-packet cache equality
  is too weak to declare either cached
  location the independently authoritative
  rendered/physics position. This may be
  non-atomic reads, separate cache lifecycles,
  interpolation or other unverified writes.

**More important original source constraint**:
the *original seven-capture* SHA-qualified
`audit_p0_seven_numbered_source_pairs_private.py`
reader enforces:
`u(ball + 0x4C) == ball + 0x30`.
That is a *source-qualified pointer self-reference*
in the original archival cohort. Our **new November
operator live** `p0_tree_contact_record_private.py`
recorder reads `nested = u(ball+0x4C)` and
checks only that the resulting 12-byte MEM2
window is bounded, **not** that it equals
`ball+0x30`. Crucially, it reads the 448-byte
Ball window first and the so-called
`nested` triplet **later through a second
RPC call**. Therefore, IF the original pointer
self-reference still holds in all 110 live
packets, this is a **re-read of the exact
same native memory address**, not an
independent nested transform object.
A mismatch during flight would then be
expected under non-atomic updates and
MUST NOT be treated as evidence of a
second position cache. This remains a
**conditional hypothesis** until the
new live pointer identity is checked.

### Tree "contact-only" candidates are pointer-like and largely in the no-contact control

Across all 15 original complete snapshots
(94 source tree records each = 1410
tree-record-word observations):
- `Tree+0x24`: **1410/1410 aligned
  MEM2-range words** (pointer-like).
- `Tree+0x2C`: **775/1410 aligned
  MEM2-range words**, **635/1410 zero**.
  These are pointer/nullable-handle
  *bit patterns*, NOT C++ type proof.
- `Tree+0x48`: **1410/1410 zero**.
- At each trial's first sustained Ball
  candidate movement interval, the
  `+0x24/+0x2C` cochange sets had
  **23 (foliage), 14 (wood), and 11
  (near-miss)** tree entries. The contact
  sets overlapped in **14** source
  tree indices, of which **11** also
  changed during the control. Thus
  **11 of the 14 common "contact" tree
  changes are not contact-exclusive**;
  three further common candidates
  still need source-object receiver
  proof and are **not** a hit latch.
  Source tree indices 11,38,40 are
  not spatially near the recorded Ball
  candidate under the already-unverified
  shared-axis hypothesis.
- For all three trials, `+0x4C/+0x50`
  changed across all 94 trees around
  movement. Original PPC Tree source
  includes `lwz +0x24` and float
  stores at `+0x4C/+0x50` but native
  Tree class receiver for those specific
  94 live records is still unresolved.

### New gated memory-only test of the self-reference, not a guessed identity

Added `scripts/p0_tree_live_ball_selfref_private.py`
and `tests/test_p0_tree_live_ball_selfref_private.py`.
The script rereads **only** the already-private,
previously SHA-verified 110 live JSONL
source samples, and for each packet:
- decodes the source-selected Ball address
  from selected-player-record `+0x88`;
- decodes the Ball object `+0x4C`
  nested pointer;
- checks exact private native pointer
  identity `Ball+0x4C == BallAddress+0x30`,
  plus bounded MEM2 and stable ownership;
- segregates exact Ball `+0x30,+0xCC,
  +0xF0,+0xFC,+0xAC` matches during
  moving samples and compares neighbor
  sample lags.
It writes **only sanitized counts/booleans**,
no raw pointers, values, source instructions,
game position, private paths, or native
assets, to the new exclusive local
`tree-contact-ball-selfref-SAFE.json`.
The original raw capture/manifest/summary
are unchanged; no Dolphin, video, new
swing or guest write required.

**Why this check matters:** an original
`Ball+0x4C` pointer selfref would
make the previous "nested position"
and `Ball+0x30` both views of the
*same address at different moments*,
rather than two separate memory
objects. This directly narrows the
native copy/writer investigation,
leaving Ball `+0xCC,+0xF0,+0xFC`
and their original PPC writer/reader
provenance as the next unresolved source
dataflow. None of this currently proves
wood or leaves native physics.
`training_approved=false`.


## Original live Ball selfref verified in all 110 packets; next bounded native writer audit

Operator ran the original in-repo offline
`p0_tree_live_ball_selfref_private.py` against
the existing SHA-verified 2026-11-11
wood-intent/leaves-intent/near-miss recording
session; reported `original_sha_verified=true`,
**110 original source-selected Ball packets**.
The exact saved private selected Ball+0x4C
pointer was **`Ball+0x30` in every packet**:

| Human reported observation | Recorded intent | Exact selfref matches | Selected Ball identity |
| --- | --- | ---: | --- |
| Leaves | `wood` | **45/45** | stable |
| Wood | `leaves` | **39/39** | stable |
| No contact | `near_miss` | **26/26** | stable |
| **All** | | **110/110** | same across trials |

This **confirms** the native pointer/address
identity, not merely a matching twelve-byte
float value. The previous term "nested
translation candidate" was misleading:
it is a **later RPC re-read of the identical
`Ball+0x30` native memory address**,
not a separate allocated position object.

The recorder reads the 448-byte Ball source
object in an earlier bridge memory read,
then the selected player record, then
12 bytes by the `Ball+0x4C` pointer.
Because these operations are not atomic,
the memory at the same physical address
can legitimately differ during flight.
Do not treat a mismatch as two
physical position vectors or as
interpolation/collision-induced
cache disagreement. As measured,
same packet selfref reread matches
are only **6/26 during Ball motion**,
vs **83/84 during Ball stationary
candidate state** (one stationary
near-miss anomaly).

The separately recorded 12-byte
`Ball+0xCC` cache **also** equals
Ball+0x30 in only **6/26 moving packets**
and 84/84 idle packets. Compared to
captured Ball+0x30 in the *following*
source packet, `Ball+0xCC` equals it
**3 times per original trial**
(3/7 wood, 3/10 leaves, 3/9 miss).
This one-packet apparent *lead*
is **not** a prediction proof or an
exact guest-frame cache relation:
the operator's ~4 Hz sampling, possible
same-RPC non-atomicity and source
update ordering are unverified. The
`Ball+0xAC` 12-byte field matched
`Ball+0x30` in **0/26** moving
samples (and did not match during
stationary samples), and native
velocity semantics are still NOT
proven.

Original **signed** Ball+0x30
candidate turn ratios remain:
operator-observed wood **59.79°**
at packet 28, after/before
host-second-displacement **0.2511**;
foliage **66.06°** at packet 27,
ratio **0.8841**; no contact
**14.74°** at packet 11,
ratio **0.8993**. Because the
native sampled Ball+0x30 coordinate
frame, actual tree contact,
guest frame atomicity, comparable
swing profiles, collision impulse,
and branch semantics remain
unproven, these numbers are
**candidate motion evidence**,
not true material-specific
coefficients. No training.

### Source-side next step: inspect original PPC writer syntax, not broad RAM scans

Added `scripts/p0_tree_ball_source_store_inventory_private.py`
and synthetic-only
`tests/test_p0_tree_ball_source_store_inventory_private.py`.
The source audit reads the **original seven-pair
SHA-gated Rev1 MEM1/MEM2 archive**, verifies
original Golf scene, FieldManager
94×84 Tree source loop, Tree
source anchors, and the exact
five Ball→GolfKCol plus seven reverse
source-code calls before examining
**bounded public .text units only**
(Ball, Simulation, Player, PlayerManager).

The script enumerates direct PPC
`stfs`/`stw` instructions with
D-form displacements overlapping
`+0x30/+0x34/+0x38`,
`+0xAC/+0xB0/+0xB4`,
`+0xCC/+0xD0/+0xD4`,
`+0xF0/+0xF4/+0xF8`,
`+0xFC/+0x100/+0x104`.
It also scans for bounded
`lwz rN,+0x4C(rX)` followed by
`stfs 0/4/8(rN)` without
intervening branch or obvious GPR
clobber, a candidate for writing
through the demonstrated live
self-pointer. Includes public known
`Ball fn_80299C70` potential cache
update function window and
`Player fn_802A0320`
potential translation writer window.

**Crucial caveat:** matching PPC
D-form field offsets on *other
objects* are not proof of a store
to the selected Ball. Even pointer
chaining is syntactic unless the
receiver type/dataflow are proven.
This study does **not** establish
the game executed these writers
in any of the November shots,
nor the native wood/leaf contact
branch or impulse. Output is
only public-code-relative
instruction site labels and
categorical counts, with **no
ROM bytes, original code words,
private pointers, coordinates,
raw memory, file paths or hashes**.
Do not infer physics from source
ownership or method names alone.

The next operator task is to run
this **read-only original archive
PPC audit**, not to record
another shot or upload video.
The existing original seven-capture
archive is required; the 110
live JSONL packets cannot themselves
recover native .text. Research
branch PR remains draft,
`training_approved=false`.


## Source-store output reviewed: original PPC cache windows and seven self-pointer chains

The user pasted original successful source-only
`P0_ORIGINAL_TREE_BALL_SOURCE_STORES_V1`
at pinned source head `cda839e914687518418a8d1764c81cb114f91a6e`.
The script passed SHA qualification of private original
seven-capture Rev1 source capture **7**,
Golf scene and 94 source-owned Tree slots,
and exact **5 Ball→GolfKCol and 7 reverse**
source-call gates. These are original archive
STATIC instruction-site findings; they do not
prove the candidate instructions actually
executed during the November wood/leaf shots.

### Specific source sites, not object receiver proof

Original Ball source unit contains **57**
D-form `stfs/stw` *displacement matches*,
Player contains **39**,
PlayerManager contains **10**,
and scanned Simulation contains **zero**.
Each unit includes code operating on many
different object types, and same numeric D-form
displacement on one register does **not**
establish active selected Ball receiver identity.

Within the public Ball compiled code unit
(`RPGolMapObjBall`), the known
`fn_80299C70` potential goal/cache-update
window contains exactly these relevant
three-component floating-point store sites:

| Candidate source member displacements | Original Ball-unit instruction offsets |
| --- | --- |
| `+0xCC/+0xD0/+0xD4` | `+0x2D04/+0x2D0C/+0x2D14` |
| `+0xF0/+0xF4/+0xF8` | `+0x2F6C/+0x2F70/+0x2F74` |
| `+0xFC/+0x100/+0x104` | `+0x2FA8/+0x2FAC/+0x2FB0` |

Other original Ball-unit source candidates
storing float triples at `+0x30/+0x34/+0x38`
are `+0x3E48/+0x3E4C/+0x3E50` and
`+0x3EAC/+0x3EB0/+0x3EB4` (both outside
the known `fn_80299C70` window);
those might operate on other objects.

Seven additional bounded syntactic
`lwz rP,+0x4C(rReceiver)` followed by
`stfs fX,+0,+4,+8(rP)` chains emerged:
- Ball `+0x1788`, `+0x1AAC`,
  `+0x38DC` (pointer load offsets;
  first/last store sites at
  `+0x179C..+0x17BC`,
  `+0x1ABC..+0x1ADC`,
  `+0x38F4..+0x3918`);
- Player `+0x1D88`, `+0x2200`;
- PlayerManager `+0x0BE0`, `+0x0C70`.

In the live SHA-verified 110 packets, the
*selected active Ball* `+0x4C` pointer
always equaled *selected Ball +0x30*.
The source chains may thus be plausible
translation writers **if**, and only if,
their receiver is source-proven to be
that selected Ball object. This receiver
binding and dynamic execution are unresolved;
some native PPC `lwz +0x4C` instructions
can load an unrelated object's member.

Added a narrower second-pass
`scripts/p0_tree_ball_writer_register_context_private.py`
plus synthetic-only
`tests/test_p0_tree_ball_writer_register_context_private.py`.
This reads only the same original SHA-gated
7-pair Rev1 native source, verifies the
original 94×84 Tree scene and Ball↔KCol
source call gates, then checks **exact**
original instruction sites instead of
broad displacements:
- Whether each of the three stfs
  components uses the same **base GPR**,
  and each register's original **FPR
  source index** (bounded, control-transfer-
  aware nearest linear load/FP operation
  syntax, NOT runtime or full CFG provenance).
- Whether each of the seven pointer
  triples has the same source GPR
  loaded by `lwz +0x4C` and no
  **known** intervening control transfer
  or simple GPR clobber; no claim
  of exhaustive register alias analysis.
- How many direct static PPC `bl`
  sites call the **exact published function
  entry** for `Ball fn_80299C70`
  or `Player fn_802A0320`, including
  source-unit-relative caller sites.
  No inference of native execution
  in a tree impact.

This second pass **never prints original
instruction words, code bytes, private
source RAM addresses, game assets, XYZ
or original hashes**, and does not
connect to Dolphin, run any swing or
ask for video. Results indicate
syntactic source likelihood only;
`selected_ball_receiver_binding_proven=false`
and `training_approved=false`.
Next operator input should be the
sanitized new PPC register-context
report from original private archive,
not new gameplay.


## Original PPC register-context report reviewed — common r27 but no active receiver yet

Operator supplied the completed original source-only report
`P0_ORIGINAL_TREE_BALL_WRITER_REGISTER_CONTEXT_V1`,
original seven-pair SHA-qualified capture **7**. The
source code gate `original_sha_scene_tree_and_kcol_gates_verified=true`
was met, but every receiver/execution/velocity/material branch proof
flag remained false.

**Three complete static cache-source store triplets share base GPR r27**:
- Ball source unit `+0x2D04,+0x2D0C,+0x2D14`
  stores candidate members `+0xCC,+0xD0,+0xD4`;
  each precedes a nearby `lfs` for the same FPR f0.
- Ball unit `+0x2F6C,+0x2F70,+0x2F74`
  stores `+0xF0,+0xF4,+0xF8`;
  FPR indices f3/f0/f4, one load nearby, others
  previously blocked by bounded control-flow analysis.
- Ball unit `+0x2FA8,+0x2FAC,+0x2FB0`
  stores `+0xFC,+0x100,+0x104`,
  FPR f2/f1/f0 with bounded preceding `lfs` candidates.

All nine `stfs` instructions use **r27** for the native
destination register. This narrows the audit to how that
register is initialized within the published
`Ball fn_80299C70` window, but r27 == the selected live
Ball address is **not established**. Other source numeric
displacement matches use different base registers:
`+0x30` stores in Ball unit use r3; three groups
of `+0xAC` stores use r1, r23, r29 respectively.
Because r1 is the conventional PPC stack pointer,
**r1+0xAC is likely a stack-local store, not Ball+0xAC**;
do not count it as an active Ball object's state writer.

**Seven** earlier source `lwz +0x4C` →
three component `stfs +0/+4/+8` chains have
their pointer-register consistency confirmed with
no obvious intervening control or recognized GPR clobber.
The original report specifies receiver GPR indices:
Ball source loads at +0x1788 (r30), +0x1AAC (r3),
+0x38DC (r31); Player at +0x1D88 (r4), +0x2200 (r5);
PlayerManager +0x0BE0 and +0x0C70 (r3). This is
syntactic pointer continuity only. It does **not**
prove any of these pointer chains reads
the specific selected active Ball object
or executes at tree impact.

Two direct public Ball source-unit `bl` callers target
the **exact native `fn_80299C70` entry**:
`Ball+0x2B8C`, `Ball+0x2C80`. Another
`PlayerManager+0x0F2C` calls the published
`Player fn_802A0320` entry.
No indirect caller census or dynamic call trace
has been established for the latter. The two direct
cache calls are prioritized for upstream receiver
argument trace.

**Follow-up implemented**:
`scripts/p0_ball_cache_r27_lineage_private.py`,
with `tests/test_p0_ball_cache_r27_lineage_private.py`
and Win/Ubuntu CI. It re-verifies the SHA-qualified
original seven-pair source capture and native code gates,
then checks:
- bounded source syntactic writers to destination r27
  from the beginning of the published cache-function window
  up to each of the three triplets, including
  `mr` (PPC OR rD,rS,rS), `lwz`, `addi`,
  pointer arithmetic/known logical and other common
  assignments; records only public source-relative
  code location and register indices;
- the nearest preceding `lfs`/other FP producer
  for each exact `stfs` site in the three groups,
  with source GPR and signed D-form displacement;
- the two exact direct cache-entry `bl` instructions
  and nearest bounded syntactic r3 argument
  assignments, stopping on prior control-transfer.

This is **not** complete native CFG/SSA,
an active object receiver binding,
or dynamic evidence of the wood/leaves branch.
The new study outputs no original PPC code
words, actual native heap pointers or
game asset/XYZ data and does not access Dolphin,
video or live memory. No physics trained:
`training_approved=false`. User requests
**memory-only** progress; do not ask for videos.


## Operator r27-lineage result — candidate CC input copy, possible FC downstream duplicate

The user ran the original SHA-verified Rev1 capture **7**
`P0_ORIGINAL_BALL_CACHE_R27_LINEAGE_V1` audit at
`ea64d20bf59b3df022dfffda0067ba0f0c93b5ff`.
Result `original_seven_pair_SHA_and_scene_qualified=true`,
`training_approved=false`, and all native impact,
Ball-world-velocity, wood/foliage material and
active-selected-Ball receiver flags explicitly **false**.

### Source-level register facts

In the published Ball source unit:

- Known cache routine entry `0x80299C70` corresponds
  to Ball-unit `+0x2C98`. At `Ball+0x2CB8`
  (`+0x20` relative to the routine's published entry),
  PPC syntax is `mr r27,r3`. The existing partial
  register-destination scanner found this to be the
  **sole recognized r27 definition** prior to all three
  cache triplet writers. This is a syntactic report,
  not a complete CFG proof against unrecognized writes
  or crossing a call.
- Two exact calls to that native entry:
  `Ball+0x2B8C` and `Ball+0x2C80`.
  Their nearest preceding bounded `r3` assignments
  are `mr r3,r31` at `Ball+0x2B80` and
  `Ball+0x2C70`. If original r31 holds
  the relevant Ball object in the caller, this
  provides a plausible `caller r31 → incoming r3
  → callee r27` receiver chain. **Caller r31
  provenance and execution during tree impact
  are not yet verified**.
- In the first source cache triplet,
  `Ball+0x2D00`: `lfs f0,0(r3)`,
  `+0x2D04`: `stfs f0,+0xCC(r27)`,
  `+0x2D08`: `lfs f0,4(r3)`,
  `+0x2D0C`: `stfs f0,+0xD0(r27)`,
  `+0x2D10`: `lfs f0,8(r3)`,
  `+0x2D14`: `stfs f0,+0xD4(r27)`.
  This is a **strong candidate for a 12-byte
  vector copy** from the current r3 data source
  to r27+0xCC, although r3's pointer
  origin after callee prologue remains to
  be proved and the stores are not known
  to execute at tree impact.
- In the later store group,
  `Ball+0x2F98` is an `lfs f2,+0xCC(r27)`,
  `+0x2F9C` `lfs f1,+0xD0(r27)`,
  `+0x2FA0` `lfs f0,+0xD4(r27)`.
  Then `+0x2FA8/+0x2FAC/+0x2FB0`
  store `f2/f1/f0` to
  `r27+0xFC/+0x100/+0x104`.
  The *single* intervening instruction at
  `Ball+0x2FA4` must be decoded and
  checked for control/FPR/source-memory changes
  before upgrading this from candidate
  to a source-proven continuous copy.
- The middle `Ball+0xF0/+0xF4/+0xF8`
  store group has only partial input
  provenance: a nearby `lfs f0,+0xD0(r27)`
  at Ball `+0x2F64` feeds an
  `stfs f0,+0xF4(r27)` at `+0x2F70`
  in the bounded linear analysis.
  Other components have unresolved prior
  control flow, so **no complete copy
  or velocity interpretation** follows.

The live source-qualified 110 Ball packets independently
prove `u32(Ball+0x4C)==Ball+0x30`, while
`Ball+0xCC` differed from `Ball+0x30`
during 20/26 movement packets. This
is consistent with separate cache stages
rather than additional independent object
allocations, but the exact game/physics
semantics of `+0xCC/+0xF0/+0xFC`
and the selected Ball receiver during
the original native stores are unproven.

### New focused native memory-only audit

Added
`scripts/p0_ball_cc_fc_copy_receiver_private.py`
with synthetic-only
`tests/test_p0_ball_cc_fc_copy_receiver_private.py`
and Windows/Ubuntu CI. On the original
seven-pair SHA-verified Rev1 native archive,
it demands the exact sequential 6 PPC
`lfs/stfs` instruction pair sequence
of the r3→r27+CC triplet, re-verifies
six source/destination instructions around
CC→FC, and checks the *intervening*
`Ball+0x2FA4` native opcode syntax
for possible control transfer and
register clobber without printing native
instruction bytes. It separately reports
r3 register assignments between
`Ball+0x2CB8` and the CC input lfs
source, along with bounded possible
definitions of caller r31 near the two
exact cache routine BLs. It **will
not** infer complete CFG/SSA,
selected live Ball object,
impact timing, velocity or
wood-versus-leaf material branch
from such static syntactic evidence.

All outputs are public source-relative
locations, register numbers, syntax
classes and bounded counts. It does
not open Dolphin, contact users for
video, perform live RAM reads, modify
capture files, embed original PPC code
words, export private addresses or
fit game physics. `training_approved=false`.


## Original exact CC-to-FC source-copy report — global input pointer is the next identity gate

Operator executed `P0_ORIGINAL_BALL_CC_FC_NATIVE_COPY_AND_RECEIVER_AUDIT_V1`
on original capture **7** of the SHA-gated source archive.
The native source, scene, and 94-tree source gates passed
(`original_seven_pair_SHA_source_qualified=true`).
The new report confirms two **static exact** vector-copy
sequences inside the native function at `0x80299C70`:

1. Six contiguous native instructions at Ball source unit
   `+0x2D00/04/08/0C/10/14` interleave
   `lfs f0,0/4/8(r3)` with
   `stfs f0,+0xCC/+0xD0/+0xD4(r27)`.
   These exact register assignments and offsets
   are source-verified, but `r3` is not
   independently proven to point at the selected
   live Ball's position. The cache receiver
   `r27` is likewise not bound to that
   selected live Ball at any observed impact.
2. At Ball source unit `+0x2F98/+0x2F9C/+0x2FA0`,
   three native `lfs` load `r27+0xCC/+0xD0/+0xD4`
   into f2/f1/f0. At `+0x2FA8/+0x2FAC/+0x2FB0`,
   corresponding `stfs` instructions
   write those unchanged registers into
   `r27+0xFC/+0x100/+0x104`.
   The intervening native original source
   instruction at `Ball+0x2FA4`
   is **`lwz r0,+0x108(r27)`**.
   It changes an integer GPR only, and
   does not clobber the input floating-point
   values, r27, memory source or control
   in the sequential instruction window.
   Thus the **static CC→FC copy is established**;
   its dynamic execution, source object
   and physics semantics remain unverified.

**The critical remaining source difference**
is that `r3` is modified **after**
`mr r27,r3` at `Ball+0x2CB8`.
The native source contains
`lwz r3,-23304(r13)` at
`Ball+0x2CD4` and again at
`Ball+0x2CF8`, plus
`lwz r3,+0x4C(r3)` at
`Ball+0x2CFC`. That second
r13-relative global load, member pointer
dereference and `lfs f0,0(r3)`
at `Ball+0x2D00` are consecutive.
The immediate input to the CC cache
copy therefore comes through **a
global object pointer's +0x4C field**,
rather than necessarily the original
receiver r3. The global object may
or may not be the selected live Ball.
The original live 110-packet memory
capture separately established that
the **selected Ball** itself has
`Ball+0x4C -> Ball+0x30`; source
code alone has not shown that
the r13-global object is the selected
Ball. Avoid collapsing these two
different evidence claims.

The two static callers of the cache
entry each have a bounded previous
`r31 <- r3` assignment: native
Ball source `+0x2B08` for the
`+0x2B8C` direct call and
`+0x2C5C` for the `+0x2C80`
call. The source caller r31
would therefore plausibly preserve
an original receiver pointer, but
its dynamic identity as the Ball
selected in November is still
unproven.

Created `scripts/p0_ball_cc_global_caller_source_private.py`,
`tests/test_p0_ball_cc_global_caller_source_private.py`
and Windows/Ubuntu offline CI. This
next source-only study checks the
exact original r13-global source
loads and +0x4C pointer dereference,
small bounded PPC control-flow
branches around them, exact caller
r31-save/r3-restore and possible
intervening GPR clobbers. The script
requires the original seven-capture
SHA-qualified private archive and
preserves all private data. Output
includes only public Ball source-relative
code sites, register numbers, signed
displacements and bounded counts;
no PPC instruction words, native heap
addresses/XYZ, player recordings,
ROM data or files are exported.

Neither `+0xCC` nor `+0xFC`
is established as a physics position,
collision velocity, wood material code
or canopy damping. No tree contact
instruction, exact guest impact frame
or native branch has been identified.
The user explicitly wants memory-only
investigation and does **not** wish
to upload video. No additional
gameplay is required for this
source qualification step.
`training_approved=false`.


## Crucial original branch gate: exact cache stores do not imply executable path from 0x80299C70

The original operator ran the SHA-gated
`P0_ORIGINAL_BALL_NATIVE_CACHE_SOURCE_GLOBAL_AND_CALLER_V1`
audit on Rev1 original source capture 7, following
the earlier static native three-float `r3→r27+CC`
and `r27+CC→r27+FC` copies. The result
**does not yet establish executable path
reachability of either group from the
published cache-function entry**.

The original source audit returned
the following exact source-relative
native direct/conditional transfer
sites in the small published Ball unit:

| Original site | Static PPC transfer | Target |
| --- | --- | --- |
| Ball+0x2CCC | **unconditional `b`** | **Ball+0x2FB8** |
| Ball+0x2CDC | `bc` BO=12 BI=2 | Ball+0x2CF4 |
| Ball+0x2CEC | `bc` BO=4 BI=2 | Ball+0x2CF4 |
| Ball+0x2CF4 | linked `bl` | Ball+0x28B8 |

**Crucial interpretation:** the
unconditional branch at Ball+0x2CCC,
if reached from the published
`fn_80299C70` entry (Ball+0x2C98),
jumps to Ball+0x2FB8, **past**
the exact `+0xCC` writer
at +0x2D00..+0x2D14 AND the
`+0xFC` writer at
+0x2F98..+0x2FB0. The
earlier source-copy finding remains
a **verified static instruction
relationship** but is NOT proof
that these instructions execute
when callers invoke the published
cache entry. A branch at or after
+0x2FB8 may jump *back* into
the copy code; other native
direct/indirect entries could reach
it, and function boundaries are
not independently proven. Thus
simply declaring those native
stores 'the active Ball cache
update function' would be premature.

Other original register findings:
- At Ball+0x2CB8 `mr r27,r3`.
- Ball+0x2CD4 and +0x2CF8
  both load `r3` from signed
  `-23304(r13)`; +0x2CFC
  follows the **second** load
  with `lwz r3,+0x4C(r3)`,
  then consecutive
  `lfs f0,0(r3)` at +0x2D00.
- Two native callers at Ball+0x2B8C
  and +0x2C80 save incoming
  `r3` to `r31` at +0x2B08
  and +0x2C5C respectively,
  then restore via `mr r3,r31`
  at +0x2B80 and +0x2C70.
  No recognized `r31` reassignment
  in the bounded linear spans,
  but the report showed 4
  and 1 intervening control-transfer
  instructions; exact per-path
  receiver preservation and
  actual selected-Ball identity
  remain unproven.

Added bounded static PPC CFG audit
`scripts/p0_ball_cache_cfg_reachability_private.py`
and synthetic-only regression
`tests/test_p0_ball_cache_cfg_reachability_private.py`
to check:
- exact original unconditional
  Ball+0x2CCC → Ball+0x2FB8,
  full native source/scene
  SHA and both exact copy gates;
- bounded direct PPC `b`/conditional
  `bc` targets and conditional
  fallthrough, with linked `bl`
  modeled as possible call-return
  fallthrough;
- whether a possible path from
  `0x80299C70` reaches
  Ball+0x2D00/04 and
  +0x2F98/+0x2FA8, and a
  bounded branch-route witness
  where one exists;
- direct static branches to
  suspected CC/FC source
  entry sites across the
  public Ball code unit.

This is a *bounded static
may-reachability model*.
A missing route is not proof of
native unreachability because
LR/CTR indirect paths and exact
function boundaries remain unresolved;
a found route is not evidence
of dynamic execution, collision
or native material response.
The report only prints public
source-relative code sites,
branch syntax and counts.
It does not export original
PPC words, private RAM,
native pointer values or XYZ.
No Dolphin, screenshots, video,
new swings or live writes.
`training_approved=false`.


## Original static CFG report: forward skip has a possible conditional back-route into CC and FC copies

The operator uploaded the original
`P0_ORIGINAL_BALL_CACHE_ENTRY_BRANCH_REACHABILITY_V1`
report generated on SHA-qualified private
Rev1 original seven-pair source capture 7,
at research branch head
`81a70fe4e1e35d81c4097d1625f69bc3e67b8cb0`.
`original_seven_pair_sha_and_scene_gates_passed=true`.
No Dolphin, additional swing, or gameplay video
was used; per user request all future work
on this branch stays **memory/native-source-only**.

**Crucial correction to the prior native
skip concern:** the original unconditional
PPC branch at published Ball+0x2CCC
to Ball+0x2FB8 **skips CC and FC
copy blocks on that initial straight-line
edge**, but the bounded static CFG shows
possible paths back into both blocks.
The CFG model explored **242 source
instructions**, including **31 conditional
`bc`**, **7 linked direct `bl`**,
**3 unconditional direct `b`**,
and **2 unresolved indirect `bclr/bcctr`**.
There were no successors leaving the
chosen coarse source window under
this model (NOT proof the function ends
there or external calls never execute).

The bounded *may-reach* model reports:
- Ball+0x2CB8 receiver-save site: **reachable**;
- Ball+0x2CD4 global source load:
  **reachable** through a route traversing
  conditional branches at
  **Ball+0x2FC4** and **Ball+0x2FCC**;
- Ball+0x2D00 original source
  `lfs` and Ball+0x2D04
  first `+0xCC` writer:
  **both reachable**;
- Ball+0x2F98 original
  `+0xCC` copy load, Ball+0x2FA8
  first `+0xFC` store, and
  Ball+0x2FB0 final store:
  **all reachable** under the bounded
  conditional-branch overapproximation.
- The two unresolved indirect transfers
  lie at Ball+0x2DAC and
  Ball+0x305C; direct inbound
  census found zero *exact direct
  targets* for +0x2D00 and +0x2F98,
  which does not exclude normal
  linear fallthrough.

**Do not read this as a verified
guest execution trace.** The
original reported route is a **possible
static path**, not a solved system
of concrete CR-register conditions,
guest frame timing, r31/r27 selected
object identity, or actual runtime
Ball/Tree collision handling.
In particular, a conditional
backedge could be unsatisfiable on
the relevant runtime state; no
material-specific handler is proven.
Our earlier conclusion that the
two native local copies exist
remains correct, but claims that
they actively update the selected
Ball during wood/canopy impacts
remain **unproven**.

**Focused next source-only audit**
`scripts/p0_ball_cache_backedge_condition_private.py`
and 12 synthetic regression tests
`tests/test_p0_ball_cache_backedge_condition_private.py`
are added to the same PR branch,
with Windows and Ubuntu CI:
- Strictly read the original
  SHA-qualified Rev1 MEM1/MEM2
  source and previous
  exact native-copy and CFG gates.
- Decode original PPC `bc`
  BO/BI conditions and targets
  at Ball+0x2FC4 and +0x2FCC;
  summarize whether simple
  CR-bit true/false interpretation
  applies, plus nearby bounded
  comparison syntax, never CR
  guest register values.
- For sources at +0x2D00,
  +0x2D04, +0x2F98,
  +0x2FA8 and +0x2CD4,
  report the static *witness*
  branch choices: direct target,
  conditional fallthrough, or
  assumed return after `bl`.
  The latter is an overapproximation,
  not guaranteed guest call return.
- Preserve the separate facts:
  original native memory-copy
  instructions exist, static
  may-reachability established,
  active selected Ball receiver
  UNKNOWN, source r13 global
  object UNKNOWN, dynamic
  branch outcomes UNKNOWN,
  wood/leaf collision physics
  UNKNOWN. `training_approved=false`.

Only source-unit-relative
code sites and syntactic branch
registers/offsets leave the private
original archive. No original
binary/code word, RAM value,
pointer, XYZ coordinate, game asset
or ROM is committed; original files
remain untouched.


## Original Rev1 branch-witness corrected: signed r28 < 0, not equality; trace actual r0/r28 writers

The operator supplied original
`P0_ORIGINAL_BALL_CACHE_BACKEDGE_CR_WITNESS_V1`
SHA-verified source report (Rev1 seven-pair
original capture **7**), no new shots, Dolphin,
video or guest RAM reads. It gives the **exact**
native PowerPC compare and branch pair:

| Ball-unit source | Native PPC syntax | Meaning |
| --- | --- | --- |
| +0x2FC0 | `cmpwi r0,0` (signed, CR0) | compare r0 with zero |
| +0x2FC4 | `beq +0x2FDC` (BO=12,BI=2) | divert when r0 == 0; **fall through when r0 != 0** |
| +0x2FC8 | `cmpwi r28,0` (signed, CR0) | compare signed r28 with zero |
| +0x2FCC | `blt +0x2CD0` (BO=12,BI=0) | **backedge taken when signed r28 < 0** |

**Important correction:** for PowerPC CR0,
bit **BI=2 is EQ** and **BI=0 is LT**.
Thus the second branch is a **signed
less-than-zero check**, *not* a
zero-equality check. The bounded
source-CFG witness to the local
`+0xCC` copy requires **both**
`r0 != 0` (not taking +2FC4)
and signed `r28 < 0` (taking
+2FCC), plus downstream branch
choices and assumed returns from
linked calls. These two predicates
are logically compatible for
some register values; that
does **not** establish those
values occur at runtime.

The full witness into
`Ball+0x2F98`/`+0x2FA8`
further includes branches
at +0x2CDC, +0x2D3C,
+0x2DCC, +0x2E90,
+0x2EF0, +0x2F60,
+0x2F84 and +0x2F94,
and assumes return from
linked BLs at +0x2CB0,
+0x2CF4 and +0x2F10.
Original code does not
yet prove condition
satisfiability along
the *whole* path,
native execution, selected
Ball receiver or a
wood-versus-foliage branch.
The copy-site native source
instructions and bounded
static reachability
remain verified, not
physics semantics.

**Next offline source test:**
`scripts/p0_ball_cc_backedge_signed_operands_private.py`
and synthetic-only
`tests/test_p0_ball_cc_backedge_signed_operands_private.py`
revalidate all prior private original archive
SHA/scene/source/native-copy/CFG gates,
then require those exact signed
`cmpwi` operands and EQ/LT
branch bit encodings and
target sites, trace the original
bounded witness's recognized
r0 and r28 register writers,
and enumerate any recognized
source assignments in the local
Ball+0x2FB8..+0x2FCC
prelude. It explicitly
separates a syntactic `li`
immediate value, a source
memory-load candidate,
an unknown called function
that may clobber volatile
GPRs, and runtime selected
Ball state. Decoder is partial:
unknown X-form/CFG/SSA
effects remain unproven,
so no runtime register
value or native collision
is inferred.

All outputs are public native
source-relative sites,
register indices, operation
categories and bounded
immediates; no original
ROM/PPC words, private
heap addresses, ball XYZ,
game assets, user video
or original RAM. No
training; `training_approved=false`.


## Original backedge condition provenance: byte flag from r3+0x5C and r28 from post-call r4

The operator ran the native source-only
`P0_ORIGINAL_BALL_CC_BACKEDGE_SIGNED_OPERAND_LINEAGE_V1`
audit against the previously SHA-gated seven-pair
Rev1 capture **7** at research source head
`87014b10a8aa7680af64637a8f90e04099e8aadf`.
The original archive and native source gates passed;
guest runtime CR/register values, selected Ball ownership,
actual tree impact, wood/leaf response and velocity
semantics all remain **unproven**.

**Source-qualified exact native predicate inputs:**

| Source unit site | PPC instruction | Qualified meaning |
| --- | --- | --- |
| Ball+0x2FBC | `lbz r0,+0x5C(r3)` | Reads a single unsigned byte; nonzero permits fallthrough past the subsequent `beq` |
| Ball+0x2FC0 | `cmpwi r0,0` | Signed zero compare in CR0 |
| Ball+0x2FC4 | `beq Ball+0x2FDC` | To stay on candidate backedge, **r0 != 0** |
| Ball+0x2FC8 | `cmpwi r28,0` | Signed r28 zero compare in CR0 |
| Ball+0x2FCC | `blt Ball+0x2CD0` | To take backedge, **signed r28 < 0** |

The original source report finds **no recognized
writes to r28** between Ball+0x2FB8
and its comparison. Its nearest recognized
writer on the bounded static witness is
**`mr r28,r4` at Ball+0x2CBC**.
The native **byte flag field source is
not proven to be the active Ball**:
the code at +0x2FBC reads from
the object currently in r3,
whose correct receiver provenance
must be established separately.
Do not equate its `+0x5C`
with Ball+0x5C solely by
instruction displacement.

**Critical CALLING-CONVENTION caveat
not captured by earlier analyses:**
there is an original **linked `bl` at
Ball+0x2CB0**, *before* the
`mr r28,r4` at +0x2CBC.
PowerPC EABI r4 is caller-volatile;
therefore **r28 is copied from the
POST-CALL value of r4**, and it
is *not yet proven to equal
the native cache function's
original incoming r4*.
Even if a caller had `li r4,-1`
or a nonnegative constant
before calling `0x80299C70`,
that value cannot be directly
used to decide whether the
backedge is feasible without
analyzing the intervening BL
callee or source register
restoration. Earlier casual
phrase "incoming r4" for
the +0x2CBC assignment
should be read as "r4 at
that instruction, after
the +0x2CB0 call."

**Further original memory-only source audit added:**
`scripts/p0_ball_backedge_postcall_arg_private.py`
and `tests/test_p0_ball_backedge_postcall_arg_private.py`.
This verifies the original
`lbz r0,+0x5C(r3)`,
`bl` at Ball+0x2CB0,
`mr r28,r4` at +0x2CBC,
the signed EQ/LT backedge
gates, and the original
two direct cache callers.
It reports only:
- the *public Ball unit-relative* linked BL target classification,
  and whether any recognized r4 writes occur
  before the r28 <- r4 binding;
- caller r4 writer *syntax* from the two
  known direct callers, explicitly
  flagging that the intervening
  callee may clobber r4;
- recognized r3 writer sites on the
  bounded branch witness before
  the byte-flag load, without
  asserting the selected Ball
  is the byte field's owner.

This audit does NOT prove
the function call's actual
runtime r4 effect, original
r3 object identity, exact
CFG predicate feasibility,
or the wood-versus-foliage
collision handler. No new
Dolphin session, gameplay
recording, video upload,
RAM write, native PPC instruction
word, original ROM byte, heap
pointer or world XYZ is needed
or exported.
`training_approved=false`.


## Native r28 backedge: two distinct caller arguments and a possible compiler register-save thunk

Operator supplied original success report
`P0_ORIGINAL_BALL_BACKEDGE_POSTCALL_R4_AND_FLAG_V1`
at SHA-qualified original seven-pair Rev1 source capture
**7**, head `d22fc2303f8826ba7edf8c43f878da6ccdd79e3a`.
The exact branch condition from the previous study is
**nonzero byte at current r3+0x5C** plus **signed
r28 less than zero**. Both native GPR roles are now
tighter, yet runtime selected Ball/impact identity
remains unverified.

**First original caller at Ball+0x2B8C:**
the nearest native r4 setter is **`addi r4,r4,+1`
at Ball+0x2B84**, rather than a fixed value.
Upstream original syntactic r4 loads/moves also
occur at +0x2B14, +0x2B34, +0x2B54, +0x2B6C
and +0x2B74. It is not safe to infer r4's sign
on that caller's path from this increment alone.

**Second original caller at Ball+0x2C80:**
the nearest original native r4 setter is
**`li r4,-1` at Ball+0x2C78**.
This directly suggests a negative sentinel
argument at the function's entry, **if the
caller executes this source path**.
That is significant because the candidate
backedge's second branch tests signed
r28 < 0.

**Critical qualifier:** original `fn_80299C70`
has a linked `bl` at **Ball+0x2CB0**,
before `mr r28,r4` at +0x2CBC.
No recognized r4 assignments were reported
in the linear instructions between that
call and r28's copy, but r4 is normally
volatile across PPC ABI calls. Thus
the second caller's `li r4,-1`
cannot yet be propagated through
the **actual callee** by relying
on calling-convention assumptions.

**Byte flag receiver is not the caller
or selected Ball by default**.
Native source instruction sequence:
`Ball+0x2FB8: lwz r3,-23304(r13)`,
`Ball+0x2FBC: lbz r0,+0x5C(r3)`.
Therefore the branch's byte comes
from an **r13-relative global object
pointer** (a runtime object not yet
identified). Even though the live
selected Ball self-pointer
`Ball+0x4C→Ball+0x30` was
confirmed in 110/110 samples,
that alone does not identify the
r13-relative global object's +0x5C
as a Ball field or a tree collision
material flag.

**Next source-only audit** implemented in
`scripts/p0_ball_prelude_save_thunk_private.py`
with 12 synthetic-only tests
`tests/test_p0_ball_prelude_save_thunk_private.py`
and Win/Ubuntu offline CI. The
placement of the linked BL at
+0x2CB0 relative to prologue
register saves suggests the call
might be a **compiler-generated
nonvolatile GPR-save thunk**
rather than gameplay code.
This is an unverified hypothesis,
not a symbol identification.

The tool decodes the actual
original PPC direct BL target from
the existing SHA-verified private
MEM1 executable bank. It will only
certify **r4 unchanged by that
callee** if the full bounded
target block consists exclusively
of recognized **plain `stw`
of r27–r31 to stack/save slots
through r1/r11**, followed by
unconditional standard `blr`.
Any other op, control transfer,
unbounded region, or failed source
SHA gate **abstains** from
r4 preservation; unknown ABI
callee effects are not presumed.
It separately rechecks the exact
`addi r4,r4,+1` and
`li r4,-1` at the two callers
and bounds any intervening
source writes/branches before
their direct calls.

If the actual original target
matches the strict save-thunk
pattern, the **static local
r28==entry r4 relationship**
would be established
through the call for this
source path, and the second
caller's negative r4
would make r28<0 feasible
on a conditional execution
path. This would still not
show the global object's
byte is nonzero, that the
function is actually called
during tree contact,
which live Ball receives
the copy, or native
wood-versus-leaf response.
No training.
Only relative instruction
indices, PPC syntax classes
and boolean source gates
are output, no original
binary/code words, RAM
pointers, game coordinates,
private capture paths,
screenshots or videos. No
Dolphin or new recording.
`training_approved=false`.


## Original Ball+0x2CB0 callee: stw-only save-thunk disconfirmed, register effect still unknown

Operator ran the original private seven-pair SHA-qualified
USA Rev1 source audit
`P0_ORIGINAL_BALL_ENTRY_SAVE_THUNK_R4_PRESERVATION_V1`
at source head `95847057d540dd874592ce26a52223b6e72d1453`,
capture **7**. Original native scene/source gates
passed. At native Ball+0x2CB0, the direct linked
BL's target lies inside the original MEM1 source-bank
candidate executable range. The immediately examined
first instruction **did not match** the previous
tool's strict `stw r27..31,(r1/r11)`-only helper
grammar: `callee_verified_plain_stw_count=0`,
`callee_is_store_only_GPR_save_thunk_verified=false`,
`r4_is_preserved_by_exact_callee_source_verified=false`,
with `instruction_not_plain_nonvolatile_GPR_store`.

**Interpretation: a negative pattern match is NOT
a proven r4 clobber.** The original first instruction
could be a PPC `stmw` (store multiple), an update-form
store, a common function prelude, an arithmetic or
control instruction, or some other source. None is
identified until further decoding. In particular,
the previous strict helper checker omitted
`stmw` entirely.

Original caller facts remain source-qualified:
Ball+0x2B84 `addi r4,r4,+1`
for BL at Ball+0x2B8C, and
Ball+0x2C78 `li r4,-1`
for BL at Ball+0x2C80, with no
identified intervening assignment at those
caller sites. At callee Ball+0x2CBC
`mr r28,r4` follows the linked
call at +0x2CB0. Until the callee's
source effects are verified,
**r28 == incoming r4 remains unproven**.
The source-byte branch still requires
nonzero `lbz r0,+0x5C(r3)`
at Ball+0x2FBC from an r13-global
object of unproven selected-Ball identity.

**Follow-up authored:** source-only
`scripts/p0_ball_prelude_callee_census_private.py`
and twelve synthetic-only regression tests
`tests/test_p0_ball_prelude_callee_census_private.py`,
with Linux/Windows CI.
It reruns all existing original SHA,
scene/94-tree and native source qualification,
then reads a bounded 24-instruction
source snippet **only in the original
private MEM1 archive** at the
actual native +2CB0 BL target. It emits
only categories/operand register indices
and instruction-index-relative sites
rather than native PPC instruction words,
ROM bytes, function target absolute
addresses, RAM pointers or XYZ.
The *only* automatic r4-preservation
promotion is a complete, bounded,
straight-line local **`stw` or
`stmw` of r27..r31 (and ordinary
PPC NOP)** followed by
unconditional **`blr`**.
Unknown instructions, control
transfers, update forms, or
out-of-bound targets abstain.
An unrecognized instruction
does **not** imply an r4 write.

This remains **native source/receiver
investigation, not collision physics**.
No proof yet of original guest
execution of that call during the
human-observed foliage or wood contact,
of the r13-global object belonging to
the selected active Ball, of a
wood-versus-leaf branch, or of
native collision impulse/restitution.
No Dolphin, video (operator explicitly
declines uploads), live RAM interaction,
new swings, or training.
`training_approved=false`.


## Original callee census resolves the missed r26 save: six stw + blr

Operator supplied the original success report
`P0_ORIGINAL_BALL_PRELUDE_CALLEE_INSTRUCTION_CENSUS_V2`
for private SHA-qualified Rev1 seven-pair
source archive **capture 7**, at pinned research
head `410e11e60077d9619d22e0a57ac7cb957b68120c`.

The **actual first seven PPC instructions at
the source-qualified BL target of Ball+0x2CB0**,
reported as instruction categories without
native instruction words or absolute callee
addresses, are exactly:

```text
relative 0: stw r26, -24(r11)
relative 1: stw r27, -20(r11)
relative 2: stw r28, -16(r11)
relative 3: stw r29, -12(r11)
relative 4: stw r30,  -8(r11)
relative 5: stw r31,  -4(r11)
relative 6: blr
```

**The previous two source tools missed a valid
nonvolatile-GPR save helper** because they
only allowed stores of **r27–r31**, while
the original starts with **r26**. This
previous negative test was a **parser
false negative**, NOT proof the callee
clobbered r4. Each of the six actual
`stw` instructions writes to memory
without modifying r4; the following
ordinary unconditional `blr` returns
to the caller. The additional 17
source instructions printed by the
24-instruction census come **after
the return** and do not affect this
straight-line helper path; the
report classified them as unrecognized
primary opcode 32 (PowerPC `lwz`),
likely part of adjacent restore
machinery, but that restore function's
symbol/entry is not yet verified.

**Updated source proof** in
`scripts/p0_ball_prelude_callee_census_private.py`
now accepts `stw r26..r31`,
`stmw` beginning no earlier than r26,
and NOPs as store-helper constituents,
and separately publishes
`exact_original_r26_through_r31_six_store_then_blr_shape_verified`.
The script **does not assume** the
entry argument r4 reaches the
`mr r28,r4` at Ball+0x2CBC merely
because the helper preserves it:
an additional bounded gate checks
all original function-entry instructions
up to Ball+0x2CB0, and all original
instructions from the helper return
to +0x2CBC for any possible
recognized r4 writes or unknown
instruction categories. The second
direct caller still explicitly sets
`li r4,-1` at Ball+0x2C78
and BLs the cache routine at
+0x2C80. **Only when the original
revised source audit confirms
the full entry → helper → r28
register chain** can the
negative second-caller argument
be source-qualified as r28.
No runtime tree contact or
material-specific physics follows.

The exact original native byte
flag on the candidate backedge
is still **`lbz r0,+0x5C(r3)`**
where current r3 is read from
an r13-global pointer. Its
runtime nonzero value, the
global object's identity and
whether native code takes
the source CFG route during
actual wood or leaf collision
remain unresolved. No
velocity, restitution, KCL
material identity or native
tree hitbox verified.
`training_approved=false`.

All artifacts remain source-only,
SHA-gated, read-only, and
sanitized: no original PPC
binary words, ROM extracts,
private RAM pointers, ball XYZ,
game assets, personal paths,
new gameplay, Dolphin or
video. Source study and
synthetic-only tests updated
on draft PR #422.


## Original save helper confirmed, entry r4 provenance blocked by two unclassified instructions

The operator reran the source-verified original
USA Rev1 private seven-pair archive **capture 7**
under head `6f5943ed2b4e7f44a60f47af00ead6a0ac2e0cbd`.
Output `P0_ORIGINAL_BALL_PRELUDE_CALLEE_INSTRUCTION_CENSUS_V2`
established:

- The original native BL target at Ball+0x2CB0
  is **exactly** six PPC `stw` instructions
  saving r26 through r31 to
  `-24,-20,-16,-12,-8,-4(r11)`,
  followed by ordinary `blr`.
  `exact_original_r26_through_r31_six_store_then_blr_shape_verified=true`
  and `exact_register_r4_preservation_proven=true`.
  The earlier `stw r27..` only failure was
  a false negative from an incomplete decoder.
- The two bounded source instructions **after**
  the return and **before** `Ball+0x2CBC
  mr r28,r4` both qualified
  as non-control, non-r4-writing.
  `r4_preserved_between_return_and_r28_binding_source_verified=true`.
- The **remaining failed gate** is
  `r4_preserved_between_entry_and_helper_call_source_verified=false`.
  It inspected the six instructions at
  the published native cache routine entry
  `0x80299C70` (public Ball+0x2C98)
  through the helper BL at Ball+0x2CB0.
  The previous partial decoder accepted
  relative instruction indices 0,1,2,5
  and conservatively abstained at
  **index 3 = Ball+0x2CA4**
  and **index 4 = Ball+0x2CA8**,
  with **no recognized** r4 writes at
  either. This proves neither that r4
  was modified nor that it was preserved;
  `second_caller_minus_one_can_feed_r28_if_executed_and_path_reached=false`
  was correctly left unpromoted.

**Follow-up in-place source checker improvement:**
`scripts/p0_ball_prelude_callee_census_private.py`
now recognizes the actual Gekko PPC
D-form **`stfd` (opcode 54)** and
paired-single **`psq_st` (opcode 60)**
as floating-point store operations
that do **not** modify any GPR.
It recognizes update variants
`stfdu` (55) and `psq_stu` (61)
only if their **updated base GPR
is not r4**. It preserves
conservative abstention for
unrecognized operations, control
transfers and any known r4
destination. The sanitized
report now provides per-instruction
**primary opcode numbers** and,
where relevant, **base register
indices** for the six-entry
source span, so any remaining
unrecognized original instructions
can be identified without
printing native PPC words or
private binaries.

These added opcode rules are
**not** a claim that original
indices 3 and 4 were `stfd`/
`psq_st`. That is a testable
hypothesis; the source-archive
operator must rerun the corrected
script before `r4` path
preservation can be verified.
Three synthetic tests guard
ordinary floating stores vs
updating `r4`, in addition to
the earlier save-helper and
source-gate regression suite.

If the full entry→helper→postcall→r28
path qualifies and the second
caller still passes `li r4,-1`,
then signed r28 is source-qualified
as negative **if that caller
and linear prologue path execute**.
The **other** branch gate,
the **r13-global object's
`+0x5C` byte being nonzero**,
is still an unknown runtime value,
and neither native wood-vs-foliage
material, selected Ball identity,
impact frame, velocity nor physics
restitution is established.
`training_approved=false`.
No Dolphin, new shots, video,
raw PPC words, original game
assets, private RAM pointers
or coordinates are requested
or committed.


## Source verified negative second-caller backedge operand; global byte owner remains unresolved

Operator reran the original source audit
`P0_ORIGINAL_BALL_PRELUDE_CALLEE_INSTRUCTION_CENSUS_V2`
at pinned SHA `93ba75fdd24d4c60f1ba66a3b25e06c5927e660f`,
original USA Rev1 seven-pair private archive capture **7**.
`original_seven_pair_SHA_and_source_verified=true`.
The previous two unresolved native entry-prologue instructions
at public Ball source `+0x2CA4` and `+0x2CA8`
were confirmed to be PPC primary opcodes **54** and **60**
respectively, both non-updating **floating-point stores**
(`stfd` and Gekko `psq_st`),
each with base GPR `r1`, not r4.

**All original straight-line r4-preservation gates now pass:**
- `Ball+0x2C78`: the second exact direct caller uses
  `li r4,-1` before `Ball+0x2C80` `bl`.
- `original_entry_r4_to_r28_straightline_source_verified=true`:
  the six original instructions at published
  cache-entry `Ball+0x2C98` through
  the BL at +0x2CB0 preserve r4.
  (PPC D-form instructions include stwu
  based on r1, X-form prologue opcode,
  stw, stfd, psq_st and addi.)
- Original helper called at `Ball+0x2CB0`
  is the six `stw` r26..r31 through r11
  then unconditional `blr`;
  `exact_register_r4_preservation_proven=true`.
- The two original instructions after the helper
  and before `Ball+0x2CBC: mr r28,r4`
  preserve r4.
- `second_caller_minus_one_can_feed_r28_if_executed_and_path_reached=true`:
  for that source route r28 receives
  the literal signed **-1**.
  Since the source branch is
  `Ball+0x2FC8: cmpwi r28,0` followed by
  `Ball+0x2FCC: blt Ball+0x2CD0`,
  **the signed r28<0 predicate is satisfied**
  for the second call path if executed.

This is a **static source-level and conditional-path proof**,
not a native guest execution trace.
The other required gate for backedge is still the
**nonzero byte in an unidentified object**:
`Ball+0x2FB8: lwz r3,-23304(r13)`
followed by
`Ball+0x2FBC: lbz r0,+0x5C(r3)`;
then `cmpwi r0,0` / `beq`.
No original runtime capture has established
the meaning or live value of that global object's
byte, and it has not been identified as the selected Ball,
a tree, leaf/trunk material, collision response or
guest physics state.

**Memory/source-only next stage:**
added `scripts/p0_ball_global_5c_source_census_private.py`
plus ten synthetic-only tests
`tests/test_p0_ball_global_5c_source_census_private.py`,
with Windows and Ubuntu CI. It strictly re-gates
all original SHA, seven-capture and 94-tree/native Ball
source checks and the now proven r4→r28 path.
It scans bounded published Golf units
(Ball, Simulation, Player, PlayerManager,
Tree, FieldManager, GolfKCol) for:
- D-form byte reads and writes with numeric
  displacement `+0x5C`, counting nearby
  source sites and their PPC register indices;
- r13-relative global-slot loads and stores with
  original signed displacement `-23304`;
- bounded direct load `lwz rX,-23304(r13)`
  prior to `lbz`/`stb` numeric `+0x5C(rX)`,
  flagging intervening branch or register-writer
  concerns. **A displacement match is only a candidate,
  not a typed receiver link or dynamic source proof.**

The goal is to find the global byte's actual
native writer or prove that its source identity
must be investigated elsewhere, then pivot
back to concrete native Ball↔KCol impact
instructions. Do not derive a wood/foliage
coefficient or an impact flag from this branch.
No Dolphin, new gameplay, video, RAM writes,
PPC code words, private pointer values,
raw game assets or XYZ exported;
`training_approved=false`.
