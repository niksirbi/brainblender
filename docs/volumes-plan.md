# Volumes plan

Re-implements the volume features of PR #5 (branch `volume-scenes`) on top of
current `main`, with a volume API that mirrors the mesh API.
Delete this file once the work is merged.

## Mesh pattern to mirror

- `fetch-meshes ATLAS … -o ./meshes` writes a folder: PLY files + `manifest.json`.
- `import-meshes ./meshes` opens Blender with the folder imported
  (via `$BLENDER`, running `brainblender/blender/import_meshes.py`).
- The manifest is the contract between the two; scenes call the same
  Blender-side `import_meshes()`.

## Volume API

| Meshes | Volumes |
|---|---|
| `fetch-meshes ATLAS -o ./meshes` → `manifest.json` + PLYs | `fetch-template ATLAS --level N -o ./template` (and `fetch-annotation … -o ./annotation`) → `manifest.json` |
| `import-meshes ./meshes` | `import-volume ./template` |
| `brainblender/blender/import_meshes.py` | `brainblender/blender/import_volume.py` |

Decisions:

- `--finest` is renamed to `--level`. Fetching still downloads every level from
  the coarsest down to `--level`; the manifest records `--level` as the one to import.
- Default output folders are `./template` and `./annotation`, like `./meshes`.
- The volume `manifest.json` points at the cached OME-Zarr (it doesn't copy it) and
  records: kind (template/annotation), atlas, zarr path, level, voxel size,
  extent in mm, and for templates the default contrast window and opacity floor.
  This replaces PR #5's `prepare-volume` command and `volume.json`.
- `import-volume` loads the volume with Microscopy Nodes and places it in mesh
  space (mm, centred, X right, Y anterior, Z superior), so meshes and volumes
  can be combined in one scene.
- Annotation manifests are written from commit 1 so the format is shared;
  annotation *import* (Microscopy Nodes label volumes) is out of scope for now.

## Commits

1. **Fetch side.** `fetch-template`/`fetch-annotation` gain `--level` and
   `--output` and write the manifest. Port from `volume-scenes`:
   `brainblender/volume.py` (`default_window`, unequal y/x spacing check,
   empty-volume error), `tests/synthetic.py`, `tests/test_volume.py`.
   Add `zarr` as a direct dependency. Update README "Working with volumes".
2. **Import side.** `import-volume` CLI command plus
   `brainblender/blender/import_volume.py`, built from
   `brainblender/blender/volume_setup.py` (load, pose like meshes, look).
   Port `tests/test_volume_scene.py` (headless Blender; skips without
   Microscopy Nodes).
3. **Template-cut scene.** Port `brainblender/blender/cut.py` + `tests/test_cut.py`
   and `scenes/allen-mouse-template-cut/`, rebuilt on `import_volume()`.
4. **Smaller, independent items** (any order):
   - `fetch-template --reference` (additional reference images).
   - Save a `.blend` next to every scene render (no `.blend1` backup).
   - Pre-commit mypy hook runs `uv run mypy brainblender/`, and mypy skips
     Blender-only imports.

Dropped: PR #5's design doc under `docs/superpowers/specs/`.

## Known limitations carried over from PR #5

- Single cut plane only.
- Cut settings are validated only after the Microscopy Nodes load.
- Microscopy Nodes' slice-cube mode isn't forced to "shader".
- Computing the default window reads the whole level into memory
  (a lot for 10 µm `s0`).
