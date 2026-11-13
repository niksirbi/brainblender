#!/bin/bash
# Export the root meshes of atlases from different species and render them in a row.
set -euo pipefail

SCENE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCENE_DIR/../.."

# Meshes and renders live outside the repo, in a per-machine folder (see README)
DATA_DIR=${BRAINBLENDER_SCENES_DIR:-$HOME/brainblender-scenes}/$(basename "$SCENE_DIR")
MESHES_DIR=$DATA_DIR/meshes
RENDER_PNG=$DATA_DIR/renders/banner.png

BLENDER=${BLENDER:-blender}
if ! command -v "$BLENDER" >/dev/null; then
    echo "Blender not found: put 'blender' on your PATH or set BLENDER (see README)" >&2
    exit 1
fi

# One atlas per species; the scene orders them by brain size
ATLASES=(
    mpin_zfish_1um
    columbia_cuttlefish_50um
    hoops_tawny_dragon_20um
    eurasian_blackcap_25um
    allen_mouse_25um
    allen_human_500um
)

for atlas in "${ATLASES[@]}"; do
    uv run --project "$REPO_ROOT" brainblender export "$atlas" \
        --regions root \
        --output "$MESHES_DIR/$atlas"
done

"$BLENDER" --background \
    --python "$SCENE_DIR/scene.py" \
    -- "$MESHES_DIR" "$RENDER_PNG"
