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
