"""
Phase 1 / Step 2: Automate Earth Engine Scraping
-----------------------------------------------------------
Queries a cloud-free Sentinel-2 surface reflectance composite and exports it
PER GRID CELL (not as one big composite) - GEE's direct-download path
(geemap.ee_export_image / getPixels) has a hard size limit, and a 10m
composite over the whole Lahore metro area blows past it silently. Each
1 sq km cell at 10m is only ~100x100 px per band, so per-cell export stays
well within limits and doubles as the "tile aligned with the grid" step.

Also exports one small VIIRS nighttime-lights composite for the whole area
(500m resolution keeps the file tiny, so a single export is fine there).

Prerequisites:
    uv sync
    uv run earthengine authenticate   # one-time browser login
    Set config.GEE_PROJECT_ID to your Google Cloud project ID

Run:
    uv run python 02_gee_ingestion.py

Output:
    data/tiles/<cell_id>_s2.tif    (one Sentinel-2 tile per grid cell)
    data/raw/viirs_ntl_composite.tif
"""

import os
import time

import ee
import geemap
import geopandas as gpd

import config


def init_ee():
    try:
        ee.Initialize(project=config.GEE_PROJECT_ID)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=config.GEE_PROJECT_ID)


def get_region_geometry() -> ee.Geometry:
    """Build an EE geometry from the grid's total bounds - used only for the
    VIIRS composite, which is small enough to export in one shot."""
    grid = gpd.read_file(config.GRID_OUTPUT_PATH)
    minx, miny, maxx, maxy = grid.total_bounds
    return ee.Geometry.Rectangle([minx, miny, maxx, maxy])


def mask_s2_clouds(image: ee.Image) -> ee.Image:
    """Cloud-mask Sentinel-2 SR using the built-in cloud probability band."""
    cloud_prob = image.select("MSK_CLDPRB")
    mask = cloud_prob.lt(config.S2_CLOUD_PROB_THRESHOLD)
    return image.updateMask(mask).divide(10000)  # scale reflectance to 0-1


def build_s2_composite(region: ee.Geometry) -> ee.Image:
    """Median cloud-free Sentinel-2 composite, clipped to a region. Called
    once per grid cell with that cell's geometry as `region`."""
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(config.S2_START_DATE, config.S2_END_DATE)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .map(mask_s2_clouds)
    )
    bands = ["B2", "B3", "B4", "B8", "B11"]  # blue, green, red, NIR, SWIR1
    return s2.median().clip(region).select(bands)


def get_viirs_ntl_composite(region: ee.Geometry) -> ee.Image:
    viirs = (
        ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
        .filterBounds(region)
        .filterDate(config.VIIRS_START_DATE, config.VIIRS_END_DATE)
        .select("avg_rad")
    )
    return viirs.mean().clip(region)


def export_image(image: ee.Image, out_path: str, region: ee.Geometry, scale: int):
    geemap.ee_export_image(
        image,
        filename=out_path,
        scale=scale,
        region=region,
        file_per_band=False,
    )


def export_sentinel2_tiles(grid: gpd.GeoDataFrame, max_retries: int = 3):
    """Export one small Sentinel-2 GeoTIFF per grid cell. Resumable: cells
    that already have a tile file on disk are skipped, so a crashed run can
    just be re-launched."""
    total = len(grid)
    for i, row in grid.iterrows():
        cell_id = row["cell_id"]
        out_path = os.path.join(config.TILES_DIR, f"{cell_id}_s2.tif")

        if os.path.exists(out_path):
            continue  # already downloaded in a previous run

        coords = list(row.geometry.exterior.coords)
        region = ee.Geometry.Polygon([coords])
        image = build_s2_composite(region)

        for attempt in range(1, max_retries + 1):
            try:
                export_image(image, out_path, region, scale=10)
                break
            except Exception as e:
                print(f"  [{cell_id}] attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    print(f"  [{cell_id}] giving up after {max_retries} attempts")
                else:
                    time.sleep(2 * attempt)  # simple backoff before retrying

        if (i + 1) % 25 == 0 or (i + 1) == total:
            print(f"Sentinel-2 tiles: {i + 1}/{total} cells processed")


def main():
    init_ee()
    grid = gpd.read_file(config.GRID_OUTPUT_PATH)

    print(f"Exporting Sentinel-2 tiles for {len(grid)} grid cells ...")
    export_sentinel2_tiles(grid)
    print(f"Sentinel-2 tiles saved to: {config.TILES_DIR}")

    print("Exporting VIIRS nighttime-lights composite ...")
    region = get_region_geometry()
    ntl_composite = get_viirs_ntl_composite(region)
    ntl_out_path = os.path.join(config.RAW_DIR, "viirs_ntl_composite.tif")
    export_image(ntl_composite, ntl_out_path, region, scale=500)
    print(f"Saved: {ntl_out_path}")


if __name__ == "__main__":
    main()