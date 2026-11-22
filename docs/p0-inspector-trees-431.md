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


## Source-verified course registration audit (2026-11-11)

Further operator evidence showed that *neither* 0° nor the earlier
180° bounding-box overlay matches the source course. The earlier
display-yaw hypothesis is superseded: a scalar bounds fit and free
yaw cannot prove two source assets share one active game coordinate
frame. There is also a concrete exporter bug: `dae_visual.py` previously
read only `library_geometries/POSITION` arrays and ignored source
`library_visual_scenes` node matrix/rotate/translate/scale records.
These original Collada **authored model transforms are now applied**,
with bounded nested parent/child matrices and multiple source-authored
instances; UV seams and materials retain their native texture bindings.
Unsupported skinned/instance-node/ambiguous graph layouts fail closed
rather than showing incorrectly positioned visual art. This is the
correct source-authored *Collada model frame*, but does **NOT**
establish the game's KCL/MDL0 matrix or native world-to-course mapping.
The earlier guessed 180° comparison default is removed; optional
0/90/180/270 viewer experiments remain and show UNVERIFIED.

For further source registration, run:

```powershell
Set-Location 'D:\Projects\Wii-Golf-Tree-PR432'
py -3 -I scripts/p0_inspect_course_alignment_private.py
```

The local-only **read-only memory probe** uses the existing tested
`fast.packet` source and pointer provenance with two consecutively
independent RSPE01 US Rev1 Golf scene/selected player/tee/pin/epoch gates.
It accepts only `memory.read_u32`, `memory.read_bytes`, and
`frame.get_count` via `ReadOnlyRPC`. Source identity and tee/pin
memory words must agree across non-atomic host frame brackets; otherwise
live memory evidence is declined. The script never launches Dolphin,
presses a button, writes RAM, uploads or commits original vectors.
An unavailable bridge does not cause a guessed fallback.

This audit also checks actual DAE source-authored scene node transforms
and counts, optional up-axis metadata, original private DAE/KCL source
SHA, per-surface green/fairway/bunker triangle counts and centroids,
and with qualified live RAM, native tee/pin versus KCL green/fairway
displacements. `--require-live` returns a nonzero code if the bridge
or source qualification is unavailable; `--offline` audits file
structure without pretending to inspect running memory.

The output **does not automatically change the KCL or tree transform**.
It explicitly labels native world mapping as unverified. Review the
source DAE scene matrix, actual active hole and source-paired tee/pin
versus KCL geometry first; confirm the original visual file is
the **same** native hole as the KCL. Only then may a source-qualified
native world matrix or separately measured correspondence with residual
and independent holdout be applied to collision/tree graphics.


## 2026-11-11 regression: gray-only 94-tree view and slow arrow movement

Operator screenshot showed **blue-gray solid KCL triangles, 94 illustrative
green tree crowns, and AIM?/BALL/TEE/PIN text**. This is conclusive evidence
that the *legacy Tk source-coordinate fallback*, not the original UV/PNG
texture viewport, was on screen. Mipmap tweaks cannot change it.

Root causes addressed in PR #432:
1. The DAE was only auto-discovered when an explicit/saved KCL OBJ path
   was available. The original source visual filename was not saved
   (whereas KCL/tree paths were). A missing/rejected DAE silently left the
   source inspector on the gray fallback, and the error text existed only
   inside the never-packed visual tab. The original known local FC1 path
   is now examined independent of the OBJ, a successfully validated DAE/OBJ
   path is remembered in OS-local settings with legacy format migration,
   and an import rejection is shown prominently **inside the visible
   fallback** with concrete loader exception text.
2. The full hidden Tk fallback was unnecessarily redrawn on every
   read-only LIVE packet even while a real original visual renderer was
   active, adding thousands of terrain/tree painter operations to the UI
   thread. Hidden redraw now returns early. Original KCL/JSON are untouched.
