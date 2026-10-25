"""Allen mouse cortical areas three levels below CTX.

Viewed obliquely from anterior-superior-right.

Run with: blender --background --python scene.py -- <meshes_dir> <output_png>
"""

import sys
from pathlib import Path

# Blender helpers aren't installed in Blender's Python, so load them from the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "brainblender/blender"))

from import_meshes import import_meshes  # noqa: E402
from scene_setup import (  # noqa: E402
    ANTERIOR,
    RIGHT,
    SUPERIOR,
    add_camera,
    add_light,
    render,
    scene_args,
    scene_bounds,
)

VIEW_DIRECTION = ANTERIOR + SUPERIOR + RIGHT  # brain → camera

if __name__ == "__main__":
    meshes_dir, output_png = scene_args()
    import_meshes(meshes_dir)
    center, radius = scene_bounds()
    add_camera(center, radius, VIEW_DIRECTION)
    add_light(VIEW_DIRECTION)
    render(output_png)
