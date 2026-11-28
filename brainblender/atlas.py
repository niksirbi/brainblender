"""Atlas loading and region selection."""

import json
from pathlib import Path

from brainglobe_atlasapi import BrainGlobeAtlas
from brainglobe_atlasapi.descriptors import (
    V3_ANNOTATION_NAME,
    V3_TEMPLATE_NAME,
    remote_url_s3,
)


def load_atlas(atlas_name: str) -> BrainGlobeAtlas:
    """Load a BrainGlobe atlas by name.

    Parameters
    ----------
    atlas_name:
        Name of the atlas (e.g. "eurasian_blackcap_25um").

    Returns
    -------
    BrainGlobeAtlas
        The loaded atlas instance.

    """
    return BrainGlobeAtlas(atlas_name, check_latest=False)


def _get_regions_at_depth(atlas: BrainGlobeAtlas, parent: str, depth: int) -> list[str]:
    """Get region acronyms `depth` levels below parent.

    Branches that end sooner contribute their leaf instead, so the result is
    the leaves of the tree `list-regions --depth` prints, covering the whole parent.
    """
    parent_id = atlas.structures[parent]["id"]
    current_level = [parent_id]
    for _ in range(depth):
        next_level: list[int] = []
        for region_id in current_level:
            children = atlas.hierarchy.children(region_id)
            if children:
                next_level.extend(child.identifier for child in children)
            else:
                next_level.append(region_id)  # leaf above `depth`
        current_level = next_level
    return [atlas.structures[rid]["acronym"] for rid in current_level]


def resolve_regions(
    atlas: BrainGlobeAtlas,
    regions: list[str] | None = None,
    children_of: str | None = None,
    depth: int | None = None,
) -> list[str]:
    """Resolve a combined region specification to a flat list of acronyms.

    Parameters
    ----------
    atlas:
        A loaded BrainGlobeAtlas instance.
    regions:
        Explicit list of region acronyms.
    children_of:
        Parent region acronym for hierarchy-based selection. Defaults to the
        root region, unless only `regions` are given.
    depth:
        Hierarchy level below `children_of`; leaves above that level are
        included too. Defaults to 1 (the direct children) when `children_of`
        is given.

    Returns
    -------
    list[str]
        Deduplicated list of region acronyms.

    """
    result: set[str] = set()

    if regions:
        for r in regions:
            atlas.structures[r]  # validate existence
            result.add(r)

    if children_of is None and (depth is not None or not regions):
        children_of = atlas.structures[atlas.hierarchy.root]["acronym"]

    if children_of:
        depth = 1 if depth is None else depth
        result.update(_get_regions_at_depth(atlas, children_of, depth))

    return sorted(result)


def get_region_metadata(atlas: BrainGlobeAtlas, acronym: str) -> dict:
    """Return metadata dict for a region.

    Parameters
    ----------
    atlas:
        A loaded BrainGlobeAtlas instance.
    acronym:
        Region acronym.

    Returns
    -------
    dict
        Keys: acronym, name, id, color_rgb, parent.

    """
    structure = atlas.structures[acronym]
    id_path = structure["structure_id_path"]
    parent_acronym = None
    if len(id_path) > 1:
        parent_id = id_path[-2]
        parent_acronym = atlas.structures[parent_id]["acronym"]

    return {
        "acronym": structure["acronym"],
        "name": structure["name"],
        "id": structure["id"],
        "color_rgb": structure["rgb_triplet"],
        "parent": parent_acronym,
    }


def levels_to_fetch(n_levels: int, finest: int) -> list[int]:
    """Return pyramid levels from the coarsest down to `finest`."""
    if not 0 <= finest < n_levels:
        raise ValueError(f"Level must be in 0..{n_levels - 1}, got {finest}")
    return list(range(n_levels - 1, finest - 1, -1))


_UM_PER_UNIT = {"millimeter": 1000.0, "micrometer": 1.0}


