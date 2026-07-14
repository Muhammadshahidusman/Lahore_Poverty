"""
Phase 1 / Step 1: Define Spatial Boundaries & Grid Tiling
-----------------------------------------------------------
Loads Lahore's Union Council boundaries (or falls back to a bounding box),
then generates a standardized 1 sq km vector grid over the metro area.

Run:
    python 01_grid_tiling.py

Output:
    data/processed/lahore_grid_1km.geojson
"""

import os
import geopandas as gpd
import numpy as np
from shapely.geometry import box

import config


def load_boundary() -> gpd.GeoDataFrame:
    """Load the Union Council shapefile if present, otherwise build a
    rectangular boundary from the fallback bounding box."""
    if os.path.exists(config.UC_BOUNDARY_SHAPEFILE):
        print(f"Loading boundary shapefile: {config.UC_BOUNDARY_SHAPEFILE}")
        gdf = gpd.read_file(config.UC_BOUNDARY_SHAPEFILE)
        if gdf.crs is None:
            raise ValueError("Shapefile has no CRS defined - fix the .prj file first.")
        gdf = gdf.to_crs(config.OUTPUT_CRS)
    else:
        print("No boundary shapefile found - falling back to Lahore bounding box.")
        min_lon, min_lat, max_lon, max_lat = config.LAHORE_BBOX
        geom = box(min_lon, min_lat, max_lon, max_lat)
        gdf = gpd.GeoDataFrame({"name": ["lahore_bbox"]}, geometry=[geom], crs=config.OUTPUT_CRS)
    return gdf


def make_grid(boundary_gdf: gpd.GeoDataFrame, cell_size_m: float) -> gpd.GeoDataFrame:
    """Generate a square grid covering the boundary's extent, clipped to the
    boundary geometry, in a projected (metres) CRS for accurate sizing."""
    boundary_proj = boundary_gdf.to_crs(config.WORKING_CRS)
    minx, miny, maxx, maxy = boundary_proj.total_bounds

    xs = np.arange(minx, maxx + cell_size_m, cell_size_m)
    ys = np.arange(miny, maxy + cell_size_m, cell_size_m)

    cells = []
    for x in xs[:-1]:
        for y in ys[:-1]:
            cells.append(box(x, y, x + cell_size_m, y + cell_size_m))

    grid = gpd.GeoDataFrame({"geometry": cells}, crs=config.WORKING_CRS)

    # Keep only cells that actually intersect the boundary (drops empty corners)
    union_geom = boundary_proj.geometry.union_all()
    grid = grid[grid.geometry.intersects(union_geom)].reset_index(drop=True)

    grid["cell_id"] = [f"lhr_{i:05d}" for i in range(len(grid))]
    grid["area_sqkm"] = grid.geometry.area / 1e6

    return grid.to_crs(config.OUTPUT_CRS)


def main():
    boundary = load_boundary()
    grid = make_grid(boundary, config.GRID_CELL_SIZE_M)

    grid.to_file(config.GRID_OUTPUT_PATH, driver="GeoJSON")
    print(f"Generated {len(grid)} grid cells covering {grid['area_sqkm'].sum():.1f} sq km")
    print(f"Saved to: {config.GRID_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
