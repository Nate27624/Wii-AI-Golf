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
