# Private Wii Sports Golf visual extraction — local operator workflow

Status: discovery/preview tooling available; the exact original RSPE01 Rev1 hole-1 visual source is NOT selected or exported. Do not claim active-hole or texture alignment.

The original SHA-verified 2,498-triangle KCL candidate under D:\Projects is COLLISION geometry and has no native MDL0 UVs or TEX0 texture art. Do NOT change its OBJ or guess UVs.

## 1. Extract the filesystem of your legally obtained copy in Dolphin

From the game list: right-click Wii Sports -> Properties -> Filesystem. Confirm the correct original game and Rev1 locally; under /Stage/RPGolScene/ look for candidate *.carc archives (reported location; candidate only). Extract chosen course files, or choose Extract Entire Disc into a NON-GIT private folder such as:

    D:\Projects\WiiGolfVisualPrivate\disc\

Keep the disc, exported source and original model/image bytes out of GitHub and ChatGPT.

## 2. Scan your own exported files (read-only)

From the repo containing the discovery script:

    py -3 -I scripts\p0_private_visual_asset_discovery.py --scan "D:\Projects\WiiGolfVisualPrivate"

Reported stages:
- ARCHIVES_FOUND_NEEDS_FORMAT_VERIFIED_EXTRACTION: .carc/.arc/.szs candidates.
- BRRES_FOUND_NEEDS_MDL0_TEX0_EXPORT: native Wii visual model candidate.
- DAE_FOUND_NEEDS_UV_OBJ_MTL_PNG_CONVERSION: convert native model preserving material UV data.
- UV_VISUAL_MODELS_READY_TO_PREVIEW_HOLE_UNVERIFIED: actual local UV OBJ/MTL/PNG accepted by inspector parser.
- NO_COURSE_VISUAL_ASSETS_FOUND: no recognized candidate files.

The tool never guesses hole ownership from a file name; scans are bounded and symlinks not followed.

## 3. Inspect and unpack an archive, without editing the source

Wiimms SZS Toolset includes wszst LIST and EXTRACT for supported U8/SZS/RARC/BRRES archives; file extension alone does NOT prove that any particular Wii Sports .carc is supported. Explicitly replace CHOSEN with the filename you found:

    wszst LIST "D:\Projects\WiiGolfVisualPrivate\disc\Stage\RPGolScene\CHOSEN.carc"

Only if LIST succeeds, run into a NEW private directory (no --overwrite):

    wszst EXTRACT --DEST "D:\Projects\WiiGolfVisualPrivate\unpacked\CHOSEN" "D:\Projects\WiiGolfVisualPrivate\disc\Stage\RPGolScene\CHOSEN.carc"

If LIST rejects the archive, stop; do not treat unknown compression/magic as a valid BRRES.

## 4. Export genuine visual UVs and diffuse textures

Use BrawlCrate or BRRESViewer to open glf_course_* BRRES candidates. Export MDL0 as COLLADA .dae (BrawlCrate requires explicitly choosing DAE instead of its default MDL0 extension) and TEX0 images as PNG. Keep source UV indices/material associations.

In Blender 4.5 LTS use built-in COLLADA import; Blender 5.x removed built-in DAE support and needs a separate importer. Import DAE, associate original exported PNGs with materials, then export triangulated (or quads) Wavefront OBJ+MTL retaining real UVs. The model is a source *visual* model, NOT the KCL collision candidate.

Expected private files:
    D:\Projects\WiiGolfVisualPrivate\hole01_candidate\
        course_visual.obj
        course_visual.mtl
        green.png
        grass.png

The current strict viewer requires v, vt, f v/vt, exactly one mtllib, explicit usemtl per face, MTL newmtl/map_Kd, and safe local PNG paths. Advanced game TEV layers, incompatible MTL or multi-image shaders require separate research; do not silently assign unrelated textures.

## 5. Validate and preview within the inspector

    py -3 -I scripts\p0_private_visual_asset_discovery.py --check-model "D:\Projects\WiiGolfVisualPrivate\hole01_candidate\course_visual.obj"
    py -3 -I scripts\p0_private_visual_asset_discovery.py --check-model "D:\Projects\WiiGolfVisualPrivate\hole01_candidate\course_visual.obj" --preview

Optional display dependencies: py -m pip install -e '.[visual]' in a clean, current-main repo. Alternatively click Preview PRIVATE game textures in the current-main inspector. The visual window is separate from source-qualified KCL/ball/tee/pin/A overlays.

Do NOT combine render and collision meshes until exact native source/hole, axis, scale and translation align against tee, pin and additional landmarks. No real active collision/physics/training claim; training_approved=false.

References:
https://szs.wiimm.de/wszst/cmd-extract.html
https://github.com/soopercool101/BrawlCrate/issues/115
https://developer.blender.org/docs/release_notes/5.0/pipeline_io/


## Real operator result: FC1 main course visuals (2026-11-10)

