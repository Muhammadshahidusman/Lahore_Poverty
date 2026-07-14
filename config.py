"""
Shared configuration for the Pakistan Poverty Lens - Lahore Pilot pipeline.
Edit these paths/constants once; every script imports from here.
"""

import os

# ---- Project paths ----
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
INTERIM_DIR = os.path.join(DATA_DIR, "interim")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
TILES_DIR = os.path.join(DATA_DIR, "tiles")

for d in [DATA_DIR, RAW_DIR, INTERIM_DIR, PROCESSED_DIR, TILES_DIR]:
    os.makedirs(d, exist_ok=True)

# ---- Input files (replace with your own) ----
# Download Lahore's Union Council boundaries from Pakistan's PBS / HDX
# (e.g. https://data.humdata.org/dataset/cod-ab-pak) and place the shapefile here.
UC_BOUNDARY_SHAPEFILE = os.path.join(RAW_DIR, "lahore_union_councils.shp")

# Fallback bounding box for Lahore metro area (used if no shapefile is available yet)
# (min_lon, min_lat, max_lon, max_lat)
LAHORE_BBOX = (74.15, 31.35, 74.50, 31.65)

# ---- Grid settings ----
GRID_CELL_SIZE_M = 1000  # 1 sq km cells
WORKING_CRS = "EPSG:32643"  # UTM Zone 43N - metres, correct for Lahore
OUTPUT_CRS = "EPSG:4326"    # lat/lon for storage & web maps

# ---- Earth Engine settings ----
GEE_PROJECT_ID = "ee-shahidusmaninfo"  # required for GEE's new project-based auth
S2_START_DATE = "2024-01-01"
S2_END_DATE = "2024-12-31"
S2_CLOUD_PROB_THRESHOLD = 20  # max % cloud probability per pixel
VIIRS_START_DATE = "2024-01-01"
VIIRS_END_DATE = "2024-12-31"

# ---- Output file names ----
GRID_OUTPUT_PATH = os.path.join(PROCESSED_DIR, "lahore_grid_1km.geojson")
FEATURES_OUTPUT_PATH = os.path.join(PROCESSED_DIR, "lahore_grid_features.geojson")
