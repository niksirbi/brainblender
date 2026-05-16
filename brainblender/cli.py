"""CLI commands for brainblender."""

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from brainblender.atlas import get_region_metadata, load_atlas, resolve_regions
from brainblender.export import export_all
from brainblender.mesh import decimate as decimate_mesh
from brainblender.mesh import normalize as normalize_mesh
from brainblender.mesh import smooth as smooth_mesh
from brainblender.mesh import to_trimesh

if TYPE_CHECKING:
    import trimesh

app = typer.Typer()


@app.command()
def info(
    atlas_name: Annotated[str, typer.Argument(help="BrainGlobe atlas name")],
) -> None:
    """Print atlas metadata and summary."""
    atlas = load_atlas(atlas_name)
    print(f"Atlas:      {atlas.atlas_name}")
    print(f"Species:    {atlas.metadata['species']}")
    print(f"Resolution: {atlas.resolution} um")
    print(f"Shape:      {atlas.shape} voxels")
    print(f"Regions:    {len(atlas.structures_list)}")


@app.command()
def list_regions(
    atlas_name: Annotated[str, typer.Argument(help="BrainGlobe atlas name")],
    depth: Annotated[int, typer.Option(help="Maximum tree depth to display")] = 2,
    root: Annotated[
        str, typer.Option(help="Root region to start the tree from")
    ] = "root",
) -> None:
    """Print region hierarchy as an indented tree."""
    atlas = load_atlas(atlas_name)

    def _print_tree(region_id: int, current_depth: int) -> None:
        structure = atlas.structures[region_id]
        acronym = structure["acronym"]
        name = structure["name"]
        indent = "  " * current_depth
        print(f"{indent}{acronym} ({name})")

        if current_depth >= depth:
            return

        children = atlas.hierarchy.children(region_id)
        for child in children:
            _print_tree(child.identifier, current_depth + 1)

    root_structure = atlas.structures[root]
    _print_tree(root_structure["id"], 0)


@app.command()
def export(
    atlas_name: Annotated[str, typer.Argument(help="BrainGlobe atlas name")],
    regions: Annotated[
        list[str] | None,
        typer.Option("--regions", "-r", help="Region acronyms to export"),
    ] = None,
    children_of: Annotated[
        str | None,
        typer.Option(help="Export children of this region"),
    ] = None,
    hierarchy_depth: Annotated[
        int | None,
        typer.Option("--depth", help="Hierarchy depth for --children-of"),
    ] = None,
    decimate_ratio: Annotated[
        float | None,
        typer.Option("--decimate", "-d", help="Decimation ratio (0.0-1.0)"),
    ] = None,
    smooth_iterations: Annotated[
        int,
        typer.Option("--smooth", "-s", help="Smoothing iterations (0=none)"),
    ] = 0,
    smooth_method: Annotated[
        str, typer.Option(help="Smoothing method: taubin, laplacian, humphrey")
    ] = "taubin",
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output directory")
    ] = Path("./meshes"),
) -> None:
    """Fetch, process, and export region meshes as PLY files."""
    atlas = load_atlas(atlas_name)

    acronyms = resolve_regions(
        atlas, regions=regions, children_of=children_of, depth=hierarchy_depth
    )
    if not acronyms:
        typer.echo("No regions matched. Specify --regions or --children-of.")
        raise typer.Exit(code=1)

    typer.echo(f"Processing {len(acronyms)} region(s) from '{atlas_name}'...")

    meshes: list[tuple[dict, trimesh.Trimesh]] = []
    for acronym in acronyms:
        typer.echo(f"  {acronym}...", nl=False)
        raw_mesh = atlas.mesh_from_structure(acronym)
        mesh = to_trimesh(raw_mesh.points, raw_mesh.cells[0].data)
        mesh = normalize_mesh(mesh, atlas.resolution, atlas.shape)

        if smooth_iterations > 0:
            mesh = smooth_mesh(mesh, iterations=smooth_iterations, method=smooth_method)  # type: ignore[arg-type]
        if decimate_ratio is not None:
            mesh = decimate_mesh(mesh, ratio=decimate_ratio)

        metadata = get_region_metadata(atlas, acronym)
        meshes.append((metadata, mesh))
        typer.echo(f" {len(mesh.vertices)} verts, {len(mesh.faces)} faces")

    processing = {
        "smoothing_iterations": smooth_iterations,
        "smoothing_method": smooth_method if smooth_iterations > 0 else None,
        "decimation_ratio": decimate_ratio,
    }
    export_all(
        output_dir=output,
        atlas_name=atlas_name,
        species=atlas.metadata["species"],
        meshes=meshes,
        processing=processing,
    )
    typer.echo(f"Exported to {output}/")