3. Fallback canvas had no held-arrow input bindings. It now supports
   time-based continuous arrow-key pan independent of OS keyboard repeat,
   debounces fake autorepeat key releases, stops on focus loss/visual
   activation and caps expensive Tk redrawing to ~10 Hz. During movement
   it uses a clearly labeled lower-detail preview with tree bases and
   restores all surfaces and illustrative crowns on stop.
4. The original UV 3D renderer previously used full resolution even
   while navigating if Numba was unavailable. Both rendering engines
   now reduce only display *pixel resolution* during drag/held keys,
   defer expensive mip filtering until the camera stops, and always
   preserve all original model triangles/UVs. This improves interactivity
   without changing native game geometry.

A read-only original source asset diagnostic is now available:
```powershell
cd 'D:\Projects\Wii-Golf-Tree-PR432'
py -3 -I scripts/diagnose_inspector_visual_loading.py
```
It reports the exact selected local source filename, importer
validation/error category, source model face count, source-bound PNG
count, omitted unknown original effects and whether optional Numba
acceleration is available. NO original model/texture bytes or source
coordinates are printed. To examine a specific local export, provide
`--visual-dae 'D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae'`.
A missing native source DAE, unsupported Collada node hierarchy,
missing PNG, invalid path outside-Git requirement or absent Pillow
is reported instead of pretending that the KCL fallback is textured.
If the diagnostic succeeds but the viewer still remains gray,
investigate Tk startup exceptions/UI widget state separately.

Open verification: run against the actual private DAE on the operator's
Windows machine, confirm source texture viewport appears and movement
is smooth, then compare filtered art with Dolphin native Wii rendering.
Offline tests cannot prove original visual-model source fidelity.


## 2026-11-11 original FC1 DAE scene-graph import rejection (operator evidence)

Operator screenshot showed this precise red on-screen error:

`TEXTURED MODEL FAILED — fallback collision-only canvas.
VisualAssetError: Unsupported original scene graph transform/controller.`

This error came from the new strict Collada `source_scene_instances()`
rejecting any `lookat`, `skew`, `instance_node` or
`instance_controller`, *before* a single otherwise-valid original PNG
texture/UV mesh could be displayed. The old gray Tk fallback was merely
covering for an original visual model **not imported at all**.

Now resolved conservatively:
- Original `instance_node` links in source `library_nodes` or
  `library_visual_scenes` are traversed with the actual composed
  hierarchical transforms. Bounded recursion, per-reference instance
  counting, unique source IDs, cycle detection, and same-file-only
  `#id` links prevent silent guessing or external includes.
- Unsupported source `instance_controller` (skeleton/skin), `lookat`,
  and `skew` are named explicitly by the strict importer rather than
  folded into a generic error. External controller links and
  malformed/nonfinite `lookat`/`skew` remain hard rejected.
- For *only those well-formed but unsupported source scene features*,
  the GUI first offers a **PARTIAL ORIGINAL SCENE PREVIEW**, preserving
  valid native-authored transform matrices for supported source geometry
  while omitting unsupported controller/skew/lookat subtrees. If the
  scene has no renderable supported geometry, it instead offers an
  explicitly labeled **GEOMETRY-ONLY ORIGINAL-TEXTURE PREVIEW**. That
  mode reads the same verified original DAE library POSITION/UV/materials
  and local PNGs without applying any visual-scene hierarchy or skinning.
  Neither mode represents native world alignment, and original KCL
  overlays are **not automatically enabled** in either mode.
- The red warning appears INSIDE the now-visible source-texture
  viewport; status labels NEVER claim a native original scene matrix
  or hole registration was applied. Strict `load_private_dae_visual_model`
  calls still fail closed unless a caller explicitly asks for this
  bounded, non-authoritative compatibility display.
