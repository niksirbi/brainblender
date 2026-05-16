"""CLI commands for brainblender."""

import meshio
import typer
from brainglobe_atlasapi import BrainGlobeAtlas

app = typer.Typer()


def fetch_region_mesh(atlas: BrainGlobeAtlas, region: str | int) -> meshio.Mesh:
    """Return the mesh of a brain region as a meshio.Mesh object.

    Parameters
    ----------
    atlas:
        A BrainGlobeAtlas instance.
    region:
        Region acronym (e.g. "HVC") or integer region ID (e.g. 596).

    Returns
    -------
    meshio.Mesh
        The region mesh with vertices and triangle faces.

    """
    return atlas.mesh_from_structure(region)


@app.command()
def main(
    atlas_name: str = typer.Argument(
        ..., help="BrainGlobe atlas name, e.g. 'eurasian_blackcap_25um'"
    ),
):
    """Print metadata and root mesh statistics for a BrainGlobe atlas."""
    print(f"Loading atlas '{atlas_name}'...")
    atlas = BrainGlobeAtlas(atlas_name, check_latest=False)

    print(f"\nAtlas:      {atlas.atlas_name}")
    print(f"Species:    {atlas.metadata['species']}")
    print(f"Resolution: {atlas.resolution} um")
    print(f"Shape:      {atlas.shape} voxels")
    print(f"Regions:    {len(atlas.structures_list)}")

    root_mesh = fetch_region_mesh(atlas, "root")
    num_vertices = len(root_mesh.points)
    num_faces = len(root_mesh.cells[0].data)
    print(f"Root mesh:   {num_vertices} vertices, {num_faces} faces")
