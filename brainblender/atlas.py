"""Atlas loading and region selection."""

from brainglobe_atlasapi import BrainGlobeAtlas


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
        Parent region acronym for hierarchy-based selection.
    depth:
        Hierarchy level below `children_of`; leaves above that level are
        included too. None means all descendants.

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

    if children_of:
        if depth is None:
            descendants = atlas.get_structure_descendants(children_of)
        else:
            descendants = _get_regions_at_depth(atlas, children_of, depth)
        result.update(descendants)

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
