"""Volume scene helpers: load a template with Microscopy Nodes, then pose, style, cut.

Runs inside Blender (bpy + stdlib only). Microscopy Nodes does the OME-Zarr
loading; these helpers rely on the objects and node names it creates, and fail
with a clear error if a Microscopy Nodes update renames them.
"""

from pathlib import Path
from typing import Any

import bpy
from cut import Axis
from import_meshes import clear_default_scene
from mathutils import Matrix

TESTED_MIN_VERSION = "3.1.3"
# Volume density per Blender unit (1 unit = 1 mm): opaque within about a voxel,
# so the cut face reads as a flat section.
ALPHA_MULTIPLIER = 100.0
# 0 = pure emission (no absorption: glows through and blows out),
# 1 = pure scattering (dim and flat). In between: brightness follows intensity
# and absorption stops the view at the cut face.
EMISSION_SCATTERING = 0.3
# Opacity ramps up from 0 at the floor to near-opaque at floor + this
# (normalized intensity). A hard on/off edge shows voxel layers as rings on
# the brain's outer surface; a ramp this wide removes most of them.
EDGE_SOFTNESS = 0.1
BACKGROUND = (0.02, 0.02, 0.02, 1.0)

# Microscopy Nodes places the volume with local x = right→left,
# y = superior→inferior, z = anterior→posterior (mm). This rotation maps it to
# mesh space: X = right, Y = anterior, Z = superior.
_MIN_TO_MESH = Matrix(((-1, 0, 0, 0), (0, 0, -1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
# Local slice-cube axis for each cut axis.
_LOCAL_INDEX = {"LR": 0, "SI": 1, "AP": 2}


def _require(collection: Any, name: str, kind: str) -> Any:
    """Look up a Microscopy Nodes item by name, failing clearly if it's gone."""
    item = collection.get(name)
    if item is None:
        raise RuntimeError(
            f"Microscopy Nodes {kind} '{name}' not found (brainblender is tested "
            f"with Microscopy Nodes {TESTED_MIN_VERSION})"
        )
    return item


def _min_preferences() -> bpy.types.AddonPreferences:
    """Return the Microscopy Nodes add-on preferences."""
    for name, addon in bpy.context.preferences.addons.items():
        if name.split(".")[-1] == "microscopynodes":
            return addon.preferences
    raise RuntimeError(
        "Microscopy Nodes is not enabled in Blender "
        f"(brainblender is tested with Microscopy Nodes {TESTED_MIN_VERSION})"
    )


def load_volume(zarr_path: Path, level: int, cache_dir: Path) -> bpy.types.Object:
    """Load one pyramid level of an OME-Zarr template with Microscopy Nodes.

    Parameters
    ----------
    zarr_path:
        Local OME-Zarr template (its data must already be downloaded).
    level:
        Pyramid level to load.
    cache_dir:
        Where Microscopy Nodes writes its VDB files; kept with the scene so a
        saved .blend still finds them.

    Returns
    -------
    bpy.types.Object
        The Microscopy Nodes holder object, parent of the volume.

    """
    clear_default_scene()
    prefs = _min_preferences()
    prefs.cache_option = "PATH"  # this session only; preferences aren't saved
    prefs.cache_path = str(cache_dir)
    scene = bpy.context.scene
    scene.MiN_remake = True  # never reuse VDBs from an earlier (maybe empty) load
    scene.MiN_input_file = str(zarr_path)
    scene.MiN_selected_array_option = str(level)
    channel = scene.MiN_channelList[0]
    channel.volume, channel.surface, channel.emission = True, False, False
    if bpy.ops.microscopynodes.load_background() != {"FINISHED"}:
        raise RuntimeError(f"Microscopy Nodes failed to load {zarr_path}")
    _require(bpy.data.objects, "axes", "object").hide_render = True
    return _require(bpy.data.objects, zarr_path.name, "object")


def pose_like_meshes(
    holder: bpy.types.Object, extent_mm: tuple[float, float, float]
) -> None:
    """Place the volume in mesh space: mm, centred, X right, Y anterior, Z superior.

    `extent_mm` is (ap, si, lr) as in volume.json.
    """
    ap, si, lr = extent_mm
    holder.matrix_world = Matrix.Translation((lr / 2, ap / 2, si / 2)) @ _MIN_TO_MESH


def set_look(
    window: tuple[float, float],
    floor: float,
    color: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> None:
    """Apply the volume look: a black → `color` ramp over the contrast `window`.

    Voxels below `floor` are transparent; opacity ramps up over EDGE_SOFTNESS
    above it, then stays nearly constant so the cut face reads flat.
    """
    volume = _require(bpy.data.objects, "volume", "object")
    nodes = volume.material_slots[0].material.node_tree.nodes

    lut = _require(nodes, "[color_lut_ch_id0]", "node").color_ramp.elements
    while len(lut) > 1:
        lut.remove(lut[-1])
    lut[0].position, lut[0].color = 0.0, (0.0, 0.0, 0.0, 1.0)
    lut.new(1.0).color = (*color, 1.0)

    contrast = _require(nodes, "[contrast_limits_ch_id0]", "node").color_ramp.elements
    contrast[0].position, contrast[1].position = window
    # Opacity stays below 1: Microscopy Nodes drops voxels whose alpha is exactly 1.
    alpha = _require(nodes, "[alpha_limits_ch_id0]", "node").color_ramp.elements
    while len(alpha) > 2:
        alpha.remove(alpha[-1])
    alpha[0].position, alpha[0].color = floor, (0.0, 0.0, 0.0, 0.0)
    alpha[1].position, alpha[1].color = 1.0, (0.0, 0.0, 0.0, 0.99)
    alpha.new(min(floor + EDGE_SOFTNESS, 0.999)).color = (0.0, 0.0, 0.0, 0.98)

    transparency = _require(nodes, "[volume_alpha_ch_id0]", "node").inputs
    _require(transparency, "Alpha Mode", "input").default_value = "Linear Alpha"
    _require(transparency, "Alpha Multiplier", "input").default_value = ALPHA_MULTIPLIER
    shading = _require(nodes, "[microscopy_shading_ch_id0]", "node").inputs
    _require(
        shading, "Emission / Scattering", "input"
    ).default_value = EMISSION_SCATTERING

    scene = bpy.context.scene
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = BACKGROUND
    scene.view_settings.view_transform = "Standard"
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.volume_step_rate = 1.0  # coarser steps under-sample dense tissue


def cut_volume(axis: Axis, interval: tuple[float, float]) -> None:
    """Keep only `interval` (mm from the near end) along `axis`."""
    slice_cube = _require(bpy.data.objects, "slice cube", "object")
    i = _LOCAL_INDEX[axis]
    lo, hi = interval
    slice_cube.location[i] = (lo + hi) / 2
    slice_cube.scale[i] = (hi - lo) / 2


def set_quality(preview: bool) -> None:
    """Choose fast preview or full-quality final render settings."""
    scene = bpy.context.scene
    scene.render.resolution_percentage = 50 if preview else 100
    scene.cycles.samples = 16 if preview else 128
    scene.cycles.use_adaptive_sampling = not preview
    scene.cycles.use_denoising = True