The original main course BRRES was read-only extracted at
D:\Projects\WiiGolfVisualPrivate\unpacked\glf_course_fc1\G3D\glf_course_fc1.brres.

wszst XALL --ext --ext into a NEW private visual_exports/glf_course_fc1
directory produced:
- glf_course_fc1.mdl0 (UV-bearing source model candidate);
- 19 raw TEX0 resources;
- 36 PNG files including mipmaps, representing 18 base-level texture images.

CRITICAL: extraction emitted ERROR #38 INVALID IMAGE FORMAT for
glf_tokosenFix.tex0.png, because that paletted texture has unsupported
palette format 0xffffffff; no valid base-level PNG was produced for it.
Do not claim full success. Preserve original BRRES and all 36 successfully
exported images. Grass/fairway, green, rough, out-of-bounds, sand/bunker,
and multiple edge textures are already available. Do not fabricate missing
paletted texture; assess source material usage first and BrawlCrate can be
tried for its original PLT0/TEX0 pair if required.

Next: export ORIGINAL BRRES 3DModels(NW4R)/glf_course_fc1 MDL0 to .dae
in BrawlCrate (official Windows winget ID soopercool101.BrawlCrate).
Choose .dae export format explicitly, not default .mdl0. Preserve
material UV mappings. Open that DAE in Blender 4.5 LTS and export a new
UV OBJ/MTL paired with authentic base PNGs only after independently
matching material/TEX0 names. Never rewrite the KCL collision OBJ.

Audit the existing output read-only:
  py -3 -I scripts\p0_private_visual_asset_discovery.py --scan "D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1"

Expected stage MDL0_WITH_EXTRACTED_PNG_NEEDS_UV_DAE_EXPORT and one
unresolved glf_tokosenFix.tex0 base PNG. No claim about active Hole1
visual source identity, native GPU TEV fidelity, KCL alignment or training.


## BrawlCrate DAE material reference gate passed

Operator's exact original glf_course_fc1.dae (1,181,053 bytes) reports:
12 Collada geometries, 12 triangle groups, 13 TEXCOORD inputs,
19 library images, 12 library materials, and 11 actual sampled
diffuse texture effect slots. Their exact original DAE source bindings are:

    M_Bunker       glf_sand01.png
    M_Color        glf_color1.png
    M_Enkei        glfM_hayasi3.png
    M_Fairway      glf_fairway1.png
    M_Green        glf_green1.png
    M_Kiwa_Bunker  glf_Kiwa_Bunker.png
    M_Kiwa_F       glf_Kiwa_F.png
    M_Kiwa_OB      glf_Kiwa_OB.png
    M_Kiwa_R       glf_Kiwa_R.png
    M_OB           glf_ob1.png
    M_Rough        glf_rough1.png

M_Kiwa_Black has no DAE texture effect; it must remain an
untextured original-color Kd material, not receive any invented PNG.
glf_tokosenFix image is referenced in the DAE library, but it is
NOT assigned by one of these 11 texture slots; its failed palette
conversion does not block this first source-model preview.
No game native TEV, active hole or KCL/world transform is claimed.

New script p0_prepare_private_dae_textures.py stages EXACTLY the
source-linked base PNG files, renaming existing .tex0.png to DAE
expected names as byte-identical copies into a brand-new private
directory. DAE itself is copied byte-identically; originals untouched.
It fails closed on missing images/ambiguous links/non-UV models,
wrong XML, Git, symlinks or pre-existing destination:

    py -3 -I scripts\p0_prepare_private_dae_textures.py --dae "D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\glf_course_fc1.dae" --texture-dir "D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\Textures(NW4R)" --output "D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\uv_stage"

Then use Blender **4.5 LTS**, which still has its native
Collada importer (Blender 5.x removed bundled Collada import).
Source-only script p0_blender_private_dae_to_obj.py runs in
Blender 4.5, reads stage manifest, imports DAE source UVs, connects
only those 11 original PNGs and requires authentic diffuse source
color for untextured M_Kiwa_Black, then exports adjacent UV
glf_course_fc1_visual.obj plus MTL. It does NOT add nonexistent
materials or replace the collision KCL OBJ:

    blender --background --factory-startup --python-exit-code 7 --python scripts\p0_blender_private_dae_to_obj.py -- --stage "D:\Projects\WiiGolfVisualPrivate\visual_exports\glf_course_fc1\uv_stage"

A Blender native application run is only verifiable on operator's
machine, NOT proven by synthetic CI. Win+Ubuntu CI verifies offline
source DAE/PNG staging and Python Blender-script syntax; do not
claim Blender runtime success until original operator test.

The combined original-source inspector branch #429 (based on
solid KCL #419) now supports a source-MTL Kd-only material without
faking a PNG (e.g. M_Kiwa_Black); use it to select the resulting
UV OBJ in the left-pane Preview PRIVATE game textures button.
Standalone #428's main-based older strict visual checker may
still reject Kd-only source materials. Keep the KCL 2498-face OBJ
unmodified and separate.
