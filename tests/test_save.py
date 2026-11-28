"""Tests for saving meshes."""

import json
from pathlib import Path

import trimesh

from brainblender.save import save_meshes


def test_save_meshes_handles_slash_in_acronym(tmp_path: Path) -> None:
    """A "/" in an acronym (e.g. layer 2/3) doesn't end up in the file path."""
    mesh = trimesh.creation.box()
    save_meshes(tmp_path, "atlas", "species", [({"acronym": "MO2/3"}, mesh)], {})

    region = json.loads((tmp_path / "manifest.json").read_text())["regions"][0]
    assert region["acronym"] == "MO2/3"
    assert (tmp_path / region["file"]).is_file()
