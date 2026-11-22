#!/bin/bash
# Export the Allen mouse cortical areas three levels below CTX, plus the major
# divisions outside the cortex, and render them.
set -euo pipefail

SCENE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCENE_DIR/../.."

# Meshes and renders live outside the repo, in a per-machine folder (see README)
DATA_DIR=${BRAINBLENDER_SCENES_DIR:-$HOME/brainblender-scenes}/$(basename "$SCENE_DIR")
MESHES_DIR=$DATA_DIR/meshes
RENDER_PNG=$DATA_DIR/renders/cortex.png

BLENDER=${BLENDER:-blender}
if ! command -v "$BLENDER" >/dev/null; then
    echo "Blender not found: put 'blender' on your PATH or set BLENDER (see README)" >&2
    exit 1
fi

# Cortical areas three levels below CTX, or the leaf where a branch ends sooner (CLA, LA, PA):
# the leaves of `brainblender list-regions allen_mouse_25um --children-of CTX --depth 3`.
# Everything else as the Allen major divisions: striatum, pallidum, thalamus,
# hypothalamus, midbrain, pons, medulla and cerebellum.
uv run --project "$REPO_ROOT" brainblender export allen_mouse_25um \
    --children-of CTX \
    --depth 3 \
    --regions STR,PAL,TH,HY,MB,P,MY,CB \
    --output "$MESHES_DIR"

"$BLENDER" --background \
    --python "$SCENE_DIR/scene.py" \
    -- "$MESHES_DIR" "$RENDER_PNG"
