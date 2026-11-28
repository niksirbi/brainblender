"""Tests for region selection."""

from types import SimpleNamespace

import pytest
from treelib import Tree

from brainblender.atlas import level_resolutions, levels_to_fetch, resolve_regions


def make_atlas() -> SimpleNamespace:
    """Build a tiny atlas: root -> A (leaf), B -> B1 -> B1a, B -> B2 (leaf)."""
    tree = Tree()
    edges = [("root", None), ("A", "root"), ("B", "root"), ("B1", "B")]
    edges += [("B2", "B"), ("B1a", "B1")]
    structures = {}
    for i, (acronym, parent) in enumerate(edges):
        tree.create_node(
            acronym, i, parent=structures[parent]["id"] if parent else None
        )
        structures[acronym] = structures[i] = {"id": i, "acronym": acronym}
    return SimpleNamespace(structures=structures, hierarchy=tree)


def test_depth_includes_shallower_leaves() -> None:
    """Leaves above the requested depth stand in for their missing descendants."""
    atlas = make_atlas()
    assert resolve_regions(atlas, children_of="root", depth=1) == ["A", "B"]
    assert resolve_regions(atlas, children_of="root", depth=2) == ["A", "B1", "B2"]
    assert resolve_regions(atlas, children_of="root", depth=3) == ["A", "B1a", "B2"]


def test_levels_to_fetch_coarsest_first() -> None:
    """Fetching stops at the requested level and rejects levels out of range."""
    assert levels_to_fetch(4, 2) == [3, 2]
    assert levels_to_fetch(4, 0) == [3, 2, 1, 0]
    with pytest.raises(ValueError):
        levels_to_fetch(4, 4)


def test_level_resolutions_in_micrometres() -> None:
    """Levels are labelled in um, skipping the channel axis; anisotropy is kept."""
    mm = {"unit": "millimeter"}
    scales = {"s0": [1, 0.025, 0.025, 0.025], "s1": [1, 0.05, 0.1, 0.05]}
    multiscale = {
        "axes": [{"name": "c"}, mm, mm, mm],
        "datasets": [
            {"path": p, "coordinateTransformations": [{"scale": s}]}
            for p, s in scales.items()
        ],
    }
    assert level_resolutions(multiscale) == [("s0", "25 um"), ("s1", "50x100x50 um")]


def test_children_of_defaults_to_root_like_list_regions() -> None:
    """Without --children-of, selection starts from root, unless only --regions."""
    atlas = make_atlas()
    assert resolve_regions(atlas) == ["A", "B"]
    assert resolve_regions(atlas, depth=2) == ["A", "B1", "B2"]
    assert resolve_regions(atlas, regions=["B1"]) == ["B1"]


def test_children_of_alone_takes_direct_children() -> None:
    """--children-of without --depth fetches one level, so meshes don't overlap."""
    atlas = make_atlas()
    assert resolve_regions(atlas, children_of="B") == ["B1", "B2"]
    assert resolve_regions(atlas, children_of="B", depth=0) == ["B"]
