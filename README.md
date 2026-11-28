# brainblender
Visualise BrainGlobe atlas meshes and volumes in Blender.

I ([Niko Sirmpilatze](https://nikosirmpilatze.com)) am building this package
to aid me in creating reproducible illustrations for publications, websites and presentations related to the [BrainGlobe project](https://brainglobe.info/).
It is not intended as a general-purpose Blender add-on; check out
[BlenderBrain](https://github.com/ArtemKirsanov/BlenderBrain/tree/main)
if you are looking for that.

## Key features

- Explore [BrainGlobe atlases](https://brainglobe.info/documentation/brainglobe-atlasapi/index.html) and their region hierarchies on the command line.
- Export region meshes to PLY files, with configurable decimation and smoothing.
- Fetch template and annotation volumes as OME-Zarr files, up to the desired spatial resolution.
- Import meshes and volumes into Blender.
- Construct reproducible Blender scenes with camera, lighting, and render settings.

## Prerequisites and installation

### Blender

Blender must be installed separately. Download it from
[blender.org](https://www.blender.org/download/) (brainblender is tested with Blender 5.2).

You need to make the `blender` command available in your terminal.
See the [Blender docs on launching from the command line](https://docs.blender.org/manual/en/latest/advanced/command_line/launch/index.html)
for platform-specific instructions. Check it works with:

```bash
blender --version
```

If `blender` is a shell alias rather than an executable on your `PATH`,
it may work in your terminal but the [scene](#scenes) scripts won't find it.
In that case, set the `BLENDER` environment variable to the Blender executable
in your shell configuration file (e.g. `~/.zshrc` or `~/.bashrc`).
For example, on macOS:

```bash
export BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
```

### Microscopy Nodes

The [Microscopy Nodes](https://extensions.blender.org/add-ons/microscopynodes/)
extension is needed for loading volumes into Blender; you can skip this
if you are only working with meshes.

The extension can be installed from within Blender (Edit → Preferences → Get Extensions).

BrainGlobe atlases are stored as OME-Zarr 0.5 (Zarr v3),
which requires Microscopy Nodes 2.2.4 or later (Blender 4.4+).
This package is tested with Microscopy Nodes 3.1.3 on Blender 5.2.

### brainblender

Clone the repository and navigate into the folder:

```bash
git clone https://github.com/niksirbi/brainblender.git
cd brainblender
```

All CLI commands, Bash and Python scripts can be run from the root of the repository
by prepending `uv run` to each command (see examples below).
This uses [uv](https://docs.astral.sh/uv/) to automatically set up and
cache the right Python environment for you.

## Usage

There are two ways to use `brainblender`:

- **[Step by step](#step-by-step)**: run the `brainblender` CLI commands yourself to fetch and convert the atlas components you need. Then you can import them into Blender and set up the scene manually.
- **[Scenes](#scenes)**: high-level workflows that do it all in one step: prepare atlas components, set up the Blender scene (camera, lighting) and render an image. Intended for illustrations you want to regenerate reproducibly.

Scenes use the same CLI and Blender import code as the step-by-step commands, so it helps to try those first.

## Step by step

The code snippets below use two atlases as examples—`allen_mouse_50um`
and `eurasian_blackcap_25um`—but you can substitute any atlas name from the
[BrainGlobe atlas list](https://brainglobe.info/documentation/brainglobe-atlasapi/usage/atlas-details.html).

### Explore atlas region hierarchy

Show high-level atlas information:

```bash
uv run brainblender info eurasian_blackcap_25um
```

List all regions up to 2 levels below the root:

```bash
uv run brainblender list-regions eurasian_blackcap_25um --depth 2
```

List regions below a specific parent region (other than root):

```bash
uv run brainblender list-regions allen_mouse_50um --children-of grey --depth 2
```

### Working with meshes

The `brainblender export` command fetches, decimates, smooths, and saves
region meshes as PLY files.

To export meshes for specific regions:

```bash
uv run brainblender export eurasian_blackcap_25um --regions root,HVC,RA
```

To export meshes for all children of a region:

```bash
uv run brainblender export eurasian_blackcap_25um --children-of root --depth 1 --output ./level1_meshes
```

These commands create a directory with one `.ply` file per region as well as
a `manifest.json` describing the export. By default, the meshes are saved
to `./meshes/` in the current working directory, but you can change this
with the `--output` argument.

With `--children-of` and `--depth N`, the export takes the regions
`N` levels below the parent. If a given branch of the hierarchy ends sooner
than `N`, the export takes the leaf region instead (i.e. the deepest region
reached in that branch). This ensures that the whole parent region is covered
by the export.

By default, meshes with more than 100,000 faces are decimated down to that number,
and every mesh then gets 5 iterations of Taubin smoothing.
The intention is to leave light, clean meshes almost untouched
while cleaning up the dense ones.
Override these defaults with `--max-faces` (`0` turns decimation off)
and `--smooth` (`0` turns smoothing off).

Meshes are decimated in parallel, using one process per CPU core by default
(set the number of processes with the `--jobs` argument;
`--jobs 1` turns parallelisation off).

To import the exported meshes into Blender, run the following command
from the root of the repository, making sure to adjust the path to the
exported meshes (depending on your `--output` argument above):

```bash
blender --python brainblender/blender/import_meshes.py -- ./meshes/
```

This imports all exported meshes, assigns material colours from the atlas, and groups them into a collection.

### Working with volumes

The template and annotation volumes of BrainGlobe atlases are
stored as OME-Zarr volumes in
[multi-scale pyramids](https://ome-zarr.readthedocs.io/en/stable/explanation/multiscale_pyramids.html),
where `s0` is the full-resolution level, and `s1`, `s2`, etc. are downsampled levels.
`brainblender info <atlas>` lists the available levels and their voxel sizes.

Before you can import a volume into Blender with [Microscopy Nodes](https://extensions.blender.org/add-ons/microscopynodes/),
you need to fetch the appropriate OME-Zarr file metadata **and**
pre-download the voxel data at your desired resolutions. That second step is crucial;
otherwise Microscopy Nodes will show an empty volume.

The `fetch-template` and `fetch-annotation` commands are designed to do
exactly that. For example, to fetch the Allen mouse template and annotation volumes, starting from the coarsest available level down to (and including) level 2 (50 µm resolution):

```bash
uv run brainblender fetch-template allen_mouse_50um --finest 2
uv run brainblender fetch-annotation allen_mouse_50um --finest 2
```

Each command prints the path to the fetched OME-Zarr file.
BrainGlobe caches atlas data in `~/.brainglobe/brainglobe-atlasapi/` by default,
with templates under `templates/` and annotations under `annotation-sets/`,
e.g. `templates/allen_mouse-template/<version>/template.ome.zarr`.

You can load the files from the printed paths using Microscopy Nodes;
see the relevant
[Microscopy Nodes docs](https://aafkegros.github.io/MicroscopyNodes/latest/tutorials/2_loading_data/).

## Scenes

The `scenes/` directory holds complete workflows, one folder per Blender scene:

- `run.sh` fetches and exports atlas components with the `brainblender` CLI, then launches Blender with `scene.py`.
- `scene.py` runs inside Blender, sets up the scene and renders an image.

### Choosing where scene outputs go

Scenes write their outputs outside this repository, to a folder on your machine.
Choose this folder's location by setting the `BRAINBLENDER_SCENES_DIR` environment variable, or leave it unset to use the default `~/brainblender-scenes`.

If you want to keep using the same folder for all your scenes, add a line like this to your shell configuration file (e.g. `~/.zshrc` or `~/.bashrc`):

```bash
export BRAINBLENDER_SCENES_DIR="$HOME/Data/brainblender-scenes"
```

### Running a scene

```bash
bash scenes/blackcap-parcellation/run.sh
```

Available scenes:

- `blackcap-parcellation`: Eurasian blackcap regions two levels below root (major divisions and pallial subdivisions).
- `allen-mouse-parcellation`: Allen mouse grey matter regions five levels below grey, which splits the cortex into its areas (e.g. MO, SS, VIS).
- `species-banner`: whole-brain surfaces from ten atlases of different species in rows, as a 2240x1260 banner. The rows are set in `run.sh`. Colours inspired by Figure 1 of [Friedrich et al. (2026)](https://doi.org/10.64898/2026.02.13.705755).

Each scene gets its own subfolder named after the scene, e.g.
`$BRAINBLENDER_SCENES_DIR/blackcap-parcellation/`, with `meshes/` and `renders/` inside.
