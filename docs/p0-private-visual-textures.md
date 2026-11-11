# P0 — original Wii Sports Golf visual models and textures (private)

**Status: opt-in UV model preview in inspector; authentic original course asset export and alignment pending.**

The 2,498-triangle original source-selected KCL reconstruction is a **collision candidate**, not the rendered course model. A BE16 course surface type cannot recover the original visual geometry or a texture's UV map. Do not texture KCL triangles with arbitrary UVs and claim it reproduces Wii Sports. The inspector therefore keeps the existing KCL display and read-only memory sampling separate from a **PRIVATE visual-model preview**.

## Source discovery and extraction boundaries

Evidence from original *Wii Sports* modding references: Rev1 disc assets under `/Stage/RPGolScene/` may contain `*.carc` archives; extracted course models have been reported as `glf_course_*.brres`, map/minimap assets as `glf_map_*.brres`. Exact Hitting-the-Green hole 1 model and texture IDs are **not established** by the memory research yet. In BRRES models, geometric MDL0 + TEX0 images can retain real UV coordinates; full Wii GX/TEV material and lighting behavior is more involved than a single PNG.

Use a legally possessed, locally available RSPE01 Rev1 Wii Sports image. Work only in a non-Git private location such as `D:\Projects\WiiGolfVisualPrivate`. Extraction tools may include Wiimms SZS Tools (`wszst EXTRACT` for the selected `.carc`) and BrawlCrate or BRRES Viewer to export UV-preserving DAE/OBJ and PNG textures. If the export is DAE, a local 3D tool may convert DAE to OBJ+MTL+PNG without dropping UVs; export exactly the *visual* course model, not KCL. Do not upload original disc images, texture PNGs, BRRES, OBJ or MTL to GitHub, ChatGPT, or the public repository. The archive-to-hole alignment and coordinate system must be independently confirmed before combining with ball/tee/flag measurements.

Useful reference: Wii Sports `.carc` Golf course notes (The Cutting Room Floor), original Golf modding discussions at wii-homebrew.com, and BRRES model/texture exporter documentation (BrawlCrate, BRRESViewer). Do not assume Wii Sports Resort asset layouts apply to original Wii Sports Rev1.

## Local visual model format (not the private collision OBJ)

The inspector's new **Preview PRIVATE original visual textures** button accepts a user-exported **UV OBJ** and its explicit local material PNGs. Example layout (names illustrative only):

```text
D:\Projects\WiiGolfVisualPrivate\hole01\
    course_visual.obj
    course_visual.mtl
    grass.png
    sand.png
    ...
```

Example minimal OBJ/MTL syntax (synthetic, NOT from the game):

```text
# course_visual.obj
mtllib course_visual.mtl
v 0 0 0
v 20 0 0
v 0 0 20
vt 0 0
vt 1 0
vt 0 1
usemtl synthetic_grass
f 1/1 2/2 3/3

# course_visual.mtl
newmtl synthetic_grass
map_Kd synthetic_grass.png
```

The model loader requires triangle or quad vertex/texture indices, real UVs, a local `.mtl` mapping every used face material to a `.png`, and safe relative texture paths. No URLs, parent traversal, external material libraries or symlinks. Bounds: OBJ 24 MiB, MTL 2 MiB, at most 24 PNGs / 48 MiB total, max 4,096 pixels per texture side and 8.4 million pixels per texture, 100,000 input visual triangles. Local texture decoder checks SHA before rendering. Models must reside **outside Git checkouts**. The game-derived bytes are never embedded in code or copied to GitHub.

Install optional local display dependencies (the normal memory inspector still has none):

```powershell
cd 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
py -m pip install -e '.[visual]'
```

Open the normal memory inspector and select **Preview PRIVATE original visual textures**. Choose the local visual **OBJ**, not the collision mesh. A second inspector window displays the source UV textures. Wheel zoom (at pointer), middle-pan, left/right orbit and F-frame are available. The preview renderer is limited to 4,000 triangles per redraw, 1,280×800 pixel maximum, and uses an approximate depth buffer. It runs only for visual preview gestures, **not at the ~230ms read-only Felk sampling cadence**. Unrecognized vertex shader effects, multipass textures, shadows and Wii GX lighting are not recreated.

