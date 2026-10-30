# P0: Wii Sports Golf terrain material IDs and tree placements

## Evidence and scope (2026-10-30)

**User request:** include trees, green, fairway/grass, rough, sand, water in
existing source-coordinate 3D inspector. **Current main only has ball, pin, tee,
aim/A; draft #407 draws undifferentiated collision wireframe.** This work does
NOT change active S002 UI, existing KCL probe #403/#406/#409, game RAM, or
training. New independent offline code and tests only. No private RAM committed.

## Concrete ORIGINAL Wii Sports, not generic KCL, surface flags

Source: `kiwi515/Resort2OG/src/core/RPGame/RPGolFieldManager.h`
[`EOgwsKclFlag`](https://github.com/kiwi515/Resort2OG/blob/master/src/core/RPGame/RPGolFieldManager.h).
`KCol.h` documents the BE u16 prism flags at offset `+0x0E`
within each `0x10`-byte prism record.

| OGWS raw flag | Category | Proposed UI treatment |
| --- | --- | --- |
| 0x0000 | none | neutral/unknown |
| 0x0001 | fairway | fairway tint |
| 0x0002 | rough | rough tint |
| 0x0003 | bunker | sand tint |
| 0x0004 | out of bounds | OOB warning |
| 0x0005 | camera lock | non-surface overlay |
| 0x0006 | green | putting green tint |
| 0x0007 | water | water tint |
| 0x0009 | fringe | fringe tint |
| 0x000A | pole | keep distinct |
| 0x000B | cup | keep distinct |
| 0x000C | cliff | rocky/cliff tint |
| 0x000D | camera lock noncollision | non-surface overlay |

Do NOT apply Mario Kart or Wii Sports Resort flags. Resort mappings differ,
e.g. `KCL_WS2_GREEN = 0x0106` vs **OGWS** `0x0006`, and are converted explicitly in
[`Resort2OG/src/core/KCol.cpp`](https://github.com/kiwi515/Resort2OG/blob/master/src/core/KCol.cpp).
The original **real** phase7 2,498 triangles are geometrically reconstructed,
but their raw attribute distribution has NOT yet been measured in this branch.
Unknown flags must remain UNKNOWN, never be assigned green/rough by appearance.

## Source-backed trees

Original `RPGolFieldManager`:
[`ogws_info/RPGolFieldManager.h`](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolFieldManager.h):
`field+0x1C` tree object count;
`field+0x20` pointer to `RPGolMapObjTree` array;
`field+0x24/+0x28` water-reflection tree count/array;
`field+0x18` pointer to `RPUtlMapData` with PMP placement data;
`field+0x78` minimap trees render object.

OGWS PMP object IDs, source `Resort2OG/src/core/RPGame/RPGolFieldManager.h`:
`0x00010002` tree variant 1, `0x00010003` tree variant 2,
`0x00010004` and `0x00010005` reflection variants.
`RPUtlMapObject.h` specifies each raw placement record as `0x58` bytes,
with full ID at `+0x00`, VEC3 position `+0x08`, VEC3 scale `+0x14`,
rotation 3x3 `+0x20`, and params `+0x48`. Source code:
[`RPUtlMapObject.h`](https://github.com/kiwi515/Resort2OG/blob/master/src/core/RPUtility/RPUtlMapObject.h).

**Important limit:** The field manager's *in-memory unpacked* `RPUtlMapData`
may not retain the converter's file-style pointer layout on every live state.
First inventory checks only bounded source field count, array pointer, and
the optional PMP magic+object-array-pointer gate before claiming placements.
Even passing this is candidate-only until cross-checked with actual tree
models/screenshots. The actual textured 3D tree meshes are separate reusable
assets, not represented by course KCL triangles or PMP transforms alone.
A first UI overlay could depict validated tree locations/scale with simple
non-physical proxy shapes, labeled experimental; **do not equate proxies with
original game models or obstacle hitboxes**.

## Command and output

In an original source-qualified repository branch/worktree that contains this
study, from the repository root:

```powershell
$archive = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE'
py -3 -I scripts/p0_kcl_surface_tree_inventory_private.py --archive "$archive" --capture 7
```

Uses preexisting `seven._check_archive`, `seven._get` (full archive
SHA256/source selected scene/tee/pin) and read-only mmap; rechecks originals.
Returns only material flag frequencies and source-type tree count, never
paths, pointers, coordinates or a raw file. If the strict original private
archive is not accessible the script **ABSTAINS**, not fabricate a map.
If a single file-style KCL candidate isn't unique and fully valid **ABSTAINS**.
No local Dolphin/controller, no guest writes, no new capture required.

## UI handoff (to S002 / #407 and terrain extractor #403–#409)

1. Add per-prism **raw attribute ID** to private KCL-derived mesh export, e.g.
   one `g OGWS_GREEN`/OBJ face group, or separate local CSV/JSON triangle
   attribute sidecar SHA-bound to the parent private mesh. **Preserve exact
   triangle order and original 16-bit values**, and never insert invalid/
   resampled geometry without a mapping.
2. S002 UI color by **documented original OGWS IDs only**; unknown material
   gets neutral grey and its exact raw ID retained in private diagnostics.
   Legend must distinguish green/rough/fairway/fringe/bunker/water/OOB.
   Do not color purely from proximity to flag or inferred terrain slope.
3. Independently confirm local tree records, grouped variants, transforms,
   reflection objects, and source epoch against the selected field manager.
   Then draw validated tree placements; for game-accurate tree geometry, load
   separately authorized/validated private BRRES assets and preserve scale/
   rotation. A simple placeholder must be clearly labeled non-physical.
4. Show opt-in editable visibility for collision wireframe, types, trees.
   Keep live ball/tee/pin/aim/A and right-click orbit intact.
5. Require tests on original private capture and operator visual smoke test
   before claiming visual alignment or actual course physics.

**Training approved: false.** Source collision flags and tree IDs are
documented, but no original user material histogram or tree placement counts
were obtained in this agent environment.

## Real original phase-7 evidence (operator, 2026-10-30)

The operator executed the original read-only research PR #411 and reported:
`status=CANDIDATE_SURFACE_FLAGS_COUNTED`, all 2,498 KCL records valid, MEM2,
exact OGWS types `fairway=208 rough=585 bunker=301 OOB=508 camera_lock=44
green=478 water=7 fringe=99 cliff=268` (zero unknown). The source
`field+0x1C` tree count was **94**, with a MEM2-valid `field+0x20` tree
array. PMP direct object positions did *not* validate. **This is not evidence
of zero trees** and does not establish tree model meshes, 3D hitboxes,
collision octree reachability or shaded visual-terrain ownership.

## Next read-only source tree-array layout falsifier

New `scripts/p0_tree_array_layout_private.py` studies ONLY the source-owned
`field+0x20` potential contiguous native tree object array from that same
original archived phase7. It ranks possible aligned object strides using
repeatable plausible vtable pointers and finite distinct candidate `+0x30`
translation vectors. The source class annotates `+0x30` as translation, but
its alleged `+0x3C/+0x40/+0x44` fields **overlap**, so the script makes NO
claims about scale, rotation or any other offsets. It never exports tree XYZ
or dynamic pointers. A positive stride is only a structure hypothesis; it
does not verify 3D tree positions.

Example from the *current independent branch's existing detached worktree*:
```powershell
py -3 -I scripts/p0_tree_array_layout_private.py --archive 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE' --capture 7
```
No new Dolphin, gameplay action or RAM capture. If no class/object layout can
be distinguished the script returns `TREE_LAYOUT_UNRESOLVED` rather than
claiming trees are mapped. Models remain separate from the stored collision
mesh. Trainable labels remain disabled.

## Real phase-7 contiguous tree-array falsification

Operator ran the prior `p0_tree_array_layout_private.py` against original
SHA/source-gated capture 7, yielding `TREE_LAYOUT_UNRESOLVED` for count **94**.
The highest-ranked strides (104,112,160 bytes) had only 15/26/24 structurally
plausible records, with common-vtable matches 2/1/1. This **rejects those
specific contiguous-object-vtable assumptions**, not the source field count.

### Pointer-table hypothesis

New, separately scoped `scripts/p0_tree_pointer_table_private.py` tests
whether `field+0x20` instead points to a table of per-tree object **pointers**.
It probes bounded 4..48-byte pointer-table strides and aligned pointer offsets,
then independently validates each non-null unique MEM2 object pointer,
at least one plausible MEM1 virtual function reference, and finite candidate
`obj+0x30` translations. A mixture of two tree variants is allowed through
a top-two-vtable test. These are structural gates ONLY and may fail for
correct native layouts; failing does not contradict 94 source field tree objects.

No object XYZ, vtables, private address, hashes, geometry, or files are emitted.
The script does not claim tree hitboxes or model meshes. To run in the existing
detached user research worktree after fetching this PR branch:

```powershell
py -3 -I scripts/p0_tree_pointer_table_private.py --archive 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE' --captures 7
```

If `POINTER_TABLE_STRUCTURAL_CANDIDATE` and *one* layout qualifies, the
next independent step is compare the private 94 source-component translations
to the terrain bbox and record topology, plus inspect constructor/array writer
PPC. If unresolved, investigate native allocation/pointer buffer layout
directly from source disassembly. No training promotion.

## Real operator pointer-table falsification and direct PPC follow-up

Operator ran `p0_tree_pointer_table_private.py --captures 7` against the
original SHA- and source-gated private RAM cohort. Result was
`POINTER_TABLE_UNRESOLVED`. For the four top hypotheses (12/24/48-byte
entries slot+4, and 12-byte slot+8), the current probe's aggregate
structural diagnostics reported only 27/27/26/24 unique MEM2 candidate
object pointers, **zero objects with its strictly expected MEM1 vtables**
and therefore zero accepted position vectors. This shows neither
hypothesized pointer-table encoding is source-proven. It does NOT disprove
the independently reported `FieldManager+0x1C=94` trees. It may be a
contiguous tree object array with a different stride, pointer indirection,
header/element offset, or incompatible vtable/linkage assumptions.

Instead of further broad stride guessing, the next probe is
`scripts/p0_tree_ppc_indexing_private.py` in PR #411. It examines only
the Rev1 **original source .text** bounded by public ogws splits and
symbol labels:
- `RPGolFieldManager` `0x80290B44..0x80294184` split into windows
  near named **`PmpProc2` (0x802917D4)**,
  **`Golf::PmpProc` (0x80291F34)** and
  **`Golf::LoadCurrentHoleResources` (0x80293008)**;
- `RPGolMapObjTree` `0x80296238..0x80296EA8`;
- `RPGolMapObjTreeWater` `0x80296EA8..0x80296F50`;
- `RPGolMapObjBase` `0x8028F9FC..0x80290B44`.

The parser decodes only selected static PPC `mulli`, `mullw`,
`slwi`, field-related D-form `lwz/stw/lfs/stfs` and direct `b/bl`
to tree/base code. It returns public unit-relative offsets and
immediate multiplicands/counts **without** original native words,
heap pointers or private coordinates. The presence of, for example,
an immediate size `0x80` alone is NOT proof of `sizeof(Tree)`; the
next stage must check register dataflow from the field tree-count and
array pointer through the allocation/callsite instructions.
No runtime gameplay execution is proven by static code scans.

Use same original phase7 archive, no Dolphin or new capture:
```powershell
py -3 -I scripts/p0_tree_ppc_indexing_private.py --archive 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE' --capture 7
```
See [ogws public source splits](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt)
and [Wii Sports public Rev1 symbol map](https://github.com/kiwi515/ogws_info/blob/main/RSPE_r1.map.csv).
