# P0 original Golf KCL ↔ visual source contrast (diagnostic only)

This procedure investigates the operator-observed ~180° texture/collision disagreement
in the combined original Wii Sports Golf viewer. The current GUI uses an
**unverified uniform bounds fit** with optional 0/90/180/270° display yaw.
This file does **not** assert the actual game-world transform.

## Exact evidence and procedure

Prerequisites, all already source-gated and stored **outside Git**:

- The verified private original RSPE01 Rev1 KCL course OBJ
  (2498 collision triangles) with its original source material labels.
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
  --visual-dae 'D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae' `
  --offline
```

**Important:** ensure `$repo` is checked out at this diagnostic branch (or an
integration commit containing it); the earlier PR #432 does not expose the new
`display_fit_surface_contrast` report until this change is integrated.

Leave off `--offline` to attempt two **read-only**, source-identity-gated
tee/pin memory samples from an already running Felk bridge. Pass
`--require-live` to fail instead of silently accepting missing live evidence.

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
