# P0 original Golf KCL ↔ visual source contrast (diagnostic only)

This procedure investigates the operator-observed ~180° texture/collision disagreement
in the combined original Wii Sports Golf viewer. The current GUI uses an
**unverified uniform bounds fit** with optional 0/90/180/270° display yaw.
This file does **not** assert the actual game-world transform.

## Exact evidence and procedure

Prerequisites, all already source-gated and stored **outside Git**:

- The verified private original RSPE01 Rev1 KCL course OBJ
  (2498 collision triangles) **and its SHA-bound PRIVATE face-label JSON**.
  The OBJ may carry source OGWS groups itself, but the operator's exported
  candidate uses a separate labels sidecar: it must be loaded explicitly.
- The exported original `glf_course_fc1.dae` plus its private TEX0 PNGs.
  The DAE reader already applies supported authored Collada scene node matrices.
- Optional 94-source-tree JSON and optional running source-gated Felk bridge.
  These two inputs are *not* required for the offline surface contrast.

From a checkout containing this change, run the following on your own Windows
machine; the script reads source assets without writing or uploading them:

```powershell
$repo = 'D:\Projects\Wii-Golf-Tree-PR432'
py -3 -I "$repo\scripts\p0_inspect_course_alignment_private.py" `
  --terrain-obj 'D:\Projects\hole01-collision-candidate-PRIVATE.obj' `
  --terrain-labels 'D:\Projects\hole01-collision-candidate-labels-PRIVATE.json' `
  --visual-dae 'D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae' `
  --offline
```

**Important:** ensure `$repo` is checked out at this diagnostic branch (or an
integration commit containing it); the earlier PR #432 does not expose the new
`display_fit_surface_contrast` report until this change is integrated.

Leave off `--offline` to attempt two **read-only**, source-identity-gated
tee/pin memory samples from an already running Felk bridge. Pass
`--require-live` to fail instead of silently accepting missing live evidence.

## Original DAE rejection: safe source inventory (2026-11-10)

An actual operator run of the combined source audit stopped with:

```text
ABSTAIN_SOURCE_ASSETS: VisualAssetError Unsupported original scene graph transform/controller
```

This is **not** a KCL label or 180° camera-control error. The original
BrawlCrate Collada DAE contains at least one active node child in the
loader's unsupported set: `instance_controller`, `instance_node`,
`lookat`, or `skew`. **We have not yet identified which**, because the
prior loader collapsed them into one diagnostic.

A newer read-only `--scene-only` mode identifies each source construct,
reporting bounded counts only. It does not touch the KCL OBJ, textures,
private models, bridge, selected player, or game. Run:

```powershell
$repo = 'D:\Projects\Wii-Golf-Alignment-PR434'
py -3 -I "$repo\scripts\p0_inspect_course_alignment_private.py" `
    --visual-dae 'D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae' `
    --scene-only
```

If the normal combined scan is retried, the loader will now output a
structured `ABSTAIN_SOURCE_VISUAL_MODEL` JSON with a
`dae_visual_scene.active_unsupported_construct_counts` breakdown
instead of a generic exception message. The script still exits nonzero:
until all required original source scene references/transforms are
handled correctly, scoring visual-vs-KCL geometry would be misleading.
Do **not** disable the source graph check or infer a 180° native transform
from the result. Share only the printed JSON.

The next revision of the source inventory additionally reports
`dae_visual_scene.controllers.active_controller_kind_counts` and one
privacy-safe structural summary per active controller instance. It records
whether each controller is a `skin` or `morph`, whether its source mesh
actually exists, the original bind-shape matrix's identity/nonidentity
status, available joint/inverse-bind matrix counts, weighted vertex counts,
and maximum influences per vertex. It **does not** print controller names,
skeleton IDs, bones, positions, image data, or native matrices.

For the reported 12 `instance_controller` entries, this is the necessary
source-only gate before implementing static bind-pose reconstruction: even a
single-joint skin can position geometry incorrectly if its actual bind
matrix, source joint pose, and blend weights are skipped. No controller
geometry is currently rendered, and alignment scoring remains blocked.
Once the new inventory identifies the actual controller types and
structural completeness, implement the supported controller semantics
using those source fields and regression-test them against independent
native Wii screenshots. Do not relabel these instances as raw geometry.

The Python `SyntaxWarning` about `D:\\Projects` in an old module
docstring is not related to this scene-graph rejection and does not
indicate corruption of the private OBJ.


## Strict static single-joint Collada skin support

