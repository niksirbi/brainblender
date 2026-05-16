"""Mesh processing: smoothing and decimation."""

from typing import Literal

import numpy as np
import trimesh
import trimesh.smoothing


def to_trimesh(vertices: np.ndarray, faces: np.ndarray) -> trimesh.Trimesh:
    """Convert raw vertex and face arrays to a trimesh object.

    Parameters
    ----------
    vertices:
        Vertex coordinates, shape (N, 3).
    faces:
        Triangle face indices, shape (M, 3).

    Returns
    -------
    trimesh.Trimesh
        The constructed mesh.

    """
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def smooth(
    mesh: trimesh.Trimesh,
    iterations: int = 10,
    method: Literal["taubin", "laplacian", "humphrey"] = "taubin",
) -> trimesh.Trimesh:
    """Smooth a mesh in-place.

    Parameters
    ----------
    mesh:
        The mesh to smooth.
    iterations:
        Number of smoothing iterations.
    method:
        Smoothing algorithm: 'taubin', 'laplacian', or 'humphrey'.

    Returns
    -------
    trimesh.Trimesh
        The smoothed mesh (modified in-place and returned).

    """
    if method == "taubin":
        trimesh.smoothing.filter_taubin(mesh, iterations=iterations)
    elif method == "laplacian":
        trimesh.smoothing.filter_laplacian(mesh, iterations=iterations)
    elif method == "humphrey":
        trimesh.smoothing.filter_humphrey(mesh, iterations=iterations)
    else:
        msg = f"Unknown smoothing method: {method!r}"
        raise ValueError(msg)
    return mesh


def decimate(mesh: trimesh.Trimesh, ratio: float = 0.5) -> trimesh.Trimesh:
    """Decimate a mesh to a fraction of its original face count.

    Parameters
    ----------
    mesh:
        The mesh to decimate.
    ratio:
        Target ratio of faces to keep (0.0-1.0).

    Returns
    -------
    trimesh.Trimesh
        A new decimated mesh.

    """
    return mesh.simplify_quadric_decimation(percent=ratio)
