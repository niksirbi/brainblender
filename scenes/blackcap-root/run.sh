#!/bin/bash
# Export the Eurasian blackcap root mesh and render it.
set -euo pipefail

SCENE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCENE_DIR/../.."

# Meshes and renders live outside the repo, in a per-machine folder (see README)
DATA_DIR=${BRAINBLENDER_SCENES_DIR:-$HOME/brainblender-scenes}/$(basename "$SCENE_DIR")
MESHES_DIR=$DATA_DIR/meshes
RENDER_PNG=$DATA_DIR/renders/root.png

BLENDER=${BLENDER:-blender}
if ! command -v "$BLENDER" >/dev/null; then
    echo "Blender not found: put 'blender' on your PATH or set BLENDER (see README)" >&2
    exit 1
fi

uv run --project "$REPO_ROOT" brainblender export eurasian_blackcap_25um \
    --regions root \
    --decimate 0.5 \
    --smooth 3 \
    --output "$MESHES_DIR"

"$BLENDER" --background \
    --python "$SCENE_DIR/scene.py" \
    -- "$MESHES_DIR" "$RENDER_PNG"
