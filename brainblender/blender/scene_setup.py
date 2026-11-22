"""Shared helpers for scene scripts that run inside Blender (bpy + stdlib only)."""

import sys
from pathlib import Path

import bpy
from mathutils import Vector

# Anatomical directions in Blender space, as exported by brainblender.mesh.normalize.
RIGHT = Vector((1, 0, 0))
ANTERIOR = Vector((0, 1, 0))
SUPERIOR = Vector((0, 0, 1))


def script_args() -> list[str]:
    """Return the args Blender passes to the script after '--'."""
    argv = sys.argv
    return argv[argv.index("--") + 1 :] if "--" in argv else []


def scene_args() -> tuple[Path, Path]:
    """Return (meshes_dir, output_png) from the script args."""
    args = script_args()
    if len(args) != 2:
        print(
            "Usage: blender --background --python <scene.py> -- "
            "<meshes_dir> <output_png>"
        )
        sys.exit(1)
    return Path(args[0]), Path(args[1])


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
    target: Vector,
    radius: float,
    view_direction: Vector,
    margin: float = 1.15,
    resolution: tuple[int, int] = (1920, 1920),
) -> None:
    """Add a camera along view_direction (target → camera) that frames all meshes.

    Also sets the render resolution, since the framing depends on its aspect.
    The meshes fill 1/margin of the frame along its tighter side.
    """
    view_direction = view_direction.normalized()
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = resolution
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    # A long lens keeps the camera far back, so perspective doesn't distort the brain
    cam.data.lens = 120

    # Start outside the scene, looking along -view_direction, then let Blender
    # move the camera so the mesh vertices just fill the frame.
    cam.location = target + view_direction * 10 * radius
    cam.rotation_euler = (-view_direction).to_track_quat("-Z", "Y").to_euler()
    coords = [
        c
        for obj in scene.objects
        if obj.type == "MESH"
        for v in obj.data.vertices
        for c in obj.matrix_world @ v.co
    ]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cam.location, _ = cam.camera_fit_coords(depsgraph, coords)
    # A shorter lens zooms out around the frame centre, leaving the margin.
    cam.data.lens /= margin


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
