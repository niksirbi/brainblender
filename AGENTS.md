# AGENTS.md

## Project overview

**brainblender** is a Python tool for visualising BrainGlobe atlas meshes in Blender. It uses the [BrainGlobe Atlas API](https://brainglobe.info/) to fetch brain region meshes and is in early development.

## Tech stack

- Python 3.11+, managed with `uv`
- CLI via `typer`
- Brain atlas data via `brainglobe-atlasapi`
- Mesh processing via `trimesh` + `fast-simplification`
- Blender import via standalone `bpy` script

## Project structure

```
brainblender/
  __init__.py        # Package init
  cli.py             # CLI subcommands: info, list-regions, export
  atlas.py           # Atlas loading and region selection (explicit + hierarchy)
  mesh.py            # Smoothing, decimation, and normalization (trimesh)
  export.py          # PLY export + manifest.json writing
  blender/
    __init__.py
    import_meshes.py # Standalone Blender script (bpy + stdlib only)
examples/            # Complete workflow scripts
pyproject.toml       # Project metadata, dependencies, and tool config
uv.lock              # Locked dependencies
.pre-commit-config.yaml  # Pre-commit hook configuration
```

## Development commands

```bash
uv run brainblender info <atlas>                     # Print atlas metadata
uv run brainblender list-regions <atlas> --depth 2   # Show region tree
uv run brainblender export <atlas> --regions root --decimate 0.5 --smooth 3  # Export pipeline
blender --python brainblender/blender/import_meshes.py -- ./meshes/  # Load into Blender
uv sync --group dev                   # Install dependencies including dev tools
uv run pre-commit install             # Set up pre-commit hooks (once after cloning)
uv run pre-commit run --all-files     # Run all hooks manually
uv run mypy brainblender/             # Type-check
uv run ruff check brainblender/       # Lint
uv run ruff format brainblender/      # Format
```

## Conventions

- Package layout: `brainblender/` (no `src/` layout)
- CLI entry point: `brainblender.cli:app` (registered in `[project.scripts]`)
- Type hints required
- Docstrings use NumPy style
- Code quality enforced via pre-commit: ruff (lint + format), mypy, codespell
- Versioning via setuptools_scm (git tags); create `git tag v<X.Y.Z>` to cut a release