The operator's original DAE controller-only audit establishes **12 resolved
`skin` instances**, each with exactly one joint, exactly one influence per
vertex, an identity bind-shape matrix, and a source-bound inverse-bind matrix.
There are **zero direct geometry instances**, so the raw library mesh is not
an adequate substitute for authored controller rendering.

The inspector now supports *only* this constrained static skin class:

1. `instance_controller` must refer to a unique source `skin` and an
   existing original `library_geometries` mesh.
2. `skeleton` must reference a unique node in the **active** source scene.
   The single joint must resolve exactly by SID (or unique exact ID when the
   exporter uses an ID within a Name array).
3. The original `JOINT` and `INV_BIND_MATRIX` arrays, source accessors,
   original POSITION count, and `vertex_weights` indices must agree; each
   original POSITION must have **one positive joint weight** with index 0.
4. The actual source matrix is evaluated as
   `joint_world @ inverse_bind @ bind_shape`, following the Collada static
   skinning equation, without inventing a 180° transform.
5. Multifluence/skeletal animation, morphing, external references,
   missing/ambiguous joint identities, zero/invalid weights and unsupported
   source matrices **remain rejected**.

This is original *DAE scene* reconstruction only: the separate native game
world and KCL alignment are still **unverified**. All private source geometry,
textures and memory stay local and unchanged.

When checked out at the implementation commit, rerun the existing combined
local audit (from a PowerShell prompt, without launching Dolphin):

```powershell
$repo = 'D:\Projects\Wii-Golf-Alignment-PR434'
py -3 -I "$repo\scripts\p0_inspect_course_alignment_private.py" `
    --terrain-obj 'D:\Projects\hole01-collision-candidate-PRIVATE.obj' `
    --terrain-labels 'D:\Projects\hole01-collision-candidate-labels-PRIVATE.json' `
    --visual-dae 'D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae' `
    --offline
```

On accepted source skins, examine the coarse
`geometry.display_fit_surface_contrast.trial_displays` values and source
category counts. On failure, provide the safe
`ABSTAIN_SOURCE_VISUAL_MODEL` JSON, including `skin_source_gate`. That
field identifies an exact **validation category** without printing bone
names, source coordinates, original matrices or proprietary assets. A
successful geometry audit alone never authorizes collision-physics training.

## Interpreting `geometry.display_fit_surface_contrast`

The report tests 0°, 90°, 180°, and 270° using exactly the same uniform
display-only source mapping as the shared KCL/DAE viewer. Each trial gives:

- `surface_centroid_residual_xz`: per-material source centroid mismatch;
  materials are reported only by class: green, fairway and bunker.
- `surface_centroid_rms_xz`: root-mean-square XZ mismatch across available
  classes in **visual-model units** (not a claimed game-world unit).
- `surface_centroid_rms_over_visual_diagonal`: dimensionless mismatch
  normalized by the original DAE playable-area XZ diagonal.
- `uniform_display_scale`: the viewer's own bounding-box display fit.

Without recognized source face materials, the audit returns
`ABSTAIN_KCL_SOURCE_MATERIALS` rather than inventing a surface comparison.
The SHA-bound label loader also rejects a label file from the wrong OBJ.

A low score for 180° is *consistent with* a 180° **display** hypothesis. It is
not a verified native rotation or a reason to change game coordinates. These
centroids represent entire differently tessellated material regions. They are
not identical physical landmarks; an individual course piece, wrong hole,
different surface extent, and a transform/scale error can also change scores.

When fewer than two material classes are present on both sides or playable
geometry is degenerate, the report explicitly **ABSTAINS**. A report with just
two classes is especially weak and must not be used for an automatic fit.
No rotation is ever auto-selected or applied, original private source vertices
are unmodified, and `training_approved=false` remains in force.

## To actually verify native alignment

1. Confirm **source active-hole identity** of both KCL and exported FC1 DAE.
2. Independently validate at least three non-collinear exact native landmarks
   (tee/pin plus a separate located terrain/visual point) in both coordinate
   systems. Region centroids are insufficient.
3. Derive the original scene/world-to-model matrix from native source code or
   source-verified object transforms, including axis handedness and scale.
4. Validate against independent original gameplay screenshots before replacing
   the viewer's unverified bounds fit. Do not use illustrative tree canopies
   as evidence for physics.

The audit intentionally prints only source hashes, counts and derived scalar
residuals, not private source XYZ coordinates, native asset geometry, pointers,
or textures.
