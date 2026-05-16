"""Import brainblender meshes into Blender.

Run with: blender --python import_meshes.py -- <meshes_dir>
"""

import json
import sys
from pathlib import Path

import bpy


def create_material(name: str, color_rgb: list[int]) -> bpy.types.Material:
    """Create a Blender material with the given RGB color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    r, g, b = [c / 255.0 for c in color_rgb]
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    return mat


def clear_default_scene() -> None:
    """Remove all default objects (Cube, Camera, Light) from the scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def frame_viewport() -> None:
    """Frame all objects in the 3D viewport."""
    bpy.ops.object.select_all(action="SELECT")
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            region = next(r for r in area.regions if r.type == "WINDOW")
            with bpy.context.temp_override(area=area, region=region):
                bpy.ops.view3d.view_selected()
            break


def import_meshes(meshes_dir: Path) -> None:
    """Import all meshes from a brainblender export directory."""
    manifest_path = meshes_dir / "manifest.json"
    with manifest_path.open() as f:
        manifest = json.load(f)

    clear_default_scene()

    atlas_name = manifest["atlas"]
    collection = bpy.data.collections.new(atlas_name)
    bpy.context.scene.collection.children.link(collection)

    for region in manifest["regions"]:
        ply_path = meshes_dir / region["file"]
        bpy.ops.wm.ply_import(filepath=str(ply_path))

        obj = bpy.context.active_object
        obj.name = region["acronym"]

        mat = create_material(region["acronym"], region["color_rgb"])
        obj.data.materials.clear()
        obj.data.materials.append(mat)

        for col in obj.users_collection:
            col.objects.unlink(obj)
        collection.objects.link(obj)

    frame_viewport()
    print(f"Imported {len(manifest['regions'])} regions from '{atlas_name}'")


if __name__ == "__main__":
    argv = sys.argv
    # Blender passes everything after '--' as script args
    script_args = argv[argv.index("--") + 1 :] if "--" in argv else []

    if not script_args:
        print("Usage: blender --python import_meshes.py -- <meshes_dir>")
        sys.exit(1)

    meshes_dir = Path(script_args[0])
    if not (meshes_dir / "manifest.json").exists():
        print(f"Error: No manifest.json found in {meshes_dir}")
        sys.exit(1)

    import_meshes(meshes_dir)
