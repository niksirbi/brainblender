"""Tests for mesh processing."""

import trimesh

from brainblender.mesh import decimate, decimate_many


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


def test_decimate_many_matches_serial_and_keeps_order():
    """Parallel decimation yields the same meshes, in input order."""
    meshes = [trimesh.creation.icosphere(subdivisions=n) for n in (4, 1, 5)]

    serial = list(decimate_many(meshes, max_faces=500, jobs=1))
    parallel = list(decimate_many(meshes, max_faces=500, jobs=2))

    assert [len(m.faces) for m in parallel] == [500, 80, 500]
    for a, b in zip(serial, parallel, strict=True):
        assert (a.faces == b.faces).all()
        assert (a.vertices == b.vertices).all()
