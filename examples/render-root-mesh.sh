#!/bin/bash

MESHES_DIR=$HOME/Data/brainblender-meshes
ATLAS_NAME=eurasian_blackcap_25um
ATLAS_MESHES=$MESHES_DIR/$ATLAS_NAME/

mkdir -p "$MESHES_DIR"/$ATLAS_NAME

uv run brainblender export "$ATLAS_NAME" \
    --regions root \
    --decimate 0.5 \
    --smooth 3 \
    --output "$ATLAS_MESHES"

/Applications/Blender.app/Contents/MacOS/Blender \
    --python brainblender/blender/import_meshes.py \
    -- "$ATLAS_MESHES"
