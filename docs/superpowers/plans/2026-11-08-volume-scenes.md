# Volume Scenes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render a template volume cut open by one plane from a `scenes/<name>/` folder, as easily as mesh scenes.

**Architecture:** A CLI command (`prepare-volume`) fetches the OME-Zarr level and writes a small `volume.json` (path, level, extent, default window). Inside Blender, Microscopy Nodes loads the zarr; a new helper (`volume_setup.py`) re-poses it into mesh space, applies the fixed look, and moves the slice cube. Cut and camera geometry live in a stdlib-only module so they are unit-tested without Blender. A headless integration test runs the whole scene on synthetic data.

**Tech Stack:** Python 3.12, typer, numpy, zarr (already present via brainglobe-atlasapi), Blender 5.2.3 + Microscopy Nodes 3.1.3, pytest, Pillow (dev only, for reading the test render).

**Spec:** `docs/superpowers/specs/2026-11-08-volume-scenes-design.md`

## Global Constraints

- Microscopy Nodes does all OME-Zarr parsing/VDB conversion; brainblender never reads zarr inside Blender.
- Files in `brainblender/blender/` use bpy + stdlib only (`cut.py`: stdlib only, no bpy, so pytest can import it).
- Tested combination: Microscopy Nodes `3.1.3`, Blender `5.2.3`; any missing MiN object/node/property raises `RuntimeError` naming it and `3.1.3`.
- Blender space (same as `brainblender.mesh.normalize`): mm, centred on the volume centre, X = right, Y = anterior, Z = superior.
- Cut position measured from the anterior / superior / right end; default kept side posterior / inferior / left.
- Contrast window units: normalised intensity `value / (max + 1)`.
- Fixed look: Constant Alpha; alpha ramp `floor → 1.0` (top exactly 1.0); Emission/Scattering `0.3`; Cycles `volume_step_rate = 1.0`; world background `(0.02, 0.02, 0.02)`; view transform `Standard`; default cube removed; MiN `axes` hidden from render.
- Quality: preview = 50 % resolution, 16 samples, denoise; final = 100 %, 128 samples adaptive, denoise. Chosen by env `PREVIEW=1`.
- Every scene render also saves `<render>.blend` next to `<render>.png` (mesh scenes too).
- Conventions: type hints, NumPy docstrings, ruff/mypy/codespell via pre-commit.

## Review Focus

1. Pyramid level that does not exist (blackcap has only `s0`) → `prepare-volume` fails with the available levels, not a Blender traceback. Test in Task 2.
2. Template data not downloaded / all zeros → `prepare-volume` refuses ("volume is empty") instead of rendering a blank scene (the original bug). Test in Task 2.
3. Saved `.blend` reopened later → its VDBs live in `<scene data dir>/cache`, not `$TMPDIR`, so they survive temp cleanup. Asserted in Task 5's integration test.
4. Cut fraction outside (0, 1) or mm outside (0, extent) → `ValueError` with the valid range. Test in Task 3.
5. Unknown `--reference` name → error listing the atlas's references (or "none"). Test in Task 1.

---

### Task 1: `fetch-template --reference`

**Files:**
- Modify: `brainblender/atlas.py` (`fetch_template`, new `template_location`)
- Modify: `brainblender/cli.py` (`fetch-template` command)
- Test: `tests/test_atlas.py`

**Interfaces:**
- Produces: `template_location(metadata: dict, reference: str | None = None) -> str` (location without leading `/`); `fetch_template(atlas: BrainGlobeAtlas, finest: int, reference: str | None = None) -> Path`.

- [ ] **Step 1: Write the failing tests**

```python
META = {
    "annotation_set": {"template": {"location": "/templates/t/1_0"}},
    "additional_references": [{"name": "nissl", "location": "/templates/n/1_0"}],
}


def test_template_location_main_and_reference() -> None:
    assert template_location(META) == "templates/t/1_0"
    assert template_location(META, "nissl") == "templates/n/1_0"


def test_template_location_unknown_reference_lists_available() -> None:
    with pytest.raises(ValueError, match="nissl"):
        template_location(META, "mri")
    with pytest.raises(ValueError, match="none"):
        template_location({**META, "additional_references": []}, "mri")
```

