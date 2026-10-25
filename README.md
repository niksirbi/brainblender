# brainblender
Visualise BrainGlobe atlas meshes in Blender.

## Installation

### brainblender

Clone the repository and install in editable mode using [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/niksirbi/brainblender.git
cd brainblender
uv sync
```

### Blender

Blender is installed separately. If you don't have it yet, download it from
[blender.org](https://www.blender.org/download/) (brainblender is tested with Blender 4.2).

Then make the `blender` command available in your terminal.
See the [Blender docs on launching from the command line](https://docs.blender.org/manual/en/latest/advanced/command_line/launch/index.html)
for platform-specific instructions. Check it works with:

```bash
blender --version
```

## Usage

There are two ways to use `brainblender`:

- **[Step by step](#step-by-step)**: run the `brainblender` CLI commands yourself to explore an atlas and export meshes, then import them into Blender and set up a scene interactively.
- **[Scenes](#scenes)**: high-level workflows that do it all in one step: export the meshes, set up the Blender scene (camera, lighting) and render an image. Good for figures you want to regenerate reproducibly.

Scenes use the same CLI and Blender import code as the step-by-step commands, so it helps to try those first.

## Step by step

### Print atlas metadata

```bash
uv run brainblender info eurasian_blackcap_25um
```

### Explore the region hierarchy

```bash
uv run brainblender list-regions eurasian_blackcap_25um --depth 2

# Show the tree below a specific region
uv run brainblender list-regions allen_mouse_25um --children-of grey --depth 2
```

### Export meshes

Fetch, smooth, decimate, and export region meshes as PLY files:

```bash
# Export specific regions
uv run brainblender export eurasian_blackcap_25um --regions root,HVC,RA --decimate 0.5 --smooth 3

# Export all children of a region
uv run brainblender export eurasian_blackcap_25um --children-of root --depth 1 --output ./level1_meshes
```

With `--children-of` and `--depth N`, the export takes the regions `N` levels below the parent.
Where a branch ends sooner, its leaf is taken instead, so the selection matches the leaves of the tree
`list-regions --children-of <parent> --depth N` prints and covers the whole parent region.

This creates a directory with one `.ply` file per region and a `manifest.json` describing the export.

### Import into Blender

This step requires the `blender` command (see [Installation](#blender)).

```bash
blender --python brainblender/blender/import_meshes.py -- ./meshes/
```

This imports all exported meshes, assigns material colors from the atlas, and groups them into a collection.

## Scenes

The `scenes/` directory holds complete workflows, one folder per `blender` scene:

- `run.sh` fetches and exports the meshes with the `brainblender` CLI, then launches Blender with `scene.py`.
- `scene.py` runs inside Blender, sets up the scene and renders an image.

### One-time setup

Scenes write their exported meshes and renders outside the repo, to a folder on your machine.
Choose this folder's location by setting the `BRAINBLENDER_SCENES_DIR` environment variable, or leave it unset to use the default `~/brainblender-scenes`.

If you want to keep using the same folder for all your scenes, add a line like this to your shell configuration file (e.g. `~/.zshrc` or `~/.bashrc`):

```bash
export BRAINBLENDER_SCENES_DIR="$HOME/Data/brainblender-scenes"
```

Scenes launch Blender with the `blender` command (see [Installation](#blender)).
If `blender` is a shell alias or isn't on your `PATH`, scripts can't find it.
In that case, set the `BLENDER` environment variable to the Blender executable in the same file, e.g. on macOS:

```bash
export BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
```

### Running a scene

```bash
bash scenes/blackcap-root/run.sh
```

Each scene gets its own subfolder named after the scene, e.g.
`$BRAINBLENDER_SCENES_DIR/blackcap-root/`, with `meshes/` and `renders/` inside.

## Resources

See all available [BrainGlobe atlases](https://brainglobe.info/documentation/brainglobe-atlasapi/index.html).
