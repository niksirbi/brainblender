"""Blackcap root mesh scene, viewed obliquely from anterior-superior-right.

Run with: blender --background --python scene.py -- <meshes_dir> <output_png>
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# Blender helpers aren't installed in Blender's Python, so load them from the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "brainblender/blender"))

from import_meshes import import_meshes  # noqa: E402

# Anatomical directions in Blender space, as exported by brainblender.mesh.normalize.
RIGHT = Vector((1, 0, 0))
ANTERIOR = Vector((0, 1, 0))
SUPERIOR = Vector((0, 0, 1))

VIEW_DIRECTION = (ANTERIOR + SUPERIOR + RIGHT).normalized()  # brain → camera
MARGIN = 1.1  # padding around the brain in the frame


def scene_bounds() -> tuple[Vector, float]:
    """Return the center and bounding-sphere radius of all mesh objects."""
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    lo = Vector(min(c[i] for c in corners) for i in range(3))
    hi = Vector(max(c[i] for c in corners) for i in range(3))
    return (lo + hi) / 2, (hi - lo).length / 2


def add_camera(target: Vector, radius: float) -> None:
    """Add a camera along VIEW_DIRECTION that fits the bounding sphere."""
    scene = bpy.context.scene
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam

    # The camera's angle spans the wider (horizontal) side; fit the narrower one.
    aspect = scene.render.resolution_y / scene.render.resolution_x
    half_fov = math.atan(math.tan(cam.data.angle / 2) * min(aspect, 1))
    distance = MARGIN * radius / math.sin(half_fov)

    cam.location = target + VIEW_DIRECTION * distance
    cam.rotation_euler = (-VIEW_DIRECTION).to_track_quat("-Z", "Y").to_euler()


def add_light() -> None:
    """Add a sun shining roughly from the camera, tilted towards superior."""
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
    sun.data.energy = 3.0
    bpy.context.scene.collection.objects.link(sun)
    key = -(VIEW_DIRECTION + SUPERIOR).normalized()
    sun.rotation_euler = key.to_track_quat("-Z", "Y").to_euler()


def render(path: Path) -> None:
    """Render the active camera to a PNG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    argv = sys.argv
    # Blender passes everything after '--' as script args
    script_args = argv[argv.index("--") + 1 :] if "--" in argv else []

    if len(script_args) != 2:
        print(
            "Usage: blender --background --python scene.py -- <meshes_dir> <output_png>"
        )
        sys.exit(1)

    meshes_dir, output_png = (Path(arg) for arg in script_args)
    import_meshes(meshes_dir)
    center, radius = scene_bounds()
    add_camera(center, radius)
    add_light()
    render(output_png)
    print(f"Rendered {output_png}")
