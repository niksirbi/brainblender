"""Mesh processing: smoothing and decimation."""

from typing import Literal

import numpy as np
import trimesh
import trimesh.smoothing


def normalize(
    mesh: trimesh.Trimesh,
    resolution: tuple[float, ...],
    shape: tuple[int, ...],
) -> trimesh.Trimesh:
    """Normalize mesh coordinates from atlas space to mm, centered at origin.

    Atlas meshes from BrainGlobe have coordinates in micrometers
    (voxel index x resolution). This converts to millimeters and centers
    the mesh relative to the atlas volume center.

    Parameters
    ----------
    mesh:
        Mesh with coordinates in micrometers.
    resolution:
        Atlas voxel resolution in micrometers per axis.
    shape:
        Atlas volume shape in voxels per axis.

    Returns
    -------
    trimesh.Trimesh
        The mesh with coordinates in mm, centered at origin.

    """
    atlas_center_um = np.array(shape) * np.array(resolution) / 2.0
    vertices = (mesh.vertices - atlas_center_um) / 1000.0

    # Reorient from BrainGlobe ASR (X=A→P, Y=S→I, Z=R→L)
    # to Blender convention (X=right, Y=forward, Z=up)
    reoriented = np.empty_like(vertices)
    reoriented[:, 0] = vertices[:, 2]  # Blender X = Atlas Z
    reoriented[:, 1] = -vertices[:, 0]  # Blender Y = -Atlas X (Anterior)
    reoriented[:, 2] = -vertices[:, 1]  # Blender Z = -Atlas Y (Superior)
    mesh.vertices = reoriented
    return mesh


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
