"""
Phase 1 / Step 3 (continued): OSM Morphological Indicators
-----------------------------------------------------------
Pulls OpenStreetMap building footprints and road network for Lahore, then
computes, per grid cell:
    - building_footprint_density : built-up area fraction (0-1)
    - building_count             : number of building polygons
    - road_length_km             : total road length within the cell
    - road_gap_score             : proxy for infrastructure gaps (inverse of
                                    local road density, min-max normalised)

Prerequisites:
    pip install osmnx

Run:
    python 04_osm_features.py

Output:
    data/processed/lahore_grid_features.geojson (updated in place)
"""

import geopandas as gpd
import osmnx as ox

import config

ox.settings.log_console = True
ox.settings.use_cache = True


def get_place_polygon() -> gpd.GeoDataFrame:
    """Use the boundary from Step 1 as the OSM query area rather than an
    OSM place name lookup, so the area matches the grid exactly."""
    grid = gpd.read_file(config.GRID_OUTPUT_PATH)
    return grid.union_all()


def fetch_buildings(polygon) -> gpd.GeoDataFrame:
    print("Downloading OSM building footprints ...")
    tags = {"building": True}
    buildings = ox.features_from_polygon(polygon, tags)
    buildings = buildings[buildings.geometry.type.isin(["Polygon", "MultiPolygon"])]
    return buildings.to_crs(config.WORKING_CRS)


def fetch_roads(polygon) -> gpd.GeoDataFrame:
    print("Downloading OSM road network ...")
    graph = ox.graph_from_polygon(polygon, network_type="drive")
    _, edges = ox.graph_to_gdfs(graph)
    return edges.to_crs(config.WORKING_CRS)


def compute_building_features(grid: gpd.GeoDataFrame, buildings: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid_proj = grid.to_crs(config.WORKING_CRS)
    joined = gpd.overlay(buildings[["geometry"]], grid_proj[["cell_id", "geometry"]], how="intersection")
    joined["area_m2"] = joined.geometry.area

    agg = joined.groupby("cell_id").agg(
        building_count=("area_m2", "count"),
        building_area_m2=("area_m2", "sum"),
    ).reset_index()

    grid = grid.merge(agg, on="cell_id", how="left")
    grid["building_count"] = grid["building_count"].fillna(0)
    grid["building_area_m2"] = grid["building_area_m2"].fillna(0)
    cell_area_m2 = config.GRID_CELL_SIZE_M ** 2
    grid["building_footprint_density"] = grid["building_area_m2"] / cell_area_m2

    return grid


def compute_road_features(grid: gpd.GeoDataFrame, roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid_proj = grid.to_crs(config.WORKING_CRS)
    joined = gpd.overlay(roads[["geometry"]], grid_proj[["cell_id", "geometry"]], how="intersection")
    joined["length_m"] = joined.geometry.length

    agg = joined.groupby("cell_id").agg(road_length_m=("length_m", "sum")).reset_index()
    grid = grid.merge(agg, on="cell_id", how="left")
    grid["road_length_m"] = grid["road_length_m"].fillna(0)
    grid["road_length_km"] = grid["road_length_m"] / 1000

    # Infrastructure-gap proxy: cells with low road density relative to the
    # pilot area's max are flagged as higher-gap (min-max normalised, inverted)
    max_len = grid["road_length_km"].max()
    if max_len > 0:
        grid["road_gap_score"] = 1 - (grid["road_length_km"] / max_len)
    else:
        grid["road_gap_score"] = 1.0

    return grid


def main():
    polygon = get_place_polygon()
    grid = gpd.read_file(config.FEATURES_OUTPUT_PATH)  # builds on Step 3 output

    buildings = fetch_buildings(polygon)
    grid = compute_building_features(grid, buildings)

    roads = fetch_roads(polygon)
    grid = compute_road_features(grid, roads)

    grid.to_file(config.FEATURES_OUTPUT_PATH, driver="GeoJSON")
    print(f"Updated feature table with OSM indicators: {config.FEATURES_OUTPUT_PATH}")
    print(grid[["cell_id", "ndvi_mean", "ndbi_mean", "building_footprint_density",
                "road_length_km", "road_gap_score"]].head())


if __name__ == "__main__":
    main()
