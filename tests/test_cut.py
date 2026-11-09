"""Tests for volume cut and camera geometry."""

import pytest

from brainblender.blender.cut import (
    axis_extent,
    cut_position_mm,
    default_keep,
    kept_box,
    kept_interval,
    view_direction,
)


def test_reference_cut() -> None:
    """The 2026-11-08 render: A-P axis, a third in, keeping posterior."""
    pos = cut_position_mm(13.2, fraction=1 / 3)
    assert pos == pytest.approx(4.4)
    assert kept_interval(13.2, pos, "AP", default_keep("AP")) == pytest.approx(
        (4.4, 13.2)
    )
    assert view_direction("AP", "posterior") == pytest.approx((1.0, 1.5, 1.0))
    centre, _ = kept_box((13.2, 8.0, 11.4), "AP", (4.4, 13.2))
    assert centre == pytest.approx((0.0, -2.2, 0.0))


def test_view_direction_other_axes_and_flip() -> None:
    """The camera sits on the removed side, above-right unless that's the cut."""
    assert view_direction("AP", "anterior") == pytest.approx((1.0, -1.5, 1.0))
    assert view_direction("SI", "inferior") == pytest.approx((1.0, 1.0, 1.5))
    assert view_direction("LR", "left") == pytest.approx((1.5, 1.0, 1.0))


def test_mm_overrides_fraction() -> None:
    """A position in mm wins over a fraction."""
    assert cut_position_mm(13.2, fraction=0.5, mm=2.0) == 2.0


@pytest.mark.parametrize(
    "kwargs", [{"fraction": 0.0}, {"fraction": 1.2}, {"mm": 14.0}, {}]
)
def test_cut_position_out_of_range(kwargs: dict) -> None:
    """Positions outside the volume, or none at all, are rejected."""
    with pytest.raises(ValueError):
        cut_position_mm(13.2, **kwargs)


def test_axis_extent_picks_from_ap_si_lr() -> None:
    """Extents are stored (ap, si, lr) as in volume.json."""
    assert [axis_extent((13.2, 8.0, 11.4), a) for a in ("AP", "SI", "LR")] == [
        13.2,
        8.0,
        11.4,
    ]