- [ ] **Step 2: Run** `uv run pytest tests/test_atlas.py -v` — expect ImportError on `template_location`.
- [ ] **Step 3: Implement** `template_location`; make `fetch_template` use it; add `--reference` option to `fetch-template` (help: "Additional reference to fetch instead of the main template"). In the CLI, report `ValueError` as `typer.BadParameter(str(e))` (drop the `--finest` hint since the error may concern either option).
- [ ] **Step 4: Run** `uv run pytest -v` — PASS. Run `uv run brainblender fetch-template allen_mouse_50um --reference x --finest 3` — error says the atlas has no references.
- [ ] **Step 5: Commit** `git commit -m "fetch additional references with fetch-template --reference"`

### Task 2: `prepare-volume` and the default window

**Files:**
- Create: `brainblender/volume.py`
- Modify: `brainblender/cli.py` (new `prepare-volume` command)
- Test: `tests/test_volume.py`

**Interfaces:**
- Consumes: `fetch_template` (Task 1).
- Produces:
  - `TISSUE_MIN = 0.02`, `WINDOW_PERCENTILES = (2, 95)`, `FLOOR_PERCENTILE = 5`
  - `default_window(normalized: np.ndarray) -> tuple[float, float, float]` → `(lo, hi, floor)`, percentiles of voxels `> TISSUE_MIN`; `floor` clamped below `hi`; `ValueError("volume is empty ...")` when no voxel exceeds `TISSUE_MIN`.
  - `volume_info(zarr_path: Path, level: int) -> dict` with keys `zarr` (str), `level` (int), `extent_mm` (`[ap, si, lr]` = level shape × level scale, axes z/y/x), `window` (`[lo, hi]`), `floor` (float); normalises with `data / (data.max() + 1)`; `ValueError` naming available levels when `level` is out of range.
  - CLI: `brainblender prepare-volume ATLAS --level INT [--reference NAME] --output PATH.json` → `fetch_template(atlas, level, reference)`, then writes `volume_info(...)` as JSON.
  - Test helper (also used by Task 5): `tests/synthetic.py::write_ome_zarr(path: Path, data: np.ndarray, scale_mm: float, levels: int = 2) -> Path` writing an OME-Zarr 0.5 (zarr v3) group with `s0..s{levels-1}` (each level 2× downsampled by striding, scale doubled), axes `z, y, x` in `millimeter`.

- [ ] **Step 1: Write the failing tests** (`tests/test_volume.py`)

```python
def test_default_window_percentiles() -> None:
    background = np.zeros(1000)
    tissue = np.linspace(0.03, 0.5, 1000)
    lo, hi, floor = default_window(np.concatenate([background, tissue]))
    assert lo == pytest.approx(np.percentile(tissue, 2))
    assert hi == pytest.approx(np.percentile(tissue, 95))
    assert floor == pytest.approx(np.percentile(tissue, 5))


def test_default_window_rejects_empty_volume() -> None:
    with pytest.raises(ValueError, match="empty"):
        default_window(np.zeros(100))


def test_volume_info(tmp_path: Path) -> None:
    data = np.zeros((40, 20, 30), dtype=np.uint16)
    data[10:30, 5:15, 5:25] = 300
    path = write_ome_zarr(tmp_path / "t.ome.zarr", data, scale_mm=0.1)
    info = volume_info(path, level=1)
    assert info["level"] == 1 and info["zarr"] == str(path)
    assert info["extent_mm"] == pytest.approx([4.0, 2.0, 3.0])
    assert 0 < info["window"][0] < info["window"][1] < 1


def test_volume_info_unknown_level_lists_available(tmp_path: Path) -> None:
    path = write_ome_zarr(
        tmp_path / "t.ome.zarr", np.ones((8, 8, 8), np.uint16), 0.1, levels=1
    )
    with pytest.raises(ValueError, match="0..0"):
        volume_info(path, level=2)
```

