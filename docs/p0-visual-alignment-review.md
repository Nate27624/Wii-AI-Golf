# Visual alignment review: original FC1 texture vs KCL

The original FC1 Collada DAE includes twelve single-joint controllers. The
strict source loader now resolves the original source meshes with the
source-authored joint world matrices, inverse bind matrices and one
influence per vertex. This is a visual source scene, NOT proof of native
KCL/game-world alignment or collision behavior.

## Windows launch

```powershell
py -3 -I 'D:\Projects\Wii-Golf-Visual-Review\scripts\p0_memory_inspector.py' `
  --terrain-obj 'D:\Projects\hole01-collision-candidate-PRIVATE.obj' `
  --terrain-labels 'D:\Projects\hole01-collision-candidate-labels-PRIVATE.json' `
  --visual-dae 'D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae'
```

The inspector will restore a previously selected private tree source JSON;
if not already saved, choose it in the existing **Load PRIVATE trees** control.

Click **Review top-down** in the unified textured viewport. This sets a
single overhead camera, shows source-original PNG textures under
translucent original OGWS KCL face colors, and turns off illustrative tree
crowns (while preserving the 94 exact tree base markers).

Change mode with **Textures**, **Collision**, **Both** (cyan KCL edges),
**Overlay** (transparent KCL polygons), or **Split** (textures left,
collision right). Every mode uses precisely the same camera.

Choose **0/90/180/270°** display yaw or nudge **Scale +/-** and
**X/Z +/-**. Scale changes 5% per click and translations 1% of the
playable DAE XZ diagonal per click; original source XYZ is not edited.
**Reset display fit** discards manual adjustments and restores the
prior source-derived display candidate. No transformation is saved to
game physics, collision or a private asset.

Compare recognizably distinct green/bunker shapes, fairway edges and
tree bases, then tell the assistant **aligned YES or NO** with an
optional inspector screenshot. A visual match is useful operator
confirmation for the renderer, but is not an independently verified
Wii world coordinate transform. Training remains unapproved.

The tool stays read-only. Source OBJ, private label sidecar, DAE, PNGs,
native memory and control inputs are unchanged.

## Course 2 is the current operator hypothesis (FC2)

The earlier original FC1 DAE was **visually rejected by the operator** as a
different course from shot 1 of *Hitting the Green*. Naming `glf_course_fc2`
as the next candidate is **not an independent game-state linkage**;
the original game's course-selector mapping is still unverified. Do not
rotate/scale FC1 to fit a different hole.

From any checked-out inspector PR #436 commit containing the FC2 catalog:

```powershell
py -3 -I 'D:\Projects\Wii-Golf-Visual-Review-PR436\scripts\p0_memory_inspector.py' `
  --probe-visual-course 2
```

This checks only the established local paths beneath the private
`D:\Projects\WiiGolfVisualPrivate` directory and prints no original art.
There are three possible useful statuses:

- `LOCAL_SOURCE_DAE_CANDIDATE_FOUND`: run the normal inspector command with
  `--visual-course 2` instead of `--visual-dae`.
- `SOURCE_BRRES_PRESENT_EXPORT_DAE_WITH_BRAWLCRATE`: open your own extracted
  `unpacked\glf_course_fc2\G3D\glf_course_fc2.brres` in BrawlCrate; export
  its source MDL0 as `visual_exports\glf_course_fc2\glf_course_fc2.dae`,
  with corresponding original TEX0 PNG textures resolving relative to DAE,
  following the established FC1 workflow. **No guessed textures.**
- `COURSE_NOT_YET_EXTRACTED_OR_EXPORTED`: locate the original
  `glf_course_fc2.carc` on your own Wii Sports Rev1 disc under
  `Stage/RPGolScene`, extract it locally as with FC1, then export the
  BRRES MDL0 and texture images. Do not download or commit proprietary
  assets. An existing unpacked directory with a different BRRES layout
  produces its own `SOURCE_UNPACKED_SEARCH_G3D_AND_EXPORT_DAE` status.

After export, launch:

```powershell
py -3 -I 'D:\Projects\Wii-Golf-Visual-Review-PR436\scripts\p0_memory_inspector.py' `
  --terrain-obj 'D:\Projects\hole01-collision-candidate-PRIVATE.obj' `
  --terrain-labels 'D:\Projects\hole01-collision-candidate-labels-PRIVATE.json' `
  --visual-course 2
```

The same UI includes **Try Course 2 (FC2) — candidate** to switch the visual
model without touching the SHA-bound KCL or 94 source trees. If FC2 is absent,
the earlier preview is retained and a clear missing-export message is
displayed. A failed FC2 strict loader is not silently replaced by FC1.
No correspondence or native world alignment is asserted until the operator
visually confirms the actual correct course.

## Nonconsecutive original FC archive IDs; match native KCL first

The operator's original `D:\Projects\RPGolScene` folder contains the
actual numeric archives FC1, FC3, FC5, FC8, FC9, FC11, FC12, FC13, FC14,
FC16 and FC18, but **not FC2**. The second gameplay/course index must NOT
be construed as `glf_course_fc2`. The current first available new
hypothesis is FC3, **not yet confirmed**. Public Wii Sports research
identifies FC11 as unused in normal golf (associated with Target Practice)
and FC18 as unfinished, but the captured current KCL ↔ on-disc archive
identity must be proven locally from source.

Run the source-only extractor for each actually present numeric original
`*.carc` into a new `WiiGolfVisualPrivate/unpacked/<archive>` folder;
never overwrite a pre-existing extracted folder. The original source KCL
files should be extracted as `*.kcl`. Then run:

```powershell
py -3 -I 'D:\Projects\Wii-Golf-Visual-Review-PR436\scripts\p0_match_course_kcl_archive_private.py' `
  --terrain-obj 'D:\Projects\hole01-collision-candidate-PRIVATE.obj' `
  --unpacked-root 'D:\Projects\WiiGolfVisualPrivate\unpacked'
```

This diagnostic applies the **original** file-layout prism reconstruction
from the existing P0 KCL source audit (PR #403) and compares all reconstructed
triangles against the captured-source private OBJ, order-independently,
using the original OBJ export's nine-significant-digit coordinate format.
Source vertex coordinates and geometry hashes remain only in operator RAM
and are **not** printed. Only original archive labels, prism counts and
match/mismatch categories are reported. A unique exact source KCL match is
strong original **archive-to-collision** evidence, but it is **not** a
proof of active live collision selection or game-world visual transform.
If the match fails or multiple match, abstain and continue to visual review
or game RAM ownership tracing; do NOT guess a course number from file order.

To open the source DAE model once extracted/exported, use
`--visual-course <actual FC archive ID>`, such as `--visual-course 3`.
The inspector's FC archive spinbox also accepts 1-99. The explicit course
probe now detects available original `RPGolScene/glf_course_fcN.carc`
without asserting that it has been unpacked or converted to a DAE.
