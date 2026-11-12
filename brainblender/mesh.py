"""Mesh processing: smoothing and decimation."""

import multiprocessing
import os
from collections import deque
from collections.abc import Iterable, Iterator
from concurrent.futures import Future, ProcessPoolExecutor
from typing import Literal

import numpy as np
import pymeshlab
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
    reoriented[:, 0] = -vertices[:, 2]  # Blender X = -Atlas Z (Right)
    reoriented[:, 1] = -vertices[:, 0]  # Blender Y = -Atlas X (Anterior)
    reoriented[:, 2] = -vertices[:, 1]  # Blender Z = -Atlas Y (Superior)
    mesh.vertices = reoriented
    # ASR is a left-handed frame, so this mapping is a reflection; reverse the
    # face winding to keep normals pointing outward.
    mesh.invert()
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


def decimate(mesh: trimesh.Trimesh, max_faces: int) -> trimesh.Trimesh:
    """Decimate a mesh down to at most `max_faces` faces.

    Meshes that already have `max_faces` faces or fewer are returned unchanged.
    Uses MeshLab's quadric edge collapse, which rejects collapses that would
    change the topology or flip a face, so a clean mesh stays manifold.

    Parameters
    ----------
    mesh:
        The mesh to decimate.
    max_faces:
        Maximum number of faces to keep.

    Returns
    -------
    trimesh.Trimesh
        The original mesh, or a new decimated mesh.

    """
    if len(mesh.faces) <= max_faces:
        return mesh
    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(pymeshlab.Mesh(mesh.vertices, mesh.faces))
    mesh_set.meshing_decimation_quadric_edge_collapse(
        targetfacenum=max_faces,
        preservetopology=True,
        preservenormal=True,
        # Keeps triangles well-shaped on flat areas (e.g. where the atlas
        # volume cuts the brain), which otherwise collapse into sliver fans.
        planarquadric=True,
        planarweight=0.01,
    )
    decimated = mesh_set.current_mesh()
    return to_trimesh(decimated.vertex_matrix(), decimated.face_matrix())


def decimate_many(
    meshes: Iterable[trimesh.Trimesh], max_faces: int, jobs: int = 0
) -> Iterator[trimesh.Trimesh]:
    """Decimate several meshes, running the heavy ones in parallel.

    Meshes are consumed lazily and yielded in their input order, so only a
    few raw meshes are held in memory at a time.

    Parameters
    ----------
    meshes:
        The meshes to decimate.
    max_faces:
        Maximum number of faces to keep per mesh.
    jobs:
        Number of worker processes; 0 means one per CPU core and 1 decimates
        in the calling process.

    Yields
    ------
    trimesh.Trimesh
        Each mesh, decimated where it exceeded `max_faces`.

    """
    jobs = jobs or os.cpu_count() or 1
    if jobs == 1:
        yield from (decimate(mesh, max_faces) for mesh in meshes)
        return

    pending: deque[trimesh.Trimesh | Future[trimesh.Trimesh]] = deque()
    n_futures = 0
    # MeshLab is not thread-safe, so parallel decimation needs processes;
    # spawned ones avoid forking a parent that may hold threads.
    with ProcessPoolExecutor(
        jobs, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for mesh in meshes:
            if len(mesh.faces) > max_faces:
                pending.append(pool.submit(decimate, mesh, max_faces))
                n_futures += 1
            else:
                pending.append(mesh)
            # Yield what is ready; block only once too many heavy meshes are queued
            while pending and (
                not isinstance(pending[0], Future)
                or pending[0].done()
                or n_futures > 2 * jobs
            ):
                n_futures -= isinstance(pending[0], Future)
                yield _result(pending.popleft())
        while pending:
            yield _result(pending.popleft())


def _result(mesh: trimesh.Trimesh | Future[trimesh.Trimesh]) -> trimesh.Trimesh:
    return mesh.result() if isinstance(mesh, Future) else mesh
