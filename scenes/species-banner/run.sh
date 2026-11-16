#!/bin/bash
# Export the root meshes of atlases from different species and render them in a grid.
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

# One row of the banner per line, top to bottom, with atlases left to right.
# Blog posts crop the top and bottom quarters of the image, so only the middle
# row stays fully visible there.
ROWS=(
    "vfb_jrc2018u_neuropils_fly_0.519um azba_zfish_4um african_molerat_20um"
    "lambada_dev_mouse_p3_25um columbia_cuttlefish_50um eurasian_blackcap_25um allen_mouse_25um"
    "nadkarni_mri_mouselemur_91um nmt_arm_sym_macaque_250um allen_human_500um"
)

for row in "${ROWS[@]}"; do
    for atlas in $row; do
        uv run --project "$REPO_ROOT" brainblender export "$atlas" \
            --regions root \
            --output "$MESHES_DIR/$atlas"
    done
done

"$BLENDER" --background \
    --python "$SCENE_DIR/scene.py" \
    -- "$MESHES_DIR" "$RENDER_PNG" "${ROWS[@]}"
