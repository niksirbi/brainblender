"""Tests for CLI commands that don't need a downloaded atlas."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from brainblender.cli import IMPORT_SCRIPT, app

runner = CliRunner()


def test_import_meshes_launches_blender_with_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """import-meshes runs $BLENDER with the import script and the meshes folder."""
    meshes = tmp_path / "meshes"
    meshes.mkdir()
    (meshes / "manifest.json").write_text("{}")
    args_file = tmp_path / "args.txt"
    fake_blender = tmp_path / "fake-blender"
    fake_blender.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > {args_file}\n')
    fake_blender.chmod(0o755)
    monkeypatch.setenv("BLENDER", str(fake_blender))

    result = runner.invoke(app, ["import-meshes", str(meshes)])

    assert result.exit_code == 0, result.output
    assert args_file.read_text().split() == [
        "--python",
        str(IMPORT_SCRIPT),
        "--",
        str(meshes.resolve()),
    ]


def test_import_meshes_needs_a_manifest(tmp_path: Path) -> None:
    """A folder without manifest.json is rejected before Blender starts."""
    result = runner.invoke(app, ["import-meshes", str(tmp_path)])
    assert result.exit_code != 0
    assert "fetch-meshes" in result.output
