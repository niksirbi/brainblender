# Volume scenes: design

Date: 2026-11-08

## Intent

Make figures of an atlas template volume, cut open by a plane so the
inside shows on the cut face, and invoke them the same way mesh renders are
invoked today: a `scenes/<name>/` folder whose `run.sh` fetches data and
launches Blender headless with a `scene.py` built from shared helpers.

The reference result is the render produced interactively on 2026-11-08:
Allen mouse template at s2, posterior two-thirds kept, viewed from
anterior-superior-right, white matter clearly darker than grey matter on
the cut face. Getting there by hand took many shader experiments; the
point of this work is that those lessons become defaults, and a new figure
is a few lines of configuration.

## Goals

- A scene folder can render a cut template volume with only these choices:
  - **template**: atlas, plus optionally one of the atlas's additional
    references (other imaging modalities). Both must work.
  - **pyramid level** of the OME-Zarr (e.g. s2 for iterating, s1 for a final).
  - **cut**: one plane, perpendicular to one anatomical axis
    (anterior-posterior, superior-inferior, left-right). Position given as a
    fraction of the volume along that axis (e.g. `1/3`), with an optional
    override in millimetres. Which side is kept is selectable; defaults are
    posterior, inferior, and left (for the A-P, S-I, L-R axis respectively).
  - **contrast window** `(lo, hi)` as actual numbers (see Look). When not set,
    a percentile-based default is computed from that template's own data.
  - **colormap**: default black-to-white.
  - **view direction**: derived from the cut by default (user's request):
    the camera looks at the cut face obliquely, from the removed side, so the
    kept part is behind the face. Rule: `1.5 * n + (the two other default
    directions)`, where `n` is the unit cut normal pointing from the kept
    part to the removed side, and the other default directions are those of
    SUPERIOR, RIGHT, ANTERIOR not on the cut axis. E.g. A-P cut keeping
    posterior gives `1.5*ANTERIOR + SUPERIOR + RIGHT` (the reference view);
    keeping anterior flips only `n`. An explicit `VIEW_DIRECTION` (as in mesh
    scenes) overrides it. The 1.5 weight is a starting point to tune against
    the reference render.
  - **quality**: a fast preview and a full-quality final, switchable without
    editing the scene.
- `fetch-template` can fetch an additional reference, not only the main
  template.
- A lightweight pytest integration test runs the volume workflow headless in
  Blender with Microscopy Nodes on small synthetic data, so a Microscopy
  Nodes update that breaks the workflow is caught.
- One example scene reproducing the reference result.

## Non-goals

- More than one cut plane (corner cutaways, wedges). Single plane only for now.
- Isosurfaces. The look is volume only.
- High-level "contrast/brightness" knobs. The user sets the window numbers.
- Annotation (label) volumes in scenes.
- Combining meshes and volumes in one scene (but see the alignment decision
  below, which keeps that door open).

## Anti-goals

- Re-implementing OME-Zarr parsing or VDB conversion. Microscopy Nodes does
  loading; brainblender must not grow its own reader to maintain.
- Silent breakage: if Microscopy Nodes internals change, the workflow must
  fail loudly with a clear message, never render an empty or wrong image.
- Exposing the shader internals that cost time to discover (below). They are
  fixed defaults, not options.

## Constraints and context

- Microscopy Nodes 3.1.3 on Blender 5.2.3 is the tested combination. It is a
  Blender extension the user installs; brainblender does not install it.
- Microscopy Nodes is driven headless by setting scene properties and calling
  `bpy.ops.microscopynodes.load_background()`:
  `scene.MiN_input_file` (zarr path), `scene.MiN_selected_array_option`
  (pyramid level index as a string, e.g. `"2"`), and per channel
  `scene.MiN_channelList[0]` fields `volume`, `surface`, `emission`, `cmap`,
  `single_color`. It creates objects named `template.ome.zarr` (holder),
  `volume`, `slice cube`, `axes`.
- Microscopy Nodes caches converted VDBs in its cache folder keyed by input
  path and reuses them. A zarr whose chunks were not downloaded yet loads as
  all zeros and that empty cache then sticks. So data must be fetched
  (`fetch-template`) before loading.
- Modifier inputs in Blender 5 are set via
  `modifier.properties.inputs.<identifier>.value`, not `modifier[...]`.
- BrainGlobe additional references are stored like the template:
  `templates/<name>/<version>/template.ome.zarr`, listed in the atlas
  metadata under `additional_references` (each with a `location`).

## Look: the fixed recipe

Learned on 2026-11-08; these are defaults baked into the helper, not options.
Node names are those Microscopy Nodes 3.1.3 creates in the volume material.

| Setting | Value | Why |
|---|---|---|
| Channel | volume on, surface off, emission off at load | |
| Colormap (`[color_lut_ch_id0]`) | black → white ramp (option) | single colour gives no contrast |
| Contrast limits (`[contrast_limits_ch_id0]`) | the user's window `(lo, hi)` | |
| Alpha limits (`[alpha_limits_ch_id0]`) | floor ~0.05, top **exactly 1.0** | the add-on drops voxels whose alpha is exactly 1, so the ramp must not saturate earlier |
| Alpha Mode (`[volume_alpha_ch_id0]`) | `Constant Alpha` | equal density everywhere gives a flat section; linear alpha makes dark white matter recess |
| Alpha Multiplier | opaque within ~1 voxel (1000 at the add-on's default 0.1 scale; rescale if the volume scale changes) | |
| Emission / Scattering (`[microscopy_shading_ch_id0]`) | 0.3 | pure emission has no absorption and blows out; pure scattering is dim and flat |
| Cycles `volume_step_rate` | 1.0, preview and final | 4 under-samples dense tissue and causes ghosting |
| World background | near-black (0.02) | the add-on sets white when emission is off |
| View transform | Standard | |
| Default cube, axes object | removed / hidden from render | the default cube encloses the volume |

Contrast window units: Microscopy Nodes' normalized 0–1 intensity, i.e.
roughly raw value / data max. On the Allen template s2, 0.03–0.45 is the
user's chosen window (white matter median ≈ 0.09, grey matter ≈ 0.29).

Quality presets (step rate 1 in both):
- preview: 50 % resolution, 16 samples, denoise (≈ 15 s for the reference scene)
- final: 100 % resolution, 128 samples adaptive, denoise (≈ 5 min)

## Decisions taken

- Microscopy Nodes does all OME-Zarr parsing and conversion (user's call).
- brainblender owns the look and the cut on top of what Microscopy Nodes
  creates, in a new Blender-side helper module next to `scene_setup.py`
  (bpy + stdlib only, like the existing helpers).
- The cut uses Microscopy Nodes' own slice cube object (it clips in the
  shader); the helper positions and scales it.
- Default contrast window when none is given: computed from percentiles of
  the template's non-background voxels, chosen so the Allen template gives
  roughly the user's 0.03–0.45.
- Pyramid level is exposed and passed both to `fetch-template --finest` and
  to the Microscopy Nodes load.
- Each scene run also saves the `.blend` file next to the render (same name,
  `.blend` extension) so the scene can be opened and tweaked by hand. It is
  saved after setup, before rendering, with the quality preset that was used.
  This applies to the existing mesh scenes too (user's call): it goes in the
  shared `scene_setup.render` helper so every scene gets it.
- The helper re-poses the Microscopy Nodes holder object into
  the same space as exported meshes, i.e. the same normalisation as
  `brainblender.mesh.normalize` (mm, centred on the atlas volume centre,
  BrainGlobe ASR reoriented to Blender X = right, Y = anterior,
  Z = superior) (user's call). Microscopy Nodes places it
  with X = left, Y = inferior, Z = posterior at 0.1 units per mm; the mapping
  X = −x, Y = −z, Z = −y is a proper rotation, plus a scale and translation.
  This lets the existing `RIGHT/ANTERIOR/SUPERIOR` constants, `add_camera`,
  and `add_light` work unchanged, and keeps meshes + volume in one scene
  possible later. Density (Alpha Multiplier) must be rescaled to match.
- **My call:** scene configuration follows the mesh-scene pattern: atlas,
  reference, and level are set in `run.sh` (they drive fetching); cut, window,
  colormap and view direction are constants at the top of `scene.py`. Quality
  is chosen at run time without edits (e.g. `PREVIEW=1 bash scenes/<name>/run.sh`).
- **My call:** the integration test builds a tiny synthetic OME-Zarr 0.5
  (tens of voxels per side, uint16, an ellipsoid with a darker inner band)
  in a temp dir with `zarr`, runs the workflow in background Blender with a
  tiny render, and checks that the render exists, isn't uniform, and the
  dark band shows on the cut face. It skips (not fails) when `blender` or
  Microscopy Nodes isn't available, so CI without Blender stays green.
- **My call:** cut position is measured from the anterior, superior or right
  end of the volume (for the A-P, S-I, L-R axis respectively), both as a
  fraction and as the mm override. The reference render is therefore
  "A-P axis, 1/3, keep posterior".
- **My call:** the opacity floor is not a user option, but it is derived from
  the same background estimate as the default window instead of being fixed
  at 0.05, so templates with brighter backgrounds still get a clean outline.
- **My call:** the integration test runs as part of the normal `uv run pytest`
  when Blender and Microscopy Nodes are found (target well under a minute),
  and skips otherwise.
- Fail loudly: every Microscopy Nodes node, object or property the helper
  touches is looked up by name and a missing one raises an error naming it
  and the tested Microscopy Nodes version.

## Left to the builder

- Function names and signatures in the helper; how `scene_args` generalises
  for volume scenes.
- Where the default-window percentiles are computed (CLI side with numpy, or
  Blender side from Microscopy Nodes' saved histogram) and the exact
  percentiles, as long as Allen lands near 0.03–0.45 and blackcap looks
  sensible.
- How `fetch-template` selects an additional reference (option name, error
  when the atlas has none).
- The example scene's name and the README/AGENTS.md updates.
- Exact preview/final mechanism, provided no file edits are needed to switch.
