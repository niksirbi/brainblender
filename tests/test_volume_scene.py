"""Headless integration test: render the example volume scene on synthetic data.

Needs Blender with the Microscopy Nodes extension; skipped otherwise. Catches
Microscopy Nodes changes that break the volume workflow.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from synthetic import write_ome_zarr

from brainblender.volume import volume_info

BLENDER = os.environ.get("BLENDER", "blender")
SCENE = Path(__file__).parents[1] / "scenes/allen-mouse-template-cut/scene.py"


def _has_microscopy_nodes() -> bool:
    if shutil.which(BLENDER) is None:
        return False
    probe = (
        "import bpy, sys; "
        "sys.exit(0 if hasattr(bpy.types.Scene, 'MiN_input_file') else 3)"
    )
    result = subprocess.run(
        [BLENDER, "-b", "--python-expr", probe], capture_output=True, check=False
    )
    return result.returncode == 0


pytestmark = pytest.mark.skipif(
    not _has_microscopy_nodes(), reason="needs Blender with Microscopy Nodes"
)


def test_volume_scene_renders_cut_face(tmp_path: Path) -> None:
    """The cut face shows a dark band in bright tissue; .blend and cache saved."""
    data = np.full((48, 32, 40), 1, dtype=np.uint16)  # z=AP, y=SI, x=LR
    zz, yy, xx = np.ogrid[:48, :32, :40]
    inside = ((zz - 24) / 22) ** 2 + ((yy - 16) / 14) ** 2 + ((xx - 20) / 18) ** 2 < 1
    data[inside] = 300
    data[inside & (abs(yy - 16) < 3)] = 60  # dark "white matter" sheet
    zarr_path = write_ome_zarr(tmp_path / "t.ome.zarr", data, scale_mm=0.1)
    json_path = tmp_path / "volume.json"
    # Two-valued data puts the default floor (5th percentile) right on the sheet,
    # hiding it; real templates have a spread. Pin the floor below the sheet.
    info = {**volume_info(zarr_path, level=0), "floor": 0.05}
    json_path.write_text(json.dumps(info))
    png = tmp_path / "renders" / "out.png"

    subprocess.run(
        [BLENDER, "-b", "--python-exit-code", "1", "--python", str(SCENE)]
        + ["--", str(json_path), str(png)],
        env={**os.environ, "PREVIEW": "1"},
        check=True,
        timeout=300,
    )

    assert png.exists() and png.with_suffix(".blend").exists()
    assert list((tmp_path / "cache").rglob("*.vdb"))  # cache kept with the scene
    pixels = np.asarray(Image.open(png).convert("L"), dtype=float) / 255
    background = np.median(pixels[:5, :5])
    brain = pixels[pixels > background + 0.05]
    assert brain.size > 0.02 * pixels.size  # something rendered
    assert np.percentile(brain, 95) - np.percentile(brain, 5) > 0.25  # band visible
