"""Shared helpers for scene scripts that run inside Blender (bpy + stdlib only)."""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# Anatomical directions in Blender space, as exported by brainblender.mesh.normalize.
RIGHT = Vector((1, 0, 0))
ANTERIOR = Vector((0, 1, 0))
SUPERIOR = Vector((0, 0, 1))


def scene_args() -> tuple[Path, Path]:
    """Return (meshes_dir, output_png) from the args Blender passes after '--'."""
    argv = sys.argv
    script_args = argv[argv.index("--") + 1 :] if "--" in argv else []
    if len(script_args) != 2:
        print(
            "Usage: blender --background --python <scene.py> -- "
            "<meshes_dir> <output_png>"
        )
        sys.exit(1)
    return Path(script_args[0]), Path(script_args[1])


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


def add_camera(
    target: Vector, radius: float, view_direction: Vector, margin: float = 1.1
) -> None:
    """Add a camera along view_direction (target → camera) that fits the sphere.

    margin is the padding around the sphere in the frame.
    """
    view_direction = view_direction.normalized()
    scene = bpy.context.scene
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam

    # The camera's angle spans the wider (horizontal) side; fit the narrower one.
    aspect = scene.render.resolution_y / scene.render.resolution_x
    half_fov = math.atan(math.tan(cam.data.angle / 2) * min(aspect, 1))
    distance = margin * radius / math.sin(half_fov)

    cam.location = target + view_direction * distance
    cam.rotation_euler = (-view_direction).to_track_quat("-Z", "Y").to_euler()


def add_light(view_direction: Vector, energy: float = 3.0) -> None:
    """Add a sun shining roughly from the camera, tilted towards superior."""
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
    sun.data.energy = energy
    bpy.context.scene.collection.objects.link(sun)
    key = -(view_direction.normalized() + SUPERIOR).normalized()
    sun.rotation_euler = key.to_track_quat("-Z", "Y").to_euler()


def render(path: Path) -> None:
    """Render the active camera to a PNG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {path}")
