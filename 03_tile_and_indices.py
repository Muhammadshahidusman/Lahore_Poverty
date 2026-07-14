"""
Phase 1 / Step 3: Spectral Indices from Per-Cell Tiles
-----------------------------------------------------------
Reads the per-grid-cell Sentinel-2 tiles produced by 02_gee_ingestion.py
(data/tiles/<cell_id>_s2.tif), computes NDVI and NDBI per pixel, averages
each to a single value per cell, and saves both:
  - the updated grid feature table (ndvi_mean / ndbi_mean columns)
  - a .npy array per cell (bands x H x W) for later CNN training

Run:
    uv run python 03_tile_and_indices.py

Output:
    data/tiles/<cell_id>.npy
    data/processed/lahore_grid_features.geojson
"""

import os

import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio

import config

# Sentinel-2 band order exported in 02_gee_ingestion.py: B2,B3,B4,B8,B11
BAND_INDEX = {"blue": 0, "green": 1, "red": 2, "nir": 3, "swir1": 4}


def compute_indices(tile: np.ndarray) -> tuple:
    """Given a (bands, H, W) array, return (ndvi_mean, ndbi_mean) for the tile."""
    red = tile[BAND_INDEX["red"]]
    nir = tile[BAND_INDEX["nir"]]
    swir1 = tile[BAND_INDEX["swir1"]]

    eps = 1e-6
    ndvi = (nir - red) / (nir + red + eps)
    ndbi = (swir1 - nir) / (swir1 + nir + eps)

    return float(np.nanmean(ndvi)), float(np.nanmean(ndbi))


def process_cell(cell_id: str) -> dict:
    tile_path = os.path.join(config.TILES_DIR, f"{cell_id}_s2.tif")

    if not os.path.exists(tile_path):
        return {"cell_id": cell_id, "ndvi_mean": np.nan, "ndbi_mean": np.nan}

    with rasterio.open(tile_path) as src:
        tile = src.read().astype("float32")

    # Save the raw multi-band array too, for CNN input in Phase 3
    np.save(os.path.join(config.TILES_DIR, f"{cell_id}.npy"), tile)

    ndvi_mean, ndbi_mean = compute_indices(tile)
    return {"cell_id": cell_id, "ndvi_mean": ndvi_mean, "ndbi_mean": ndbi_mean}


def main():
    grid = gpd.read_file(config.GRID_OUTPUT_PATH)

    print(f"Computing NDVI/NDBI for {len(grid)} cells ...")
    results = [process_cell(cell_id) for cell_id in grid["cell_id"]]
    results_df = pd.DataFrame(results)

    missing = results_df["ndvi_mean"].isna().sum()
    if missing:
        print(f"Warning: {missing} cells had no Sentinel-2 tile on disk "
              f"(re-run 02_gee_ingestion.py to fill these in - it skips "
              f"cells that already succeeded).")

    grid = grid.merge(results_df, on="cell_id", how="left")
    grid.to_file(config.FEATURES_OUTPUT_PATH, driver="GeoJSON")

    print(f"Saved feature table: {config.FEATURES_OUTPUT_PATH}")


if __name__ == "__main__":
    main()