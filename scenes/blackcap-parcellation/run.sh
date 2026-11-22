#!/bin/bash
# Export the Eurasian blackcap regions two levels below root and render them.
set -euo pipefail

SCENE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCENE_DIR/../.."

# Meshes and renders live outside the repo, in a per-machine folder (see README)
DATA_DIR=${BRAINBLENDER_SCENES_DIR:-$HOME/brainblender-scenes}/$(basename "$SCENE_DIR")
MESHES_DIR=$DATA_DIR/meshes
RENDER_PNG=$DATA_DIR/renders/parcellation.png

BLENDER=${BLENDER:-blender}
if ! command -v "$BLENDER" >/dev/null; then
    echo "Blender not found: put 'blender' on your PATH or set BLENDER (see README)" >&2
    exit 1
fi

# Regions two levels below root, or the leaf where a branch ends sooner: the leaves of
# `brainblender list-regions eurasian_blackcap_25um --children-of root --depth 2`.
# Deeper levels pick small nuclei that leave holes in their parent regions.
uv run --project "$REPO_ROOT" brainblender export eurasian_blackcap_25um \
    --children-of root \
    --depth 2 \
    --output "$MESHES_DIR"

"$BLENDER" --background \
    --python "$SCENE_DIR/scene.py" \
    -- "$MESHES_DIR" "$RENDER_PNG"
