# Issue #431 — private original Golf trees in the inspector

## Available now (visual layer only)

The existing 3D source-coordinate inspector accepts the **original Rev1 94-tree**
private position artifact, **not** arbitrary JSON or inferred tree locations:

`D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\derived\golf-tree-positions-source-94-PRIVATE.json`

Launch the normal inspector from this branch (for example
`py -I scripts/p0_memory_inspector.py`), open a source-qualified offline
replay or connect read-only to an already running supported scene. **Tree
positions and the previously selected terrain OBJ now load automatically
on every launch** when their local files remain valid. There is no need to
browse for the same files each time.

On first use the inspector tries the expected exact PRIVATE tree JSON in
known local `Wii-AI-Golf-Data/derived` locations (including the sibling
`D:\Projects\Wii-AI-Golf-Data\derived` folder). If none passes all original
safety/source checks, click **Load PRIVATE 94 trees** once, selecting your
validated local file. Select the terrain OBJ once with **Load PRIVATE
terrain OBJ**. Subsequent runs restore the two last successful selections,
validated from disk afresh. **Clear terrain** forgets its saved path; **Clear
trees** forgets the JSON and disables automatic rediscovery until another
manual selection. Invalid/missing files are reported without silently
substituting unrelated geometry.

### Regenerating the missing PRIVATE JSON from original capture

The coordinates were generated in source-research **draft PR #411** by
`scripts/p0_tree_position_export_private.py`, not committed to Git.
The original verified archive was recorded as
`D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\p0-new-cohort-20261028-063011392-955fd483-PRIVATE`.
If your inspector clone lacks the JSON, run the **bootstrap from PR #432**:

```powershell
& powershell -NoProfile -ExecutionPolicy Bypass -File "D:\Projects\Wii-Golf-Tree-PR432\scripts\bootstrap_inspector_private_trees.ps1"
```

The bootstrap checks the original archive, fetches **PR #411** into a
separate clean detached worktree nested under `D:\Projects\Wii Golf AI`
(so its original source gating resolves the correct sibling Data root),
invokes the SHA/scene/PPC/94-object-gated exporter once, validates the exact
JSON via the inspector loader, and persists its location to local user
settings. It will **not overwrite** an existing private JSON, copy native
banks to Git, edit ROM/Dolphin, fabricate positions, or claim hitboxes.
It prints an explicit error if the original capture is missing: a Git
checkout alone cannot recover original coordinates that were intentionally
never committed. Previously selecting **Clear trees** will not prevent
this bootstrap from re-enabling the validated saved path.

If trees do not load automatically, use the **read-only local diagnostic**:
`py -3 -I scripts/diagnose_inspector_tree_loading.py`.
It reports which known private locations were checked, which file (if any)
was previously saved, whether **Clear trees** disabled auto-discovery, and
the strict loader's rejection reason. The inspector now also shows missing-
file or rejection reasons directly beneath the tree controls instead of
silently skipping the overlay. The diagnostic does **not** print any
original game coordinates or copy source assets. A loaded source JSON does
not render until source-qualified replay/live data is available.

The settings record is **paths only**, never coordinates, textures, or art:
on Windows `%LOCALAPPDATA%\WiiAIGolf\inspector-assets-v1.json`;
on Linux `~/.config/wii-ai-golf/inspector-assets-v1.json` (or the XDG
config directory). It is stored outside the Git repository and uses an
atomic write. Saved paths do not bypass any private asset loader validation.
The strict loader carried forward from PR #420 enforces its exact original
RSPE01 Rev1 source schema, exactly 94 finite distinct locations, 84-byte
source element stride, +0x30 translation, stable captures 1/5/7, the
expected directory/filename, no Git-contained private files or symlinks,
disabled safety flags, bounded file size and a SHA-256 digest.

**Show trees** toggles the layer separately from the terrain.
**Illustrative 3D crowns (NOT game art)** shows 94 small 3D pine-like
stand-ins (4 trunk faces + 8 green crown faces each), always annotated as
*illustrative, nonphysical*. Turn this off for **exact position dots only**;
enable **Tree IDs** for T01–T94 labels. The dots are anchored to exact
private source positions. The placeholder canopy sizes are scaled to the
span of the 94 private points to stay viewable, **not extracted from the
original game**. Camera yaw/pitch, zoom, pan, trajectory, tee, pin, aim,
A indicator, and existing private UV visual-model texture preview remain
separate. Source alignment with the terrain, visible scene and ground
elevation still requires the user's local independent visual check.

The overlay draws only for source-qualified samples and refuses to assume
the source epoch/scene when the capture is unqualified. No source-position
data, ROM art, textures, private OBJ, or screenshots are stored in Git.
The Tk painter uses approximate face ordering, not correct physical
occlusion or a GPU depth buffer. Even when drawn, the trees are **NOT**
collision objects, native hitboxes, physical models or training labels.
`training_approved=false`; `tree_collision_geometry_verified=false`.

## Original game tree mesh/textures — next evidence gate

