"""Save processed meshes to PLY files with a JSON manifest."""

import json
from pathlib import Path

import trimesh


def write_manifest(
    output_dir: Path,
    atlas_name: str,
    species: str,
    regions: list[dict],
    processing: dict,
) -> None:
    """Write manifest.json summarizing the saved meshes.

    Parameters
    ----------
    output_dir:
        Directory containing the saved PLY files.
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


def save_meshes(
    output_dir: Path,
    atlas_name: str,
    species: str,
    meshes: list[tuple[dict, trimesh.Trimesh]],
    processing: dict,
) -> None:
    """Save all meshes to PLY and write the manifest.

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
        # Some acronyms contain "/" (e.g. layer 2/3), which isn't valid in a filename
        filename = f"{metadata['acronym'].replace('/', '_')}.ply"
        mesh.export(str(output_dir / filename))
        regions_manifest.append(
            {
                **metadata,
                "file": filename,
                "n_vertices": len(mesh.vertices),
                "n_faces": len(mesh.faces),
            }
        )

    write_manifest(output_dir, atlas_name, species, regions_manifest, processing)
