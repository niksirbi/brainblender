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

```bash
uv run brainblender <atlas_name>
```

For example:

```bash
uv run brainblender eurasian_blackcap_25um
```

This prints metadata and root mesh statistics for the given [BrainGlobe atlas](https://brainglobe.info/documentation/brainglobe-atlasapi/index.html).
