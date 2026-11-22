#!/bin/bash
# Export the Allen mouse grey matter regions five levels below grey and render them.
set -euo pipefail

SCENE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCENE_DIR/../.."

# Meshes and renders live outside the repo, in a per-machine folder (see README)
DATA_DIR=${BRAINBLENDER_SCENES_DIR:-$HOME/brainblender-scenes}/$(basename "$SCENE_DIR")
MESHES_DIR=$DATA_DIR/meshes
RENDER_PNG=$DATA_DIR/renders/grey.png

BLENDER=${BLENDER:-blender}
if ! command -v "$BLENDER" >/dev/null; then
    echo "Blender not found: put 'blender' on your PATH or set BLENDER (see README)" >&2
    exit 1
fi

# Regions five levels below grey, or the leaf where a branch ends sooner: the leaves of
# `brainblender list-regions allen_mouse_25um --children-of grey --depth 5`.
# For the cortex, that's the cortical areas (e.g. MO, SS, VIS).
uv run --project "$REPO_ROOT" brainblender export allen_mouse_25um \
    --children-of grey \
    --depth 5 \
    --output "$MESHES_DIR"

"$BLENDER" --background \
    --python "$SCENE_DIR/scene.py" \
    -- "$MESHES_DIR" "$RENDER_PNG"
