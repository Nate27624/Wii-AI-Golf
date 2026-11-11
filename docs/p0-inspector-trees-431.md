# Issue #431 — private original Golf trees in the inspector

## Available now (visual layer only)

The existing 3D source-coordinate inspector accepts the **original Rev1 94-tree**
private position artifact, **not** arbitrary JSON or inferred tree locations:

`D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\derived\golf-tree-positions-source-94-PRIVATE.json`

Launch the normal inspector from this branch (for example
`py -I scripts/p0_memory_inspector.py`), open a source-qualified offline
replay or connect read-only to an already running supported scene, and load
your local 2,498-face source-coordinate terrain OBJ as before. In the middle
3D pane select **Load PRIVATE 94 trees** and choose the JSON on D:.
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
