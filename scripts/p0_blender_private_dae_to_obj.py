#!/usr/bin/env python3
"""Use Blender 4.5 to convert staged source UV DAE+PNG into OBJ/MTL.

Invoke with Blender 4.5: blender -b --factory-startup --python THIS -- --stage FOLDER
Inputs are user-private outside Git. No original game model or texture rewrite.
No guessed UV, color or TEX0 material assignments. Refuse unsupported mappings.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import bpy

NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z")


def name_of(element):
    return element.tag.rsplit("}", 1)[-1]


def original_source_color(dae: Path, material: str) -> tuple[float, float, float, float]:
    root = ET.parse(dae).getroot()
    effect_id = material + "-fx"
    effects = [n for n in root.iter()
               if name_of(n) == "effect" and n.get("id") == effect_id]
    if len(effects) != 1:
        raise ValueError("Original untextured material effect missing")
    diffuse = [n for n in effects[0].iter() if name_of(n) == "diffuse"]
    colors = [n for d in diffuse for n in d if name_of(n) == "color" and n.text]
    if len(colors) != 1:
        raise ValueError("Untextured material lacks exact DAE source diffuse Kd")
    vals = tuple(float(t) for t in colors[0].text.split())
    if len(vals) not in (3, 4) or not all(math.isfinite(v) and 0 <= v <= 1 for v in vals):
        raise ValueError("Untextured original DAE color is invalid")
    return vals if len(vals) == 4 else (*vals, 1.0)


def main():
    if tuple(bpy.app.version[:2]) != (4, 5):
        raise ValueError("Use Blender 4.5 LTS: Collada importer is required")
    if "--" not in sys.argv:
        raise ValueError("Expected -- --stage OUTSIDE_GIT_DIRECTORY")
    args = sys.argv[sys.argv.index("--")+1:]
    if len(args) != 2 or args[0] != "--stage":
        raise ValueError("Expected --stage DIRECTORY")
    stage = Path(args[1]).resolve(strict=True)
    if any((p / ".git").exists() for p in (stage, *stage.parents)):
        raise ValueError("Never export original Wii assets in a Git checkout")
    if any(p.is_symlink() for p in (stage, *stage.parents)):
        raise ValueError("Private source asset symlinks forbidden")
    mapping_file = stage/"source-material-mapping-PRIVATE.json"
    if not mapping_file.is_file() or mapping_file.is_symlink():
        raise ValueError("Use the source-verified staging script first")
    manifest = json.loads(mapping_file.read_text(encoding="utf-8"))
    if manifest.get("status") != "ORIGINAL_UV_DAE_TEXTURES_STAGED":
        raise ValueError("Manifest not source-stage qualified")
    texture_map = manifest["material_png"]
    untextured = set(manifest["untextured_materials"])
    if not (texture_map and all(NAME.fullmatch(k) and NAME.fullmatch(v)
                                for k, v in texture_map.items())):
        raise ValueError("Source texture bindings invalid")
    dae = stage/manifest["dae"]
    if not dae.is_file() or dae.is_symlink() or dae.suffix.lower() != ".dae":
        raise ValueError("Source UV Collada not found")
    for name in texture_map.values():
        source = stage/name
        if not source.is_file() or source.is_symlink():
            raise ValueError("Expected source staged PNG missing: " + name)
    obj = stage/(dae.stem + "_visual.obj")
    mtl = obj.with_suffix(".mtl")
    if obj.exists() or mtl.exists():
        raise ValueError("Output exists; never overwrite source or previous preview")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.collada_import(filepath=str(dae), fix_orientation=False, import_units=False)

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise ValueError("No imported source visual meshes")
    for mesh in meshes:
        if not mesh.data.uv_layers:
            raise ValueError("Imported original visual mesh has no UV map")
        if any(poly.material_index >= len(mesh.data.materials) for poly in mesh.data.polygons):
            raise ValueError("Source mesh polygon has no material binding")

    used_materials = {}
    for mesh in meshes:
        for face in mesh.data.polygons:
            if (face.material_index >= len(mesh.data.materials)
                    or mesh.data.materials[face.material_index] is None):
                raise ValueError("Source model polygon material unavailable")
        for material in mesh.data.materials:
            if material is not None:
                used_materials[material.name] = material
    if not used_materials:
        raise ValueError("Source model has no imported materials")
    recognized = set()
    for mat in used_materials.values():
        # Blender adds .001 etc for duplicate imported materials. Never
        # reinterpret unrelated material names as a source mapping.
        key = re.sub(r"\.\d{3}$", "", mat.name)
        if key not in texture_map and key not in untextured:
            raise ValueError("Unrecognized Blender/DAE material: " + mat.name)
        recognized.add(key)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        if key in texture_map:
            image_path = stage/texture_map[key]
            image = bpy.data.images.load(str(image_path), check_existing=True)
            tex = nodes.new("ShaderNodeTexImage")
            tex.image = image
            mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            color = original_source_color(dae, key)
            bsdf.inputs["Base Color"].default_value = color
            mat.diffuse_color = color
    if not set(texture_map).intersection(recognized):
        raise ValueError("None of the original textured source materials imported")

    bpy.ops.object.select_all(action="DESELECT")
    for mesh in meshes:
        mesh.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    # Blender 4.5 exporter with UVs, original material names, and LOCAL
    # unmodified source texture PNG references. No guessed alignment to KCL.
    bpy.ops.wm.obj_export(
        filepath=str(obj), check_existing=False, export_selected_objects=True,
        export_triangulated_mesh=True, export_uv=True, export_normals=True,
        export_materials=True, export_pbr_extensions=False, path_mode="STRIP",
        forward_axis="Y", up_axis="Z", apply_modifiers=False)
    if not obj.is_file() or not mtl.is_file():
        raise ValueError("Collada source converted without expected OBJ+MTL")
    print(json.dumps({
        "status": "ORIGINAL_SOURCE_UV_OBJ_MTL_EXPORTED",
        "model": obj.name,
        "material_file": mtl.name,
        "source_visual_mesh_count": len(meshes),
        "source_material_count": len(recognized),
        "untextured_source_materials": sorted(untextured & recognized),
        "alignment_verified": False,
        "training_approved": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