The preview remains a separate window rather than automatically overlaying the live ball/tee/flag: matching model/world axes, transforms, hole, native scale and coordinate frame to KCL is a separate required source-validation step. Once original course model and UV export are verified, integrate it into the main scene with explicit model transform and preserve per-object source identity; no fabricated trees. The inspector does **not** present the preview as verified game frame, contact physics or training input.

## Acceptance gates for full game-like 3D course

- Export original Rev1 current-hole **render model**, with UVs and diffuse textures, independently verified; SHA and asset identities remain private.
- Verify GLF course model and KCL coordinate axes/scale/hole source, using multiple static landmarks (tee, pin and additional ground points), without changing source-measured ball data.
- Add tree visual model assets and source-qualified placements separately from their 94 original location markers (which do not include graphics or hitboxes).
- Compare source model and textures side by side with an actual gameplay screenshot. Clarify which native TEV layers/vertex colors are missing; don't claim pixel-perfect equivalence.
- Before training, validate physics collision mapping and timing separately. `training_approved=false` throughout this visual work.


## Operator-local extraction checkpoint (2026-11-10)

The operator successfully extracted original `glf_course_fc1.carc` into
`D:\Projects\WiiGolfVisualPrivate\unpacked\glf_course_fc1`. Their local
inventory of `G3D\glf_course_fc1.brres` reports one MDL0 course model
(`glf_course_fc1`) and **19 TEX0 texture records**, including grass/fairway,
rough, green, bunker and out-of-bounds candidates. This is evidence that the
visual course assets **exist**, not yet evidence that a UV-bearing OBJ, correct
hole ID, world transform, or playable render has been obtained.

The next **local-only, read-only-source** operation is to expand the existing
BRRES archive into a *new, empty* private directory. One-paste PowerShell:

~~~powershell
$ErrorActionPreference = 'Stop'
$source = 'D:\Projects\WiiGolfVisualPrivate\unpacked\glf_course_fc1\G3D\glf_course_fc1.brres'
$dest = 'D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1'
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing BRRES: $source" }
if (Test-Path -LiteralPath $dest) {
    if (@(Get-ChildItem -LiteralPath $dest -Force).Count) {
        throw "Destination is nonempty; refusing overwrite: $dest"
    }
} else {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
}
& wszst XALL --no-wildcards --ext --ext --DEST $dest $source
if ($LASTEXITCODE -ne 0) { throw "wszst failed ($LASTEXITCODE)" }
Get-ChildItem -LiteralPath $dest -File -Recurse |
    Group-Object Extension | Sort-Object Name |
    Format-Table Name, Count -AutoSize
Get-ChildItem -LiteralPath $dest -File -Recurse |
    Where-Object { $_.Extension -in '.mdl0','.tex0','.png','.dae','.obj' } |
    Select-Object FullName, Length
~~~

`XALL` is the documented abbreviation for `EXTRACT --all`; twice using
`--ext` gives precise BRRES extensions such as `.mdl0`. It **does not
guarantee** an OBJ/DAE with UVs or PNGs ready for this inspector. If the
results contain MDL0/TEX0 but no UV-bearing DAE/OBJ and no PNG, use the
original `.brres` in a local BrawlCrate/compatible visual-model exporter:
export `3DModels(NW4R)/glf_course_fc1` as DAE (preserve UVs/material
associations), and export the TEX0 images as PNG; keep both under
`D:\Projects\WiiGolfVisualPrivate`. A UV-preserving DAE-to-OBJ conversion
with a local Blender/compatible exporter is then needed; verify `v/vt/f`,
one local MTL and real `map_Kd` PNG bindings before opening the preview.

Do not upload any private model, texture, disc image, or KCL object, and do not
substitute synthetic textures or made-up UVs for missing exports. The collision
OBJ stays intact. As of the combined PR #429 head (`97a840b2`), Windows and
Ubuntu offline inspector/texture/solid-terrain CI passed; original game-model
export and game-world alignment remain unverified.

