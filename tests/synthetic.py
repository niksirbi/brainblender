"""Write small synthetic OME-Zarr volumes for tests."""

from pathlib import Path

import numpy as np
import zarr


def write_ome_zarr(
    path: Path, data: np.ndarray, scale_mm: float, levels: int = 2
) -> Path:
    """Write `data` (z, y, x) as an OME-Zarr 0.5 pyramid with `levels` levels.

    Each level halves the previous one by striding and doubles the scale.
    """
    root = zarr.open_group(path, mode="w", zarr_format=3)
    datasets = []
    for level in range(levels):
        step = 2**level
        root.create_array(f"s{level}", data=data[::step, ::step, ::step])
        datasets.append(
            {
                "path": f"s{level}",
                "coordinateTransformations": [
                    {"type": "scale", "scale": [scale_mm * step] * 3}
                ],
            }
        )
    axes = [{"name": n, "type": "space", "unit": "millimeter"} for n in "zyx"]
    root.attrs["ome"] = {
        "version": "0.5",
        "multiscales": [{"name": "/", "axes": axes, "datasets": datasets}],
    }
    return path
