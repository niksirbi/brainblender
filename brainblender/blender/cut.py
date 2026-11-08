"""Cut-plane and camera geometry for volume scenes (stdlib only, no bpy).

Blender space as for exported meshes: mm, centred on the volume,
X = right, Y = anterior, Z = superior. Cut positions are measured from the
anterior, superior or right end of the volume.
"""

import math
from typing import Literal

Axis = Literal["AP", "SI", "LR"]
Vec = tuple[float, float, float]

# (near end, far end) per axis; positions are measured from the near end.
SIDES: dict[str, tuple[str, str]] = {
    "AP": ("anterior", "posterior"),
    "SI": ("superior", "inferior"),
    "LR": ("right", "left"),
}
# Blender index of each axis, and its position in (ap, si, lr) extents.
_BLENDER_INDEX = {"LR": 0, "AP": 1, "SI": 2}
_EXTENT_INDEX = {"AP": 0, "SI": 1, "LR": 2}
# How much more the camera faces the cut than it looks along the other axes.
CUT_FACING_WEIGHT = 1.5


def default_keep(axis: Axis) -> str:
    """Return the side kept by default: posterior, inferior or left."""
    return SIDES[axis][1]


def cut_position_mm(
    extent_mm: float, fraction: float | None = None, mm: float | None = None
) -> float:
    """Return the cut position in mm from the near end; `mm` overrides `fraction`."""
    if mm is not None:
        position = mm
    elif fraction is not None:
        position = fraction * extent_mm
    else:
        raise ValueError("Give the cut position as a fraction or in mm")
    if not 0 < position < extent_mm:
        raise ValueError(
            f"Cut at {position:g} mm is outside the volume (0-{extent_mm:g} mm)"
        )
    return position


def kept_interval(
    extent_mm: float, position_mm: float, axis: Axis, keep: str
) -> tuple[float, float]:
    """Return the kept span along `axis`, in mm from its near end."""
    near, far = SIDES[axis]
    if keep == far:
        return position_mm, extent_mm
    if keep == near:
        return 0.0, position_mm
    raise ValueError(f"Can't keep '{keep}' when cutting {axis}; use {near} or {far}")


def view_direction(axis: Axis, keep: str) -> Vec:
    """Return the camera direction (volume → camera) facing the cut obliquely.

    The camera is on the removed side, so the kept part is behind the cut face.
    """
    if keep not in SIDES[axis]:
        raise ValueError(f"Can't keep '{keep}' when cutting {axis}")
    sign = 1.0 if keep == default_keep(axis) else -1.0
    direction = [1.0, 1.0, 1.0]  # right + anterior + superior
    direction[_BLENDER_INDEX[axis]] = sign * CUT_FACING_WEIGHT
    return (direction[0], direction[1], direction[2])


def kept_box(
    extent_mm: Vec, axis: Axis, interval: tuple[float, float]
) -> tuple[Vec, float]:
    """Return the centre (Blender space) and bounding radius of the kept part.

    `extent_mm` is (ap, si, lr) as in volume.json.
    """
    sizes = [extent_mm[_EXTENT_INDEX[a]] for a in ("LR", "AP", "SI")]  # X, Y, Z
    centre = [0.0, 0.0, 0.0]
    i = _BLENDER_INDEX[axis]
    lo, hi = interval
    centre[i] = sizes[i] / 2 - (lo + hi) / 2  # near end is the + side
    sizes[i] = hi - lo
    radius = math.sqrt(sum(s * s for s in sizes)) / 2
    return (centre[0], centre[1], centre[2]), radius
