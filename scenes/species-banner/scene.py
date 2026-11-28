"""Root meshes of several species in rows, as a wide banner.

Brains are rescaled to a similar apparent size and laid out in centred rows.

Run with: blender --background --python scene.py -- <meshes_dir> <output_png> <row>...
where <meshes_dir> holds one fetch-meshes folder per atlas, and each
<row> is a space-separated list of atlas names, from the top row down.
"""

import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Color, Vector

# Blender helpers aren't installed in Blender's Python, so load them from the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "brainblender/blender"))

from import_meshes import import_meshes  # noqa: E402
from palette import OFF_WHITE, PALETTE  # noqa: E402
from scene_setup import (  # noqa: E402
    ANTERIOR,
    RIGHT,
    SUPERIOR,
    add_light,
    render,
    script_args,
)

VIEW_DIRECTION = (ANTERIOR + SUPERIOR + RIGHT).normalized()  # brain → camera
CAMERA_ROTATION = (-VIEW_DIRECTION).to_track_quat("-Z", "Y")
CAMERA_RIGHT = CAMERA_ROTATION @ Vector((1, 0, 0))
CAMERA_UP = CAMERA_ROTATION @ Vector((0, 1, 0))

# In units of a brain's apparent size (each is scaled to unit on-screen area)
GAP = 0.25
MARGIN = 0.2
RESOLUTION = (2240, 1260)

ROUGHNESS = 0.8  # matte, clay-like surface
BACKGROUND = OFF_WHITE


def extent(points: list[Vector], axis: Vector) -> tuple[float, float]:
    """Return the (min, max) of the points projected onto axis."""
    projected = [p.dot(axis) for p in points]
    return min(projected), max(projected)


def hex_to_srgb(hex_color: str) -> tuple[float, float, float]:
    """Return the 0-1 sRGB components of a '#RRGGBB' colour."""
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return r, g, b


def set_material(obj: bpy.types.Object, hex_color: str) -> None:
    """Give the object a matte material with the given sRGB hex colour."""
    linear = Color(hex_to_srgb(hex_color)).from_srgb_to_scene_linear()
    nodes = obj.active_material.node_tree.nodes
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*linear, 1.0)
    bsdf.inputs["Roughness"].default_value = ROUGHNESS


def flatten_onto_background(path: Path, hex_color: str) -> None:
    """Replace the transparency of a rendered PNG with a solid sRGB hex colour.

    Done on the saved image so the background doesn't light the scene and isn't
    dimmed by the view transform.
    """
    image = bpy.data.images.load(str(path))
    pixels = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(-1, 4)
    alpha = pixels[:, 3:]
    pixels[:, :3] = pixels[:, :3] * alpha + np.array(hex_to_srgb(hex_color)) * (
        1 - alpha
    )
    pixels[:, 3] = 1.0
    image.pixels.foreach_set(pixels.ravel())
    image.save()


def cell(
    brain: bpy.types.Object,
) -> tuple[bpy.types.Object, float, float, float, Vector]:
    """Return (brain, scale, width, height, center) for placing a brain.

    The scale gives the brain unit area on screen; width and height are its
    scaled extents and center is its unscaled centre, all in the image plane.
    """
    # Vertices rather than bounding-box corners, which overstate oblique extents
    points = [v.co for v in brain.data.vertices]
    left, right = extent(points, CAMERA_RIGHT)
    bottom, top = extent(points, CAMERA_UP)
    # Equal on-screen area keeps elongated and compact brains balanced
    scale = ((right - left) * (top - bottom)) ** -0.5
    center = CAMERA_RIGHT * (left + right) / 2 + CAMERA_UP * (bottom + top) / 2
    return brain, scale, (right - left) * scale, (top - bottom) * scale, center


def arrange_in_grid(brain_rows: list[list[bpy.types.Object]]) -> tuple[float, float]:
    """Lay the rows of brains out, each centred, in the camera's image plane.

    The grid's top-left corner is at the origin. Returns its (width, height) as
    seen by the camera.
    """
    rows = [[cell(brain) for brain in brain_row] for brain_row in brain_rows]
    row_widths = [sum(c[2] for c in row) + GAP * (len(row) - 1) for row in rows]
    grid_width = max(row_widths)

    y = 0.0
    for row, row_width in zip(rows, row_widths, strict=True):
        row_height = max(c[3] for c in row)
        x = (grid_width - row_width) / 2  # centre shorter rows
        for brain, scale, width, _, center in row:
            brain.scale = (scale,) * 3
            brain.location = (
                CAMERA_RIGHT * (x + width / 2)
                - CAMERA_UP * (y + row_height / 2)
                - scale * center
            )
            x += width + GAP
        y += row_height + GAP
    return grid_width, y - GAP


def add_banner_camera(grid_width: float, grid_height: float) -> None:
    """Add an orthographic camera that centres the grid in the fixed-size render."""
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    # Scene units per pixel needed to fit the grid plus margins on both axes
    units_per_pixel = max(
        (grid_width + 2 * MARGIN) / RESOLUTION[0],
        (grid_height + 2 * MARGIN) / RESOLUTION[1],
    )

    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    # ortho_scale spans the longer side of the frame
    cam.data.ortho_scale = units_per_pixel * max(RESOLUTION)
    grid_center = CAMERA_RIGHT * grid_width / 2 - CAMERA_UP * grid_height / 2
    # Far enough back that no brain crosses the camera plane
    cam.location = grid_center + VIEW_DIRECTION * 10
    cam.rotation_euler = CAMERA_ROTATION.to_euler()


if __name__ == "__main__":
    args = script_args()
    if len(args) < 3:
        print(
            "Usage: blender --background --python scene.py -- "
            '<meshes_dir> <output_png> "<atlas> <atlas> ..." ...'
        )
        sys.exit(1)
    meshes_dir, output_png = Path(args[0]), Path(args[1])
    rows: list[list[bpy.types.Object]] = []
    for names in args[2:]:
        row: list[bpy.types.Object] = []
        for atlas in names.split():
            row += import_meshes(meshes_dir / atlas, clear=not (rows or row))
        rows.append(row)
    # One colour per brain, in reading order
    brains = [brain for row in rows for brain in row]
    for brain, hex_color in zip(brains, PALETTE, strict=False):
        set_material(brain, hex_color)

    add_banner_camera(*arrange_in_grid(rows))
    add_light(VIEW_DIRECTION)
    bpy.context.scene.render.film_transparent = True
    render(output_png)
    flatten_onto_background(output_png, BACKGROUND)
