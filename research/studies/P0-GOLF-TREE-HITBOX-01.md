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
