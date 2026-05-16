# brainblender
Playground for visualising brain surface meshes in blender

## Installation

Clone the repository and install in editable mode using [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/niksirbi/brainblender.git
cd brainblender
uv sync
```

## Usage

### Print atlas metadata

```bash
uv run brainblender info eurasian_blackcap_25um
```

### Explore the region hierarchy

```bash
uv run brainblender list-regions eurasian_blackcap_25um --depth 3
```

### Export meshes

Fetch, smooth, decimate, and export region meshes as PLY files:

```bash
# Export specific regions
uv run brainblender export eurasian_blackcap_25um --regions root,HVC,RA --decimate 0.5 --smooth 3

# Export all children of a region
uv run brainblender export eurasian_blackcap_25um --children-of P --depth 1 --output ./pallium_meshes
```

This creates a directory with one `.ply` file per region and a `manifest.json` describing the export.

### Import into Blender

```bash
blender --python brainblender/blender/import_meshes.py -- ./meshes/
```

This imports all exported meshes, assigns material colors from the atlas, and groups them into a collection.

See all available [BrainGlobe atlases](https://brainglobe.info/documentation/brainglobe-atlasapi/index.html).
