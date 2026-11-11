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
