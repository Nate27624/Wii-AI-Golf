# P0 private KCL to OBJ export

## Operator evidence and scope

Original source/SHA-gated captures 1, 5 and 7 each produced one
MEM2 file-layout KCL candidate, 2498/2498 indexed/unit-normal/
nondegenerate triangle reconstructions, identical prism table bytes,
and tee/pin within 2% of candidate bbox diagonal in untransformed
source components. Same hole 1; the snapshots may share one asset.
Active collision ownership and octree reachability remain unproven.

Other agent PR #411 owns trees and semantic material discovery. This
exporter does not touch material, rough/green, texture, tree, or octree code.

The new script scripts/p0_kcl_obj_export_private.py is stacked on
draft #406 / #403 and reuses source/geometry readers. It requires the
original seven-pair SHA/scene/selected-ball/tee/pin/course-roots gates,
one unique MEM2 file-style KCL, every prism reconstructed, tee/pin
categorical proximity, and identical geometry on controls 1 and 7
against capture 5. All original hashes are checked again before output.

The output is a new private ASCII v/f triangle OBJ, placed only in
one of two explicitly approved directories:
- ignored sibling Wii-AI-Golf-Data/derived when that location is outside
  every Git worktree;
- Windows per-user LOCALAPPDATA/WiiGolfAI/private/derived when the sibling
  private Data directory is under an enclosing Git checkout.

The LOCALAPPDATA option is intentionally narrow; it must already exist,
is checked for symlinks, and any .git ancestor still fails closed. No
existing-file overwrite or native RAM/OBJ/paths/publication is permitted.
Actual original seven-capture source remains in the SHA-verified Data area.

## Windows operator use

From this stacked branch, invoke the isolated offline exporter with
--archive pointing to the original numbered seven-pair PRIVATE capture
directory; --output pointing directly to a new file ending in -PRIVATE.obj under the
approved private Data/derived folder, or under LOCALAPPDATA/WiiGolfAI/private/derived
after that per-user directory is created. Use --capture 5 --controls 1 7.
If OUTPUT_INSIDE_GIT appeared for the original destination, change ONLY
the output path; leave original archive and all scene/mesh gates unchanged.
The operator receives the full copy/paste PowerShell command in chat.
Dolphin is not required. No re-capture.

After export, use the **Load PRIVATE terrain OBJ** control in the
existing rotatable 3D inspector, merged by UI PR #410. This accepts
strict ASCII 'v x y z' and 'f i j k' records. The exporter gives three
vertices per triangle with no transformations, materials, or textures.
The UI applies its own safe focus and decimation (live up to 600 faces,
offline up to 1200). Compare tee/flag/ball visually and report
misalignment; no force-fit transform.

The mesh is PRIVATE and copyright-sensitive. Training remains
disabled; no active physics or verified textured model claim.


## Explicit OGWS per-face groups for solid colored inspector

Once the uncolored SHA/source-gated OBJ is validated locally, a separate NEW
file can be exported with the --surface-groups option. The exporter reads
the original attribute returned alongside each source triangle by canonical
KCL prism reconstruction; it writes exactly one plain Wavefront
g KCL_OGWS_XXXX line before its matching f i j k line. IDs are BE16 values,
not guessed from a category histogram or tee/flag proximity. This preserves
all 2498 original face indices and verifies original source-capture geometry
is byte-identical against controls 1 and 7.

Use --output ending in e.g. hole01-collision-colored-PRIVATE.obj directly
in the ignored, untracked, D: project Data/derived location. Never overwrite
the earlier legacy OBJ. The latest inspector filled-polygon branch PR #419
accepts both legacy and exact tagged forms. Source surface colors are
original-game categorical hypotheses, not visual game textures or real
coefficient-of-friction measurements. Camera lock and unknown IDs stay neutral;
training remains false.


## Preferred UI-only color workflow (operator correction)

Do **not** rewrite, re-export, or embed material groups into the successfully
created original private geometry OBJ. Its SHA stays stable. To make
categorical material colors a presentation concern, use
scripts/p0_kcl_surface_labels_private.py on the original SHA-gated capture
with --original-obj pointing to existing D: private Data/derived
hole01-collision-candidate-PRIVATE.obj. It verifies exactly the same
source-coordinate v/f face order and 2498 per-prism original attributes
against capture 5 and controls 1,7. It emits only a small, **separate**
hole01-collision-candidate-labels-PRIVATE.json in the same ignored/private
Data/derived folder, containing one source BE16 attribute per existing face
and the exact unchanged OBJ SHA. The no-overwrite and Git-ignore +
not-indexed requirements still apply. This is data only, no colors or geometry.

The inspector PR #419 takes --terrain-obj (the unchanged original) and
--terrain-labels (this separate source JSON), verifies SHA and face count,
then colors the existing triangle faces entirely within Tkinter at runtime.
Its Solid terrain and Triangle edges controls remain purely display toggles.
There are no inferred fairway/rough/green labels. Neither source file nor
private JSON/OBJ is committed. Octree reachability/active collision remain
unproven; training false.
