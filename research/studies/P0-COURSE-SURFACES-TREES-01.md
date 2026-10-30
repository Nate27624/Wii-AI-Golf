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