- [ ] **Step 2: Run** `uv run pytest tests/test_volume.py -v` — expect ImportError.
- [ ] **Step 3: Implement** `tests/synthetic.py`, `brainblender/volume.py`, and the `prepare-volume` command (report `ValueError` as `typer.BadParameter`). Reuse `levels_to_fetch`'s range message style (`"Level must be in 0..N, got L"`).
- [ ] **Step 4: Run** `uv run pytest -v` — PASS. Run `uv run brainblender prepare-volume allen_mouse_50um --level 2 --output /tmp/v.json` and check `window` ≈ `[0.033, 0.449]`, `floor` ≈ `0.054`, `extent_mm` = `[13.2, 8.0, 11.4]`.
- [ ] **Step 5: Commit** `git commit -m "add prepare-volume with percentile-based default window"`

### Task 3: Cut and camera geometry (`cut.py`)

**Files:**
- Create: `brainblender/blender/cut.py` (stdlib only)
- Test: `tests/test_cut.py`

**Interfaces:**
- Produces (`Axis = Literal["AP", "SI", "LR"]`, vectors as `tuple[float, float, float]` in Blender X/Y/Z):
  - `SIDES: dict[Axis, tuple[str, str]] = {"AP": ("anterior", "posterior"), "SI": ("superior", "inferior"), "LR": ("right", "left")}` — (near end, far end); positions are measured from the near end.
  - `default_keep(axis: Axis) -> str` → far end.
  - `cut_position_mm(extent_mm: float, fraction: float | None = None, mm: float | None = None) -> float` — `mm` overrides `fraction`; `ValueError` unless `0 < result < extent_mm`.
  - `kept_interval(extent_mm: float, position_mm: float, axis: Axis, keep: str) -> tuple[float, float]` — `(position, extent)` when keeping the far end, `(0, position)` for the near end; `ValueError` if `keep` not in `SIDES[axis]`.
  - `view_direction(axis: Axis, keep: str) -> tuple[float, float, float]` — `1.5 * n + other two`, `n` pointing from kept part to removed side.
  - `kept_box(extent_mm: tuple[float, float, float], axis: Axis, interval: tuple[float, float]) -> tuple[tuple[float, float, float], float]` — centre (Blender coords, volume centred at origin; coordinate = half extent − distance from near end) and bounding-sphere radius of the kept box. `extent_mm` is `(ap, si, lr)` as in `volume.json`.

- [ ] **Step 1: Write the failing tests**

```python
def test_reference_cut() -> None:  # the 2026-11-08 render
    pos = cut_position_mm(13.2, fraction=1 / 3)
    assert pos == pytest.approx(4.4)
    assert kept_interval(13.2, pos, "AP", default_keep("AP")) == pytest.approx(
        (4.4, 13.2)
    )
    assert view_direction("AP", "posterior") == pytest.approx((1.0, 1.5, 1.0))
    centre, _ = kept_box((13.2, 8.0, 11.4), "AP", (4.4, 13.2))
    assert centre == pytest.approx((0.0, -2.2, 0.0))


def test_view_direction_other_axes_and_flip() -> None:
    assert view_direction("AP", "anterior") == pytest.approx((1.0, -1.5, 1.0))
    assert view_direction("SI", "inferior") == pytest.approx((1.0, 1.0, 1.5))
    assert view_direction("LR", "left") == pytest.approx((1.5, 1.0, 1.0))


def test_mm_overrides_fraction() -> None:
    assert cut_position_mm(13.2, fraction=0.5, mm=2.0) == 2.0


@pytest.mark.parametrize(
    "kwargs", [{"fraction": 0.0}, {"fraction": 1.2}, {"mm": 14.0}, {}]
)
def test_cut_position_out_of_range(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        cut_position_mm(13.2, **kwargs)
```

- [ ] **Step 2: Run** `uv run pytest tests/test_cut.py -v` — expect ImportError.
- [ ] **Step 3: Implement** `brainblender/blender/cut.py`.
- [ ] **Step 4: Run** `uv run pytest -v` — PASS.
- [ ] **Step 5: Commit** `git commit -m "add cut and camera geometry for volume scenes"`

### Task 4: Save `.blend` with every render

**Files:**
- Modify: `brainblender/blender/scene_setup.py` (`render`, `scene_args` usage text)

**Interfaces:**
- Produces: `render(path: Path) -> None` now also writes `path.with_suffix(".blend")` via `bpy.ops.wm.save_as_mainfile(filepath=..., copy=True)` before rendering; `scene_args()` usage text says `<input> <output_png>` (input is a meshes dir or a `volume.json`).

