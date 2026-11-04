# Pakistan Poverty Lens — Phase 1 Pipeline (Lahore Pilot)

Portfolio: https://muhammadshahidusman.github.io

Working code for Phase 1 (Environment & Data Engineering) of the roadmap:
grid tiling → Earth Engine ingestion → spectral indices → OSM features.

## 1. Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management
(`pyproject.toml` + lockfile, no manual venv activation needed).

```bash
# install uv if you don't have it yet
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# or: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows

cd poverty_lens_pipeline
uv sync              # creates .venv/ and installs everything from pyproject.toml
```

Run any script with `uv run` — it uses the project's `.venv` automatically,
no `source .venv/bin/activate` required:

```bash
uv run python 01_grid_tiling.py
```

One-time Earth Engine auth (opens a browser to log into your Google account):

```bash
uv run earthengine authenticate
```

Then edit `config.py`:
- Set `GEE_PROJECT_ID` to your Google Cloud project ID (required by GEE's
  current auth model — create a free project at console.cloud.google.com if
  you don't have one, and enable the "Earth Engine API").
- If you have a real Lahore Union Council shapefile, place it at
  `data/raw/lahore_union_councils.shp`. Otherwise the pipeline falls back to
  a bounding box (`LAHORE_BBOX`) automatically — good enough to get the
  pipeline running end-to-end before you source the real boundary file.

## 2. Run the pipeline in order

```bash
uv run python 01_grid_tiling.py        # -> data/processed/lahore_grid_1km.geojson
uv run python 02_gee_ingestion.py      # -> data/tiles/<cell_id>_s2.tif (one per cell), data/raw/viirs_ntl_composite.tif
uv run python 03_tile_and_indices.py   # -> data/tiles/*.npy, adds ndvi_mean/ndbi_mean to grid
uv run python 04_osm_features.py       # -> adds building density + road features to grid
```

**Note on Step 2:** Sentinel-2 is exported *per grid cell*, not as one big
composite for the whole metro area - GEE's direct-download path has a size
limit that a 10m-resolution composite over all of Lahore blows past. This
means Step 2 makes one small request per cell (a few hundred for the Lahore
pilot), which takes longer but is far more reliable. It's also resumable: if
it crashes or you Ctrl+C partway through, just run it again — cells that
already have a tile on disk are skipped.

Each script reads its inputs from `config.py` paths and is safe to re-run
independently once its upstream dependency has produced output.

## 3. What you get at the end

`data/processed/lahore_grid_features.geojson` — one row per 1 sq km cell with:

| column                      | meaning                                          |
|-----------------------------|---------------------------------------------------|
| `cell_id`                   | unique grid cell identifier                      |
| `ndvi_mean`                 | mean vegetation index                            |
| `ndbi_mean`                 | mean built-up index                              |
| `building_footprint_density`| fraction of cell area covered by buildings       |
| `building_count`            | number of building polygons in the cell          |
| `road_length_km`            | total road length in the cell                    |
| `road_gap_score`            | proxy for infrastructure gap (higher = more gap) |

`data/tiles/<cell_id>_s2.tif` — raw per-cell Sentinel-2 GeoTIFF (as downloaded from GEE).
`data/tiles/<cell_id>.npy` — per-cell Sentinel-2 image arrays (5 bands ×
H × W), ready to feed into the CNN in Phase 3.

## 4. Common gotchas

- **GEE export size limits**: `geemap.ee_export_image` works for
  single-region exports up to a few hundred MB. If the Lahore metro extent
  is too large at 10 m resolution, switch to `ee.batch.Export.image.toDrive`
  with tiling, or export by grid quadrant.
- **OSM rate limiting**: `osmnx` queries the public Overpass API — for a
  city the size of Lahore this can take several minutes and occasionally
  times out. Re-running is safe; `ox.settings.use_cache = True` avoids
  re-downloading on retries.
- **CRS mismatches**: all area/length calculations happen in
  `config.WORKING_CRS` (UTM 43N, metres). If you swap in your own boundary
  file, make sure it has a defined CRS before running Step 1.

## 5. Adding dependencies later (Phase 2/3)

When you get to Phase 2/3 and need e.g. `scikit-learn`, `xgboost`, or
`torch`, add them with:

```bash
uv add scikit-learn xgboost torch
```

This updates `pyproject.toml` and `uv.lock` automatically — no need to hand-edit
either file.

## 6. Next step (Phase 2)

This pipeline produces features only — no poverty labels yet. Phase 2
(ground truth) involves acquiring PSLM/DHS survey data and spatially joining
it to `cell_id`. Say the word and I'll write that ingestion + spatial-join
script next, in the same style.