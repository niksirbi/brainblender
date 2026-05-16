# brainblender
Visualise BrainGlobe atlas meshes in Blender.

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
uv run brainblender list-regions eurasian_blackcap_25um --depth 2
```

### Export meshes

Fetch, smooth, decimate, and export region meshes as PLY files:

```bash
# Export specific regions
uv run brainblender export eurasian_blackcap_25um --regions root,HVC,RA --decimate 0.5 --smooth 3

# Export all children of a region
uv run brainblender export eurasian_blackcap_25um --children-of root --depth 1 --output ./level1_meshes
```

This creates a directory with one `.ply` file per region and a `manifest.json` describing the export.

### Import into Blender

This step requires the `blender` command to be available in your terminal.
See the [Blender docs on launching from the command line](https://docs.blender.org/manual/en/latest/advanced/command_line/launch/index.html)
for platform-specific instructions.

```bash
blender --python brainblender/blender/import_meshes.py -- ./meshes/
```

This imports all exported meshes, assigns material colors from the atlas, and groups them into a collection.

## Examples

See the `examples/` directory for complete workflow scripts, e.g.:

```bash
bash examples/render-root-mesh.sh
```

## Resources

See all available [BrainGlobe atlases](https://brainglobe.info/documentation/brainglobe-atlasapi/index.html).
