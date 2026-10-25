"""Tests for region selection."""

from types import SimpleNamespace

from treelib import Tree

from brainblender.atlas import resolve_regions


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
