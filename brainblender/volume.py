"""Template volume preparation for volume scenes."""

import json
from pathlib import Path

import numpy as np
import zarr

from brainblender.atlas import levels_to_fetch

# Voxels above this normalized intensity count as tissue, below as background.
TISSUE_MIN = 0.02
# Percentiles of tissue intensities giving the default contrast window
# (≈ 0.03-0.45 on the Allen mouse template) and the opacity floor.
WINDOW_PERCENTILES = (2, 95)
FLOOR_PERCENTILE = 5


def default_window(normalized: np.ndarray) -> tuple[float, float, float]:
    """Return a default contrast window and opacity floor for a volume.

    Parameters
    ----------
    normalized:
        Voxel intensities normalized to 0..1 (value / (max + 1)).

    Returns
    -------
    tuple[float, float, float]
        (lo, hi, floor): the contrast window and the opacity floor.

    """
    tissue = normalized[normalized > TISSUE_MIN]
    if tissue.size == 0:
        raise ValueError(
            "The volume is empty (no voxels above background); was its data downloaded?"
        )
    lo, hi = np.percentile(tissue, WINDOW_PERCENTILES)
    floor = min(float(np.percentile(tissue, FLOOR_PERCENTILE)), float(hi))
    return float(lo), float(hi), floor


def volume_info(zarr_path: Path, level: int) -> dict:
    """Describe one pyramid level of an OME-Zarr template for a volume scene.

    Parameters
    ----------
    zarr_path:
        Path to the template OME-Zarr (axes z, y, x = ASR, in mm).
    level:
        Pyramid level (index into the multiscale datasets).

    Returns
    -------
    dict
        Keys: zarr, level, extent_mm ([AP, SI, LR] in mm), window ([lo, hi]),
        floor.

    """
    attrs = json.loads((zarr_path / "zarr.json").read_text())["attributes"]
    datasets = attrs["ome"]["multiscales"][0]["datasets"]
    levels_to_fetch(len(datasets), level)  # validates the level
    dataset = datasets[level]
    scale = next(
        t["scale"] for t in dataset["coordinateTransformations"] if t["type"] == "scale"
    )
    data = np.asarray(zarr.open_array(zarr_path / dataset["path"], mode="r")[:])
    lo, hi, floor = default_window(data / (float(data.max()) + 1))
    return {
        "zarr": str(zarr_path),
        "level": level,
        "extent_mm": [n * s for n, s in zip(data.shape, scale, strict=True)],
        "window": [lo, hi],
        "floor": floor,
    }
