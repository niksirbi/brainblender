"""Root meshes of several species in a row, as a wide banner.

Brains are ordered by real size, then rescaled to a similar apparent size.

Run with: blender --background --python scene.py -- <meshes_dir> <output_png>
where <meshes_dir> holds one brainblender export folder per atlas.
"""

import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Color, Vector

# Blender helpers aren't installed in Blender's Python, so load them from the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "brainblender/blender"))

from import_meshes import import_meshes  # noqa: E402
from scene_setup import (  # noqa: E402
    ANTERIOR,
    RIGHT,
    SUPERIOR,
    add_light,
    render,
    scene_args,
)

VIEW_DIRECTION = (ANTERIOR + SUPERIOR + RIGHT).normalized()  # brain → camera
CAMERA_ROTATION = (-VIEW_DIRECTION).to_track_quat("-Z", "Y")
CAMERA_RIGHT = CAMERA_ROTATION @ Vector((1, 0, 0))
CAMERA_UP = CAMERA_ROTATION @ Vector((0, 1, 0))

# In units of a brain's apparent size (each is scaled to unit on-screen area)
GAP = 0.25
MARGIN = 0.2
RESOLUTION_X = 3000

# One colour per brain, smallest to largest: muted, earthy tones
PALETTE = ["#6F8FBF", "#D98C2E", "#D4918C", "#5F8F7B", "#B5403E", "#A6949E"]
ROUGHNESS = 0.8  # matte, clay-like surface
BACKGROUND = (1.0, 1.0, 1.0)


def extent(points: list[Vector], axis: Vector) -> tuple[float, float]:
    """Return the (min, max) of the points projected onto axis."""
    projected = [p.dot(axis) for p in points]
    return min(projected), max(projected)


def size(obj: bpy.types.Object) -> float:
    """Return the diagonal of the object's bounding box."""
    return (Vector(obj.bound_box[6]) - Vector(obj.bound_box[0])).length


def set_material(obj: bpy.types.Object, hex_color: str) -> None:
    """Give the object a matte material with the given sRGB hex colour."""
    srgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = Color(srgb).from_srgb_to_scene_linear()
    nodes = obj.active_material.node_tree.nodes
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*linear, 1.0)
    bsdf.inputs["Roughness"].default_value = ROUGHNESS


def flatten_onto_background(path: Path, color: tuple[float, float, float]) -> None:
    """Replace the transparency of a rendered PNG with a solid colour.

    Done on the saved image so the background doesn't light the scene and isn't
    dimmed by the view transform.
    """
    image = bpy.data.images.load(str(path))
    pixels = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(-1, 4)
    alpha = pixels[:, 3:]
    pixels[:, :3] = pixels[:, :3] * alpha + np.array(color) * (1 - alpha)
    pixels[:, 3] = 1.0
    image.pixels.foreach_set(pixels.ravel())
    image.save()


def arrange_in_row(brains: list[bpy.types.Object]) -> tuple[float, float]:
    """Line the brains up along the camera's horizontal axis.

    Returns the (width, height) of the row as seen by the camera.
    """
    cursor = 0.0
    row_height = 0.0
    for brain in brains:
        # Vertices rather than bounding-box corners, which overstate oblique extents
        points = [v.co for v in brain.data.vertices]
        left, right = extent(points, CAMERA_RIGHT)
        bottom, top = extent(points, CAMERA_UP)
        # Equal on-screen area keeps elongated and compact brains balanced
        scale = ((right - left) * (top - bottom)) ** -0.5
        width, height = (right - left) * scale, (top - bottom) * scale

        center = CAMERA_RIGHT * (left + right) / 2 + CAMERA_UP * (bottom + top) / 2
        brain.scale = (scale,) * 3
        brain.location = CAMERA_RIGHT * (cursor + width / 2) - scale * center
        cursor += width + GAP
        row_height = max(row_height, height)
    return cursor - GAP, row_height


def add_banner_camera(row_width: float, row_height: float) -> None:
    """Add an orthographic camera framing the row, sizing the render to fit it."""
    scene = bpy.context.scene
    frame_width = row_width + 2 * MARGIN
    frame_height = row_height + 2 * MARGIN
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = round(RESOLUTION_X * frame_height / frame_width)
    scene.render.resolution_percentage = 100

    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(frame_width, frame_height)
    # Far enough back that no brain crosses the camera plane
    cam.location = CAMERA_RIGHT * row_width / 2 + VIEW_DIRECTION * 10
    cam.rotation_euler = CAMERA_ROTATION.to_euler()


if __name__ == "__main__":
    meshes_dir, output_png = scene_args()
    brains: list[bpy.types.Object] = []
    for i, manifest in enumerate(sorted(meshes_dir.glob("*/manifest.json"))):
        brains += import_meshes(manifest.parent, clear=i == 0)
    brains.sort(key=size)
    for brain, hex_color in zip(brains, PALETTE, strict=False):
        set_material(brain, hex_color)

    add_banner_camera(*arrange_in_row(brains))
    add_light(VIEW_DIRECTION)
    bpy.context.scene.render.film_transparent = True
    render(output_png)
    flatten_onto_background(output_png, BACKGROUND)