- [ ] **Step 1: Implement** the change.
- [ ] **Step 2: Verify** `bash scenes/blackcap-root/run.sh`; expect `root.png` and `root.blend` in `$BRAINBLENDER_SCENES_DIR/blackcap-root/renders/`, and `blender -b <that>.blend --python-expr "import bpy; print(len(bpy.data.objects))"` prints a non-zero count.
- [ ] **Step 3: Commit** `git commit -m "save the .blend next to every scene render"`

### Task 5: Volume helper, example scene, integration test

**Files:**
- Create: `brainblender/blender/volume_setup.py`
- Create: `scenes/allen-mouse-template-cut/run.sh`, `scenes/allen-mouse-template-cut/scene.py`
- Create: `tests/test_volume_scene.py`
- Modify: `pyproject.toml` (add `pillow` to the `dev` group)

**Interfaces:**
- Consumes: `volume.json` (Task 2), `tests/synthetic.py::write_ome_zarr` and `volume_info` (Task 2), `cut.py` (Task 3), `scene_setup.add_camera/add_light/render/scene_args` (Task 4).
- Produces (`volume_setup.py`):
  - `TESTED_MIN_VERSION = "3.1.3"`; `ALPHA_MULTIPLIER = 100.0` (the 1000 from the reference render was at 0.1 Blender units per mm; at 1 unit per mm the same opacity per mm is 100, tune against the reference render); `EMISSION_SCATTERING = 0.3`.
  - `load_volume(zarr_path: Path, level: int, cache_dir: Path) -> bpy.types.Object` — removes `Cube` if present; sets MiN add-on prefs `cache_option = "PATH"`, `cache_path = str(cache_dir)` (session only); `scene.MiN_remake = True`; sets `MiN_input_file`, `MiN_selected_array_option = str(level)`; channel 0: `volume=True, surface=False, emission=False`; runs `bpy.ops.microscopynodes.load_background()` and requires `{"FINISHED"}`; hides the `axes` object from render; returns the holder object (named `zarr_path.name`).
  - `pose_like_meshes(holder: bpy.types.Object, extent_mm: tuple[float, float, float]) -> None` — scale 1; rotation mapping MiN local (x = R→L, y = S→I, z = A→P) to X = −x, Y = −z, Z = −y; translation `(lr/2, ap/2, si/2)`.
  - `set_look(window: tuple[float, float], floor: float, color: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> None` — the Global Constraints recipe on the `volume` material nodes `[color_lut_ch_id0]` (ramp black → `color`), `[contrast_limits_ch_id0]` (window), `[alpha_limits_ch_id0]` (`floor → 1.0`), `[volume_alpha_ch_id0]` (`Alpha Mode = "Constant Alpha"`, `Alpha Multiplier = ALPHA_MULTIPLIER`), `[microscopy_shading_ch_id0]` (`Emission / Scattering`), plus world background, view transform, Cycles engine and step rate.
  - `cut_volume(axis: Axis, interval: tuple[float, float]) -> None` — the `slice cube` object is in the holder's local mm space spanning `0..extent` per axis (location = half extent, scale = half extent); set location/scale on the local axis for `axis` (AP → z, SI → y, LR → x) to the interval's midpoint/half-length.
  - `set_quality(preview: bool) -> None` — presets from Global Constraints.
  - A private `_require(collection, name, kind)` used for every MiN lookup, raising `RuntimeError(f"Microscopy Nodes {kind} '{name}' not found (brainblender is tested with Microscopy Nodes {TESTED_MIN_VERSION})")`.
- Example scene `scene.py` constants: `CUT_AXIS = "AP"`, `CUT_FRACTION = 1 / 3`, `CUT_MM = None`, `KEEP = None` (→ `default_keep`), `WINDOW = (0.03, 0.45)` (`None` → `volume.json` default), `COLOR = (1.0, 1.0, 1.0)`, `VIEW_DIRECTION = None` (→ `view_direction`). Reads `volume.json` from `scene_args()`, `preview = os.environ.get("PREVIEW") == "1"`, cache dir = `<output_png>.parent.parent / "cache"`, camera targets `kept_box` centre/radius.
- `run.sh`: like `scenes/allen-mouse-cortex/run.sh`; `LEVEL=${LEVEL:-2}`; runs `brainblender prepare-volume allen_mouse_50um --level "$LEVEL" --output "$DATA_DIR/volume.json"`, then Blender with `-- "$DATA_DIR/volume.json" "$DATA_DIR/renders/template-cut.png"`; passes `PREVIEW` through the environment.

