"""Tests for mesh processing."""

import trimesh

from brainblender.mesh import decimate


def test_decimate_caps_faces_and_stays_watertight():
    """Decimation reaches the face cap without breaking the surface."""
    sphere = trimesh.creation.icosphere(subdivisions=5)

    decimated = decimate(sphere, max_faces=1000)

    assert len(decimated.faces) <= 1000
    assert decimated.is_watertight
    assert decimated.volume > 0  # normals still point outward


def test_decimate_leaves_light_meshes_untouched():
    """Meshes at or below the cap are returned as they are."""
    sphere = trimesh.creation.icosphere(subdivisions=2)

    assert decimate(sphere, max_faces=len(sphere.faces)) is sphere
