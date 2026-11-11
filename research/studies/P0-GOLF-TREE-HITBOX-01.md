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
