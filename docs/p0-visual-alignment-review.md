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

The operator confirmed FC3 visual/KCL alignment. Rotation, scale,
translation nudges and reset **are no longer shown as UI controls**.
Use the remaining **Top-down view** camera action and the same original
texture/KCL display mode buttons. Native physics/world registration is
still separately unverified.

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


## 2026-11-11: FC3 exact original KCL and quantitative transform investigation

The operator proved that **original glf_course_fc3 KCL** is the UNIQUE
order-independent nine-significant-digit exact 2,498-triangle match among
11 checked on-disc FC archives. The operator exported original FC3 DAE
from BrawlCrate and visually aligned the original texture surface and
source KCL in the unified viewer. Manual visual trial: display-scale
multiplier **2.0789×** the initial bounds fit, offsets **X +0.020 /
Z +0.010 of the original playable DAE diagonal**, yaw **0°**.
That is a useful preview adjustment, not an inferred/native Wii world
transformation or game physics.

`scripts/p0_measure_fc3_transform_private.py` now computes a separate
read-only original-source **surface-registration diagnostic** from the
confirmed FC3 DAE and original, SHA-bound labeled KCL OBJ. It uses only
source OGWS green/fairway groups and original DAE M_Green/M_Fairway
triangle-centroid geometry to optimize a bounded 2D display similarity.
A separate original bunker (or rough) category is **held out entirely
from optimization** and scored before and after. It starts at the
operator's confirmed displayed correction, does not modify this trial
in the UI, and reports the scale/offset and residual as scalar summaries.

```powershell
Set-Location 'D:\Projects\Wii-Golf-Visual-Review'
py -3 -I scripts/p0_measure_fc3_transform_private.py `
  --visual-dae 'D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc3\glf_course_fc3.dae' `
  --terrain-obj '<exact previously checked FC3 PRIVATE KCL OBJ>' `
  --labels '<matching SHA-bound original KCL label sidecar>'