def level_resolutions(multiscale: dict) -> list[tuple[str, str]]:
    """Label each pyramid level of an OME-Zarr multiscale with its voxel size.

    Parameters
    ----------
    multiscale:
        One entry of the OME-Zarr ``multiscales`` list.

    Returns
    -------
    list[tuple[str, str]]
        ``(level path, voxel size)`` pairs from finest to coarsest,
        e.g. ``("s2", "50 um")``, or ``"0.519x1x0.519 um"`` for anisotropic voxels.

    """
    # Spatial axes carry a unit; a channel axis, if any, does not
    spatial = [i for i, ax in enumerate(multiscale["axes"]) if ax.get("unit")]
    unit = multiscale["axes"][spatial[0]]["unit"]
    factor, label = (_UM_PER_UNIT[unit], "um") if unit in _UM_PER_UNIT else (1, unit)
    levels = []
    for dataset in multiscale["datasets"]:
        scale = dataset["coordinateTransformations"][0]["scale"]
        sizes = [f"{round(scale[i] * factor, 6):g}" for i in spatial]
        size = sizes[0] if len(set(sizes)) == 1 else "x".join(sizes)
        levels.append((dataset["path"], f"{size} {label}"))
    return levels


def _read_multiscale(zarr_path: Path) -> dict:
    """Read the first multiscale entry of a local OME-Zarr's metadata."""
    attrs = json.loads((zarr_path / "zarr.json").read_text())["attributes"]
    return attrs["ome"]["multiscales"][0]


def _template_location(atlas: BrainGlobeAtlas) -> tuple[str, str]:
    """Return the template's storage location and file name."""
    location = atlas.metadata["annotation_set"]["template"]["location"][1:]
    return location, V3_TEMPLATE_NAME


def _annotation_location(atlas: BrainGlobeAtlas) -> tuple[str, str]:
    """Return the annotation's storage location and file name."""
    return atlas.metadata["annotation_set"]["location"][1:], V3_ANNOTATION_NAME


def pyramid_levels(atlas: BrainGlobeAtlas) -> dict[str, list[tuple[str, str]]]:
    """Return the template and annotation pyramid levels with their voxel sizes.

    Parameters
    ----------
    atlas:
        A loaded BrainGlobeAtlas instance.

    Returns
    -------
    dict[str, list[tuple[str, str]]]
        ``{"template": [...], "annotation": [...]}``, each as returned by
        `level_resolutions`.

    """
    return {
        kind: level_resolutions(_read_multiscale(atlas.root_dir / loc / name))
        for kind, (loc, name) in (
            ("template", _template_location(atlas)),
            ("annotation", _annotation_location(atlas)),
        )
    }


def _fetch_pyramid(
    atlas: BrainGlobeAtlas, location: str, name: str, finest: int
) -> Path:
    """Download OME-Zarr pyramid levels from the coarsest down to `finest`.

    Levels already on disk are skipped.
    """
    zarr_path = atlas.root_dir / location / name
    levels = level_resolutions(_read_multiscale(zarr_path))
    for level in levels_to_fetch(len(levels), finest):
        path, size = levels[level]
        if (zarr_path / path / "c").exists():  # same check the atlas API uses
            print(f"  {path} ({size}): already downloaded")
            continue
        print(f"  {path} ({size}): downloading...")
        remote = remote_url_s3.format(f"{location}/{name}/{path}/")
        atlas.fs.get(remote, str(zarr_path / path), recursive=True)
    return zarr_path


def fetch_template(atlas: BrainGlobeAtlas, finest: int) -> Path:
    """Download template pyramid levels from the coarsest down to `finest`.

    Parameters
    ----------
    atlas:
        A loaded BrainGlobeAtlas instance.
    finest:
        Finest pyramid level to download (0 = full resolution).

    Returns
    -------
    Path
        Local path of the template OME-Zarr.

    """
    return _fetch_pyramid(atlas, *_template_location(atlas), finest)


def fetch_annotation(atlas: BrainGlobeAtlas, finest: int) -> Path:
    """Download annotation pyramid levels from the coarsest down to `finest`.

    This is the label volume (one structure ID per voxel) that
    `atlas.annotation` reads.

    Parameters
    ----------
    atlas:
        A loaded BrainGlobeAtlas instance.
    finest:
        Finest pyramid level to download (0 = full resolution).

    Returns
    -------
    Path
        Local path of the annotation OME-Zarr.

    """
    return _fetch_pyramid(atlas, *_annotation_location(atlas), finest)
