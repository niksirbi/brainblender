#!/bin/bash
# Render the Allen mouse template with the front third cut away.
# LEVEL picks the pyramid level (default 2 = 50 um); PREVIEW=1 renders fast.
set -euo pipefail

SCENE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCENE_DIR/../.."

# Volume data and renders live outside the repo, in a per-machine folder (see README)
DATA_DIR=${BRAINBLENDER_SCENES_DIR:-$HOME/brainblender-scenes}/$(basename "$SCENE_DIR")
VOLUME_JSON=$DATA_DIR/volume.json
RENDER_PNG=$DATA_DIR/renders/template-cut.png
LEVEL=${LEVEL:-2}

BLENDER=${BLENDER:-blender}
if ! command -v "$BLENDER" >/dev/null; then
    echo "Blender not found: put 'blender' on your PATH or set BLENDER (see README)" >&2
    exit 1
fi

uv run --project "$REPO_ROOT" brainblender prepare-volume allen_mouse_50um \
    --level "$LEVEL" \
    --output "$VOLUME_JSON"

"$BLENDER" --background --python-exit-code 1 \
    --python "$SCENE_DIR/scene.py" \
    -- "$VOLUME_JSON" "$RENDER_PNG"