## Verified complete BRRES extraction and next UI operation (2026-11-10)

The operator's extraction inventory confirms one .mdl0 (353,608 bytes), 19 .tex0,
36 .png (including mipmaps), two .scn0, two .bin, and three .txt.
These are already present under D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1.
No DAE/OBJ was present. wszst error #64 simply means the requested output
directory already exists; DO NOT re-extract, delete, or overwrite it.

Next export step (local BrawlCrate GUI): open the ORIGINAL BRRES
D:\Projects\WiiGolfVisualPrivate\unpacked\glf_course_fc1\G3D\glf_course_fc1.brres.
Expand 3DModels(NW4R), right-click model glf_course_fc1, choose Export,
switch file type from MDL0 to Collada (.dae), and save in a new private
folder under D:\Projects\WiiGolfVisualPrivate\visual_converted\.
BrawlCrate supports MDL0 export as DAE, although this must be validated
on the actual course asset for texture coordinates and materials.

Use Blender 4.5 LTS (with native Collada import) to inspect UV maps and
convert DAE to Wavefront OBJ + MTL. Blender 5.0 removed built-in Collada
support (a separately installed compatible extension is needed for 5+).
Use the existing base-level TEX0 PNGs (without .mmN mip suffix) for
diffuse materials, and verify resulting MTL map_Kd references and OBJ vt/f
UV indices before loading in the inspector. Keep all game data private.

Visual model/world collision alignment, native shader effects, and correct
hole identity are still pending verification. training_approved=false.


## Original FC1 source DAE: direct textured preview, no Blender

The operator already exported original glf_course_fc1.dae via BrawlCrate
and real PNGs via Wiimms XALL. Collada XML contains 12 source geometries,
13 TEXCOORD references, 12 materials, 11 original diffuse texture slots.
Direct import from a fresh PRIVATE folder uses:

    D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae
    D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\Textures(NW4R)\*.tex0.png

**NO BLENDER required.** Optional inspector direct Collada importer
follows original DAE mesh POSITION and TEXCOORD input indexes, material
effect and image references, then reads the existing matching TEX0 PNG
bytes in place. M_Kiwa_Black receives only its original DAE diffuse Kd
when untextured. It does not synthesize UVs/PNGs or edit the files.

glf_tokosenFix.tex0.png has a documented palette conversion failure,
but none of the actual 11 DAE diffuse texture slots references it, so
that image is NOT necessary for a first course material preview.

Preview PRIVATE game textures file picker now accepts .dae and .obj.
Or open both the current KCL terrain and separate visual DAE via:

    py -3 -I "D:\Projects\Wii Golf AI\Wii-AI-Golf-Texture-UI-P0\scripts\p0_memory_inspector.py" --terrain-obj "D:\Projects\hole01-collision-candidate-PRIVATE.obj" --terrain-labels "D:\Projects\hole01-collision-candidate-labels-PRIVATE.json" --visual-dae "D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae"

Pillow+NumPy (small optional renderer libraries) are the only image
dependencies, not a full Blender installation. The original collision
OBJ and material labels stay SHA-bound and unchanged.

Limitations: source Collada mesh-local positions are not independently
verified aligned to native scene transforms/KCL/ball/tee/flag. Skinning,
multi-TEV GPU shader passes, shadows, model and hole ownership and
training/physics remain unverified. This is a separate static source art
preview, not an in-game native graphics replacement.


## Operator visual quality/performance issue and full-source fix

An authentic first-window screenshot of glf_course_fc1.dae showed:
- 11,995 renderable source UV triangles and 11 PNG-bound textures.
- 780 original source triangles omitted because untextured DAE effect
  lacked any source-authentic diffuse color. This remains explicitly
  omitted, not replaced by guessed art.
- A severe checkerboard/speckled course with large uncovered areas.
- GUI orbit/zoom felt very laggy.

