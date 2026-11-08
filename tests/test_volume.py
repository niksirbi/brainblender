"""Tests for volume preparation."""

from pathlib import Path

import numpy as np
import pytest
from synthetic import write_ome_zarr

from brainblender.volume import default_window, volume_info


def test_default_window_percentiles() -> None:
    """Window and floor are percentiles of the tissue voxels only."""
    background = np.zeros(1000)
    tissue = np.linspace(0.03, 0.5, 1000)
    lo, hi, floor = default_window(np.concatenate([background, tissue]))
    assert lo == pytest.approx(np.percentile(tissue, 2))
    assert hi == pytest.approx(np.percentile(tissue, 95))
    assert floor == pytest.approx(np.percentile(tissue, 5))


def test_default_window_rejects_empty_volume() -> None:
    """An all-background volume (e.g. not downloaded) is an error."""
    with pytest.raises(ValueError, match="empty"):
        default_window(np.zeros(100))


def test_volume_info(tmp_path: Path) -> None:
    """Info reports the level, its physical extent, and a window inside 0..1."""
    data = np.zeros((40, 20, 30), dtype=np.uint16)
    data[10:30, 5:15, 5:25] = np.arange(100, 300, 10)[:, None, None]  # 20 AP slices
    path = write_ome_zarr(tmp_path / "t.ome.zarr", data, scale_mm=0.1)
    info = volume_info(path, level=1)
    assert info["level"] == 1 and info["zarr"] == str(path)
    assert info["extent_mm"] == pytest.approx([4.0, 2.0, 3.0])
    assert 0 < info["window"][0] < info["window"][1] < 1


def test_volume_info_unknown_level_lists_available(tmp_path: Path) -> None:
    """Asking for a level the pyramid doesn't have names the valid range."""
    data = np.ones((8, 8, 8), np.uint16)
    path = write_ome_zarr(tmp_path / "t.ome.zarr", data, 0.1, levels=1)
    with pytest.raises(ValueError, match="0..0"):
        volume_info(path, level=2)