```

The script defaults to manual multiplier=2.0789, x=.020, z=.010, yaw=0,
reads the OS-local selection if available, enforces the source-FC3
2,498-face count, verifies strict OBJ+sidecar hashes and original DAE
source safety, and prints **no original source XYZ, UV, TEX0, or tree
coordinates**. It never writes game source assets, inspector settings,
public Git files or Dolphin RAM, and never approves training.

`ORIGINAL_SURFACE_DISPLAY_FIT_CANDIDATE` means only that the green /
fairway nearest-neighbor mismatch AND independent held-out category pass
conservative *display* residual gates. It is **not** a native original
BRRES root matrix or Wii/KCL world coordinate proof. If the original
FC3 DAE has multiple disparate surface patches, missing OGWS source
labels, or separately triangulated collision, the diagnostic must
abstain/report error instead of claiming a physical transform. Native
alignment still requires further source scene transform/memory ownership
checks. Always preserve the user's manual review state until an
independently checked replacement has actually been accepted by them.

## Unified scene markers after FC3 operator visual confirmation

The viewer's **Show in 3D** row now contains **Trees (3D)**,
**Flag**, **Ball**, **Player (tee proxy)**, and **Labels** toggles.
The old bottom-row tree visibility/crown/ID checkboxes are removed; the
Load/Clear 94-tree data buttons stay intact. All visible objects are
low-polygon WORLD-SPACE 3D approximations transformed through the same
KCL-source-to-FC3-visual display map and perspective camera as the
collision mesh. Tree trunks and two conical foliage tiers, faceted
ball sphere, cylindrical flagpole with cloth, and an articulated
golfer made of 3D cylinders and head sphere replace the original
fixed-pixel symbols and separate base-dot/tree pass.

Objects are painter-sorted *against each other*, but are NOT
depth-tested against the source UV/PNG terrain. Approximate sizes,
colors, facing and a slight player/tee offset are illustrations,
not original Nintendo assets, player XYZ or hitbox/collision volumes.
The existing read-only render/UI, original DAE, KCL OBJ and JSON,
source memory and physics remain untouched.

- On SHA-qualified replay or read-only LIVE: **Ball** is the selected
  ball `+0x30`, **Flag** uses `pin_candidate`, and the **Player**
  symbol is anchored only at `tee_start_candidate`, *not a verified
  actual avatar position*. No field is carried from a prior packet.
- Before loading any source-qualified replay/live sample: the source
  OGWS green surface's area centroid and a far-end fairway triangle
  provide visibly labeled **illustrative-only** markers, so users can
  evaluate placement and scene scale immediately. **These are NOT**
  game-observed flag, ball or player world positions. The UI marks
  this state as `ILLUSTRATIVE`.
- Source-unqualified replay/live samples explicitly hide all positions
  rather than silently falling back to stale real or approximate data.
- All markers need the source KCL-to-visual display map to render. No
  display hypothesis is used in ball physics or training.

The user can load a SHA-verified JSONL capture + manifest in the existing
inspector UI or connect the existing read-only LIVE sampler; individual
sample selections update only same-packet markers. No new memory reads,
controller writes, geometry exports or original art publication.

## Reduced FC3 flag/golfer scale and aim-direction arrow

The user confirmed textured terrain/KCL registration but the first
3D illustrative golfer and pin were **far too tall** in the FC3
inspector screenshot. Both meshes now use **0.8% of the course span**
as a basic scene height instead of 3.5% (about **4.4× smaller**).
The flagpole receives a slightly thicker *illustrative* shaft for
visibility; the 3D ball radius remains deliberately legible. This
does not change the rendered source terrain scale, native world
units, source KCL, actual ball size, or hitboxes.

The Show in 3D toolbar gains **Swing direction arrow (aim hypothesis)**.
The world-space raised arrow starts at the tee candidate, points toward
the pin candidate as the zero-degree reference, and rotates by the
per-sample +0x3C **relative angle candidate** if and only if a same-source
baseline is available. The UI displays the signed angle in **degrees**,
including whether the baseline was operator-set or merely assumed
from the first packet. The original field remains a *candidate*, not
an established physical swing/club trajectory or controller direction.

If there is no replay/live sample, the existing illustrative tee/green
proxy draws a labeled **0.0° approximate-to-green** direction arrow.
If there is a qualified sample but no matching angle baseline, the UI
may show the raw candidate angle in degrees but **hides the arrow**
rather than inventing its orientation. Source identity changes or
unqualified packets also hide it. Turning the arrow checkbox off
removes only the arrow geometry; degrees remain visible as a
read-only status when evidence permits. No controller commands,
game writes, or data training result from this feature.

## FC3 operator review: mirrored aim rotation and ball size correction

On comparison with an in-game right/left rotation, the operator observed
the 3D arrow turning in the **opposite** screen direction. The 3D arrow's
*visual yaw offset* is now mirrored: a positive same-packet relative +0x3C
angle offset is projected with negative display yaw, and vice versa.
The original +0x3C word, decoded signed delta and UI degree readout are
unchanged; the UI still labels this a calibration hypothesis, not a proven
native physical swing angle or verified launch heading.

The ball model had remained oversized despite correction of the flagpole
and golfer. Only the illustrative ball sphere was reduced from 0.15× to
0.035× the approved figure height (~4.3× smaller in diameter), while the
operator-approved flagpole and golfer shapes, placements and dimensions
were not modified. For no-sample illustrative placements, the ball center
is raised by its new smaller radius; for selected sampled positions,
the source ball position is left untouched.

The original camera navigation functions and mouse sensitivity are
**identical** to the original 2026-11-10 tree-inspector source; the extra
3D geometry and additional toolbar rows can affect observed render
responsiveness and visible canvas size. Restore prior F/Shift+F
**Collision-mode framing** using the currently displayed mapped KCL
bounds. All other visual modes use the existing playable and full
textured-model frame presets. RMB continues fixed-eye look, LMB orbit,
MMB pan, arrow keys continuous movement, RMB+WASD/QE fly, wheel dolly.
Regression tests guard these behaviors.

No change to original KCL, DAE, tree source positions, samples, game
RAM, controller inputs, native physics or training approval.

## Selected club next to the A indicator (restored from PR #426)

The previous operator source study and live validation established a
separate US RSPE01 Rev1 club selector global pointer at **0x804BF900**,
distinct from the PlayerManager global, and a bounded u32 field at
owner **+0x1C**. The four validated labels are:
0 DRIVER, 1 IRON, 2 WEDGE, 3 PUTTER.
The old false PlayerManager+0x1C candidate is NOT used.

Port the original proven source-gated batched live reader and typed label
from the original PR #426 into the newer FC3 3D inspector branch. In the
main header, **CLUB WEDGE · index 2**, for example, appears on the very
same row as **A PRESSED/RELEASED**. The independent club pointer and
value must be valid, 0..3, unchanged across a complete original
source-validated packet. Arbitrary injected packet readers may NOT
promote a club index to verified; replay/offline captures do not contain
the new club index and display **CLUB UNKNOWN**.

Connection/reconnection resets, playback changes, disconnect, errors,
and stale (>3s) live samples all clear the club indicator to UNKNOWN.
The existing A heuristic is unchanged and independent. This UI feature
only exposes an existing operator-confirmed source mapping: no added
RAM scanning, no controller commands, no write RPCs, no training,
no original art/geometry and no player physics reinterpretation.
