# AGENTS.md

## Project overview

**brainblender** is a Python tool for visualising brain surface meshes in Blender. It uses the [BrainGlobe Atlas API](https://brainglobe.info/) to fetch brain region meshes and is in early development (v0.1.0).

## Tech stack

- Python 3.11+, managed with `uv`
- CLI via `typer`
- Brain atlas data via `brainglobe-atlasapi`
- Mesh handling via `meshio`
- Visualization via `napari` with PyQt6

## Project structure

```
brainblender/        # Python package
  __init__.py        # Package init
  cli.py             # CLI commands and mesh-fetching logic
pyproject.toml       # Project metadata, dependencies, and tool config
uv.lock              # Locked dependencies
.pre-commit-config.yaml  # Pre-commit hook configuration
```

## Development commands

```bash
uv run brainblender <atlas_name>      # Run the CLI (e.g. 'eurasian_blackcap_25um')
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