Root-cause confirmed in CPU raster code: MAX_PREVIEW_FACES was only
4,000, and the viewer drew every third source face via stride sampling
of the 11,995 native triangle mesh; a triangle soup with 2/3 faces
missing will never form continuous grass/fairway/green surfaces.
Also, the costly per-triangle Pillow/NumPy raster ran synchronously on
the Tk event loop.

Fix on #429:
- MAX_PREVIEW_FACES now equals the bounded 100,000 source-loader face
  budget. No silent triangle stride; if source exceeds chosen maximum,
  fail closed rather than falsely calling a sparse scene the full model.
- NumPy array camera projection is vectorized and PNG samples are
  evaluated only at pixels inside a depth-visible triangle, including
  a fast no-blend path for opaque source texels.
- One cancellable ThreadPoolExecutor worker renders source PNG+UV in the
  background, coalescing mouse move requests. The worker never accesses
  Tk; all PhotoImage/canvas writes run on Tk main thread. Closing
  invalidates the worker and stops future UI callbacks.
- Status identifies source triangle count and drawn faces, not an
  invented pixel-identical Wii render. Original 780 unknown material
  faces still explicitly omitted.
- Synthetic CI exercises full quad coverage, no silent >4000-face
  stride, cancellable camera view, stale-frame suppression, 100k
  preview cap, and the entire existing terrain/label/startup suite.

Do NOT rerun Blender install, change original assets, or commit game
textures. Reopen same existing private DAE via --visual-dae in updated
PR #429 worktree. Remaining perspective/model transformations,
Wii GX multi-pass TEV, palette material and original active-hole
identity/world-to-collision alignment are NOT yet proven.


## Integrated DAE inspector tab and fixed-position scene editor camera

The source original DAE texture viewer is now an INTEGRATED tab in the
main P0 inspector, not a second floating Toplevel window. The 2,498-face
SHA-qualified source KCL colored terrain, ball/tee/flag candidate
indicators and original sample controls remain in the independent
Collision / KCL candidates tab. No unproven native world/axis/scale
mapping is applied between these two views.

With the private collision OBJ already selected at the operator's
D:\Projects level, the inspector checks the exact sibling candidate
D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae
and loads the UV/PNG model automatically into the visual tab on startup.
A DAE supplied explicitly with --visual-dae has priority over that
candidate. The archive/model naming does not establish active-hole
identity; this is a source-model inspection convenience, not gameplay
physics. Users can still load a different local model via the visual
selection button, with no game asset changes or network scans.

Source-local visual camera controls (Unity Scene view behavior):
- RIGHT click + drag: free-look from exactly the same camera world
  position; no projected-bounds recentering and no orbiting.
- LEFT drag: orbit the source-local focus point (moves camera position).
- MIDDLE drag: pan camera and focus together.
- Wheel: dolly camera forward/back relative to gaze.
- Hold RIGHT mouse + W/A/S/D: fly forward/left/back/right.
- Hold RIGHT mouse + Q/E: fly vertically; hold Shift to speed up.
- F / Frame button: reset scene camera to initial fit.

The perspective visual projection uses source UVs with
reciprocal-depth-correct interpolation. Existing orthographic CPU preview
API remains for old synthetic tests. Camera rendering still takes place
on a single cancellable background thread (no Tk main thread blocking).
The 780 original untextured source faces with unknown appearance remain
explicitly omitted, not synthetically recolored. Wii GX/TEV and
scene/world alignment remain unproven.

Operator launch without separately specifying --visual-dae:

    py -3 -I "D:\Projects\Wii Golf AI\Wii-AI-Golf-Texture-UI-P0\scripts\p0_memory_inspector.py" --terrain-obj "D:\Projects\hole01-collision-candidate-PRIVATE.obj" --terrain-labels "D:\Projects\hole01-collision-candidate-labels-PRIVATE.json"

Windows and Ubuntu synthetic CI verifies fixed-position right look,
scene-camera math, distinct orbit/pan/dolly, source-perspective render,
new DAE integrated panel, original KCL source labels, and full offline
regression. Real Windows layout/navigation still needs operator screenshot.