- [ ] **Step 1: Write the failing integration test** (`tests/test_volume_scene.py`)

```python
BLENDER = os.environ.get("BLENDER", "blender")
SCENE = Path(__file__).parents[1] / "scenes/allen-mouse-template-cut/scene.py"


def _has_microscopy_nodes() -> bool:
    if shutil.which(BLENDER) is None:
        return False
    probe = "import bpy, sys; sys.exit(0 if hasattr(bpy.types.Scene, 'MiN_input_file') else 3)"
    return subprocess.run([BLENDER, "-b", "--python-expr", probe]).returncode == 0


pytestmark = pytest.mark.skipif(
    not _has_microscopy_nodes(), reason="needs Blender with Microscopy Nodes"
)


def test_volume_scene_renders_cut_face(tmp_path: Path) -> None:
    data = np.full((48, 32, 40), 1, dtype=np.uint16)  # z=AP, y=SI, x=LR
    zz, yy, xx = np.ogrid[:48, :32, :40]
    inside = ((zz - 24) / 22) ** 2 + ((yy - 16) / 14) ** 2 + ((xx - 20) / 18) ** 2 < 1
    data[inside] = 300
    data[inside & (abs(yy - 16) < 3)] = 60  # dark "white matter" sheet
    zarr_path = write_ome_zarr(tmp_path / "t.ome.zarr", data, scale_mm=0.1)
    json_path = tmp_path / "volume.json"
    json_path.write_text(json.dumps(volume_info(zarr_path, level=0)))
    png = tmp_path / "renders" / "out.png"

    subprocess.run(
        [BLENDER, "-b", "--python", str(SCENE), "--", str(json_path), str(png)],
        env={**os.environ, "PREVIEW": "1"},
        check=True,
        timeout=300,
    )

    assert png.exists() and png.with_suffix(".blend").exists()
    assert list((tmp_path / "cache").rglob("*.vdb"))  # Review Focus 3
    pixels = np.asarray(Image.open(png).convert("L"), dtype=float) / 255
    background = np.median(pixels[:5, :5])
    brain = pixels[pixels > background + 0.05]
    assert brain.size > 0.02 * pixels.size  # something rendered
    assert (
        np.percentile(brain, 95) - np.percentile(brain, 5) > 0.25
    )  # dark sheet visible against bright tissue
```

- [ ] **Step 2: Run** `uv sync --group dev && uv run pytest tests/test_volume_scene.py -v` — expect FAIL (scene file missing).
- [ ] **Step 3: Implement** `volume_setup.py`, the example `scene.py` and `run.sh`.
- [ ] **Step 4: Run** `uv run pytest -v` — all PASS (integration test under a minute).
- [ ] **Step 5: Verify against the reference render:** `PREVIEW=1 bash scenes/allen-mouse-template-cut/run.sh`; open `renders/template-cut.png`: posterior two-thirds, cut face towards the camera from anterior-superior-right, corpus callosum dark against bright cortex, no ghosting. Tune `ALPHA_MULTIPLIER` if the cut face looks see-through (white matter recessed) or the outer surface black. Open `template-cut.blend` in Blender and confirm the volume shows.
- [ ] **Step 6: Commit** `git commit -m "add volume scenes: Microscopy Nodes helper, example scene, integration test"`

### Task 6: Docs

**Files:**
- Modify: `README.md` (Scenes: volume scenes, `PREVIEW=1`, `LEVEL=`, saved `.blend`, Microscopy Nodes requirement and tested version; `prepare-volume` and `fetch-template --reference` usage)
- Modify: `AGENTS.md` (structure: `volume.py`, `blender/cut.py`, `blender/volume_setup.py`; commands: `prepare-volume`; note that `tests/test_volume_scene.py` needs Blender + Microscopy Nodes and skips otherwise)

- [ ] **Step 1: Update** both files.
- [ ] **Step 2: Run** `uv run pre-commit run --all-files` — all pass.
- [ ] **Step 3: Commit** `git commit -m "document volume scenes"`
