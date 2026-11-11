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