- `py -3 -I scripts/diagnose_inspector_visual_loading.py` now returns
  `VISUAL_DAE_PARTIAL_SCENE_PREVIEW` or
  `VISUAL_DAE_GEOMETRY_ONLY_PREVIEW` (instead of a missing-art error)
  and names the unsupported source element(s). The result proves
  only exact local PNG/UV loader success, **not** Wii physics, KCL
  registration, tree hitbox correctness, native animation, or game art
  fidelity.

The original source DAE/PNG/OBJ/JSON remain byte-identical and PRIVATE.
The operator should now see the source texture 3D viewer, rather than
the gray fallback. To reconstruct the actual Wii scene transform and
controllers, inspect source MDL0/BRRES and the specific DAE controller
later, rather than rotating/stretching an incomplete visual model.


## 2026-11-11 confirmed wrong scale of blue KCL/94-tree x-ray

Operator screenshot shows a geometry-only source-DAE texture preview with a
grossly over-scaled cyan KCL overlay. The previous default
`prepare_comparison_kcl()` blindly applied a uniform fit to the original
DAE *playable material bounding box* vs full source KCL bounds. With
an unsupported source `instance_controller`, and a visually very large
original background/course library, that bound is **not a native coordinate
or gameplay scale**. A guessed rotation cannot correct it.

**New behavior:** source-material category evidence gets priority.
Read-only `material_alignment.py` finds exact KCol OGWS green 0x0006,
fairway 0x0001 and an independently reserved original bunker 0x0003
(or rough 0x0002 if bunker unavailable), alongside independently
source-authored Collada material identifiers `M_Green`, `M_Fairway`,
`M_Bunker` (or `M_Rough`). Green/fairway horizontal area-weighted
centroids determine candidate translation/scale/Y-yaw. It independently
requires the transformed **green footprint area ratio** to agree within
bounded tolerance, and **holds out bunker/rough** centroid with error
at most 12% of green-to-fairway span. If any material is absent,
ambiguously grouped or the independent checks fail, the inspector
**automatically chooses Textures mode**, hides cyan KCL/tree x-ray
rather than displaying an obviously wrong-sized one, and prints
`KCL/TREES AUTO-OVERLAY HIDDEN` with reason.

If the source material evidence passes, the resulting *measured, still
display-only* similarity is applied once and **identically** to original
KCL triangles and all 94 exact source tree bases and crown stand-ins.
The viewport status prints the source-derived scale, relative yaw,
independent holdout residual and green footprint ratio. This mapping
does NOT certify native game world axes, collision physics or
botanical models. Original source KCL/DAE/PNG/tree JSON never change.
Nonzero yaw radio choices remain explicitly labeled manual bounds-fit
trials and can never be mistaken for independently measured scale.

The existing original Collada `instance_controller` may contain
real static `<bind_shape_matrix>` scale that was lost in the
geometry-only preview. Source-only
`collada_controller_scale.py` reads original DAE skin controller
bind-shape matrices and reports bounded X/Y/Z basis scale ratios,
controller/scene instance counts, nonidentity and nonuniform
transform indicators, with no raw source vertices or XML text.
**This is evidence for a future native controller implementation,
not a replacement for actual joint skinning, source root matrices
or an authoritative KCL alignment.**

Operator command:

```powershell
cd 'D:\Projects\Wii-Golf-Tree-PR432'
py -3 -I scripts/diagnose_inspector_visual_loading.py
```

The JSON now includes `original_controller_scale_audit` and
`kcl_to_visual_display_fit`. If fit status is
`SOURCE_MATERIAL_DISPLAY_FIT_CANDIDATE`, the live UI may draw a
numerically checked material overlay. If `SOURCE_DISPLAY_REGISTRATION_DECLINED`,
we must inspect source controller data and corresponding original
hole/material regions before trying a native scale, rather than
tuning a magic multiplier.

An independent comparison to the *actual* Dolphin course image is
still required, with test and holdout hole views, before claiming
accurate source registration or real Wii visual fidelity.