The separate original-game BRRES/MDL0 export on D: and the
`glf_course_fc1.dae` / PNG texture work provide **course visual assets**,
but do **not** yet establish the source model/type/transform for each
of the 94 tree objects. Do not map `glfM_hayasi3` or other foliage-like
material to trees merely from a name. Do not infer that the 72/22 resource
word groups are two species or collision types. First extract an
enumerated original **Wii Sports Golf RSPE01 Rev1** tree MDL0 resource list,
its textures/alpha setup and the actual per-object model ownership,
scale/rotation and component-frame transforms. Preserve source-to-model
evidence in a private local manifest; add a strictly validated opt-in
viewer path only after the mapping is independently checked against
game screenshots. Private source vertices/UVs/images never enter Git.

## Tests and integration

Run
`py -m unittest discover -s tests -p 'test_p0_memory_inspector_tree_*.py' -v`
and `py -m unittest discover -s tests -v`.
The dedicated tree offline workflow covers Windows and Ubuntu, synthetic
94-element fixtures, exact base markers, bounded placeholder faces and
loader's malicious/path/provenance refusal cases; no Dolphin, original
assets or live operator data are needed for CI.

This feature starts from current `main` to retain merged PR #425
(private textured preview, zoom/pan) and does not modify the draft
PR #419 terrain-solid branch. When merging #419/this PR, preserve the
94-tree projector call and the tree layer behind ball/tee/pin while
integrating terrain material shading. Revisit **shared depth ordering**
only after solid terrain is fully integrated. The existing private
texture-preview window is not itself a native 94-tree model renderer.


## Combined original texture + 2,498-face KCL + 94 source trees (PR #432)

This branch now integrates the latest cohesive **#419 and #429** renderer
into the PR #432 tree-inspector entrypoint. It preserves source-color filled
KCL polygons, the full 2,498-face option, separate SHA-bound surface-label
sidecars, original FC1 Collada DAE/TEX0 PNG source geometry, accelerated
Numba CPU raster where installed, and a single shared Unity-style visual
camera with RMB look, orbit, WASD/arrow movement, and playable-area framing.
The earlier Tk candidate KCL canvas remains a fallback when private visual
assets are absent. Its merged pan, wheel zoom, RMB orbit and F-to-frame
controls are retained independently of the high-performance UV renderer.

When a valid strict source-94 JSON exists, the **94 base markers** and
optional clearly **illustrative, nonphysical** foliage render in:
- the source-qualified 3D KCL fallback canvas; and
- the SAME original UV/KCL visual canvas when a visual DAE and KCL are both
  loaded, in **Collision** or **Both** comparison mode.

The second case deliberately uses the **unverified visual-vs-KCL bounding-box
display-fit**; native source-to-DAE alignment is NOT established. Markers and
crowns are painter-order/x-ray graphics, not actual tree geometry, collisions,
or true visual-model Z-buffer meshes. They are not displayed in
**Textures-only** mode or if KCL has not been loaded to establish a display
fit. Tree toggles and status stay visible below the single integrated source
canvas, even after switching into the DAE visual preview.

The last validated terrain OBJ and tree JSON are retained in the OS-local
path-only preference file; normal startup restores both, and manual
`--terrain-obj` replaces the saved OBJ. Private original tree XYZ, DAE, TEX0
textures, binary banks, KCL OBJ and source-label sidecars are never committed.

To launch with the local optional fast source renderer:

```powershell
cd 'D:\Projects\Wii-Golf-Tree-PR432'
py -3 -m pip install -e '.[visual-fast]'
py -3 -I scripts/p0_memory_inspector.py
```

The private original FC1 DAE is looked up only after a private terrain OBJ
has been supplied or remembered, from the known local
`D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae`
or a matching private location beside the OBJ; it is **not an assertion that
FC1 is the active game hole**. Users may always choose
`Load PRIVATE visual DAE / OBJ` manually instead. Original-game accuracy,
source-to-visual 3D alignment, tree model ownership, and operator screenshot
confirmation remain pending.


## Operator screenshot: visual DAE yaw differs from KCL/trees

The operator's November 11 integrated-source screenshot shows the textured
FC1 course visually pointing opposite the cyan KCL enclosure and 94 tree
markers. The current KCL/DAE comparison is a **bounds-fit visualization**, not
a verified native scene transform. A bounds fit alone does not recover
orientation. It can make two same-sized but oppositely directed geometries
look superimposed.

The original 2,498 source KCL triangles, source XYZ tree JSON, and UV/PNG
visual assets are immutable. The unified preview now defaults to an explicit
**+Y 180° display-only comparison yaw hypothesis**, rotating the KCL and
trees **together** around the visual bounds center (after source scale and
translation). The GUI provides **0°, 90°, 180°, 270°** radio choices so the
operator can compare opposite and perpendicular orientations. The selected
angle appears in the comparison status (including **UNVERIFIED**). Turning
it does not rotate the native visual model, mutate source KCL/tree data,
move the camera, affect Dolphin, or establish an actual game-world mapping.

At 90°/270°, fit scale is recomputed from the appropriately swapped
horizontal extents; neither KCL triangles nor tree bases receive an
independent rotation. Source tree dots and illustrative crown polygons both
call the *same* source-to-display transform as the KCL polygon vertices,
preventing future tree/KCL overlay drift. The active choice lasts within
that inspector window; initial orientation hypothesis is 180° on reopen.

Visual validation against actual course landmarks (distinct tee, flag,
bunkers, and ends of fairway) remains necessary. Matching by eye does not
prove native scene graph transforms or tree hitboxes.
