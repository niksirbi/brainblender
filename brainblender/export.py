"""Export processed meshes to PLY files with a JSON manifest."""

import json
from pathlib import Path

import trimesh


def export_mesh(mesh: trimesh.Trimesh, path: Path) -> None:
    """Export a single mesh to PLY format.

    Parameters
    ----------
    mesh:
        The mesh to export.
    path:
        Output file path (should end in .ply).

    """
    mesh.export(str(path))


def write_manifest(
    output_dir: Path,
    atlas_name: str,
    species: str,
    regions: list[dict],
    processing: dict,
) -> None:
    """Write manifest.json summarizing the exported meshes.

    Parameters
    ----------
    output_dir:
        Directory containing the exported PLY files.
    atlas_name:
        Name of the source atlas.
    species:
        Species name from atlas metadata.
    regions:
        List of region metadata dicts (must include 'file', 'n_vertices',
        'n_faces' in addition to atlas metadata fields).
    processing:
        Dict describing processing parameters applied.

    """
    manifest = {
        "atlas": atlas_name,
        "species": species,
        "processing": processing,
        "regions": regions,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))


def export_all(
    output_dir: Path,
    atlas_name: str,
    species: str,
    meshes: list[tuple[dict, trimesh.Trimesh]],
    processing: dict,
) -> None:
    """Export all meshes to PLY and write the manifest.

    Parameters
    ----------
    output_dir:
        Output directory (created if it doesn't exist).
    atlas_name:
        Name of the source atlas.
    species:
        Species name from atlas metadata.
    meshes:
        List of (region_metadata, processed_mesh) tuples.
    processing:
        Dict describing processing parameters applied.

    """
    output_dir.mkdir(parents=True, exist_ok=True)

    regions_manifest: list[dict] = []
    for metadata, mesh in meshes:
        filename = f"{metadata['acronym']}.ply"
        export_mesh(mesh, output_dir / filename)
        regions_manifest.append(
            {
                **metadata,
                "file": filename,
                "n_vertices": len(mesh.vertices),
                "n_faces": len(mesh.faces),
            }
        )

    write_manifest(output_dir, atlas_name, species, regions_manifest, processing)
