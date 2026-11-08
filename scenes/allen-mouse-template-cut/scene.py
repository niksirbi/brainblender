"""Allen mouse template, front third cut away along the anterior-posterior axis.

The camera looks obliquely at the coronal cut face from anterior-superior-right.

Run with: blender --background --python scene.py -- <volume.json> <output_png>
Set PREVIEW=1 for a fast, low-quality render.
"""

import json
import os
import sys
from pathlib import Path

from mathutils import Vector

# Blender helpers aren't installed in Blender's Python, so load them from the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "brainblender/blender"))

from cut import (  # noqa: E402
    axis_extent,
    cut_position_mm,
    default_keep,
    kept_box,
    kept_interval,
    view_direction,
)
from scene_setup import add_camera, add_light, render, scene_args  # noqa: E402
from volume_setup import (  # noqa: E402
    cut_volume,
    load_volume,
    pose_like_meshes,
    set_look,
    set_quality,
)

CUT_AXIS = "AP"  # AP, SI or LR
CUT_FRACTION = 1 / 3  # from the anterior / superior / right end
CUT_MM = None  # overrides CUT_FRACTION when set
KEEP = None  # None keeps posterior / inferior / left
WINDOW = (0.03, 0.45)  # contrast window; None uses the template's default
COLOR = (1.0, 1.0, 1.0)  # brightest tissue colour; the ramp starts at black
VIEW_DIRECTION = None  # brain → camera; None looks obliquely at the cut face

if __name__ == "__main__":
    volume_json, output_png = scene_args()
    info = json.loads(volume_json.read_text())
    extent = tuple(info["extent_mm"])

    holder = load_volume(
        Path(info["zarr"]), info["level"], output_png.parents[1] / "cache"
    )
    pose_like_meshes(holder, extent)
    set_look(WINDOW or tuple(info["window"]), info["floor"], COLOR)

    keep = KEEP or default_keep(CUT_AXIS)
    length = axis_extent(extent, CUT_AXIS)
    interval = kept_interval(
        length, cut_position_mm(length, CUT_FRACTION, CUT_MM), CUT_AXIS, keep
    )
    cut_volume(CUT_AXIS, interval)

    center, radius = kept_box(extent, CUT_AXIS, interval)
    direction = Vector(VIEW_DIRECTION or view_direction(CUT_AXIS, keep))
    set_quality(preview=os.environ.get("PREVIEW") == "1")
    add_camera(Vector(center), radius, direction)
    add_light(direction)
    render(output_png)
