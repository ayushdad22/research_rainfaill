"""
ERA5 grid population density map of Dublin region
Perfectly matched style, extent, and projection to the elevation/coastline basemaps.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from shapely.geometry import box
import contextily as cx
from pyproj import Transformer

# Ensure pathing is relative to script location
SCRIPT_DIR = Path(__file__).resolve().parent

# ── ERA5 Domain (Strictly Matched to Elevation & Coastline Maps) ──────────────
LAT_MIN, LON_MIN = 52.75, -6.75
STEP = 0.25
N = 4
lon_max = LON_MIN + (N * STEP)
lat_max = LAT_MIN + (N * STEP)

# Setup coordinate transformer to Web Mercator
to_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

# ── Load Data ────────────────────────────────────────────────────────────────
print("Loading GeoJSON and Census Data…")
geojson_path = SCRIPT_DIR / 'data' / 'census' / 'small_areas_2022.geojson'
csv_path = SCRIPT_DIR / 'data' / 'census' / 'saps_small_area_2022.csv'

if not geojson_path.exists() or not csv_path.exists():
    raise SystemExit(f"Missing data files under: {SCRIPT_DIR / 'data'}")

gdf = gpd.read_file(geojson_path)
all_wgs = gdf.to_crs('EPSG:4326')

pop_df = pd.read_csv(csv_path, usecols=['GUID', 'T1_1AGETT'])
all_wgs = all_wgs.merge(pop_df, left_on='SA_GUID_2022', right_on='GUID', how='left')

# Calculate Area and Density using metric Irish Transverse Mercator (ITM)
all_metric = all_wgs.to_crs('EPSG:2157')
all_metric['area_km2'] = all_metric.geometry.area / 1e6
all_metric['pop_density'] = all_metric['T1_1AGETT'] / all_metric['area_km2']
all_wgs = all_metric.to_crs('EPSG:4326')

# ── Clip to ERA5 Grid Box ────────────────────────────────────────────────────
grid_box = box(LON_MIN, LAT_MIN, lon_max, lat_max)
in_grid = all_wgs[all_wgs.intersects(grid_box)].copy()

# ── Aggregate to ERA5 Cells ───────────────────────────────────────────────────
print("Aggregating population to grid cells…")
cell_density = {}
cell_population = {}
cell_geom_merc = {}

for row in range(N):
    for col in range(N):
        cid = f"{row+1},{col+1}"
        south = LAT_MIN + row * STEP
        west = LON_MIN + col * STEP
        north, east = south + STEP, west + STEP
        
        cell_poly = box(west, south, east, north)
        cell_gdf = gpd.GeoDataFrame(geometry=[cell_poly], crs='EPSG:4326')

        # Intersection
        intersection = gpd.overlay(in_grid, cell_gdf, how='intersection')
        
        # Center point in Web Mercator
        cx_lon, cy_lat = (west + east) / 2, (south + north) / 2
        cell_geom_merc[cid] = to_merc.transform(cx_lon, cy_lat)
        
        if len(intersection) == 0:
            cell_density[cid] = 0.0
            cell_population[cid] = 0
            continue

        intr_m = intersection.to_crs('EPSG:2157')
        intr_m['intr_area_km2'] = intr_m.geometry.area / 1e6
        intr_m['pop_in_cell'] = (intr_m['intr_area_km2'] /
                                  intr_m['area_km2'].replace(0, np.nan)) * intr_m['T1_1AGETT']

        total_pop = intr_m['pop_in_cell'].sum()
        total_area = intr_m['intr_area_km2'].sum()

        cell_population[cid] = total_pop
        cell_density[cid] = total_pop / total_area if total_area > 0 else 0.0

# ── Plotting ─────────────────────────────────────────────────────────────────
print("Generating map plot…")
fig, ax = plt.subplots(figsize=(11, 11))

# Project census polygons to Web Mercator to overlay neatly onto the basemap
in_grid_merc = in_grid.to_crs('EPSG:3857')

valid_dens = in_grid_merc['pop_density'].dropna()
vmin = 0
vmax = np.percentile(valid_dens, 97)
cmap = plt.cm.YlOrRd

# Plot choropleth layer with alpha matching the subtle tone of the other maps
in_grid_merc.plot(
    column='pop_density',
    ax=ax,
    cmap=cmap,
    vmin=vmin,
    vmax=vmax,
    linewidth=0.04,
    edgecolor='#cccccc',
    alpha=0.5,  # Allows basemap visibility matching your other maps
    legend=False,
    zorder=2
)

# Draw ERA5 Grid Lines in Web Mercator
for col in range(N + 1):
    x_lon = LON_MIN + col * STEP
    x0, y0 = to_merc.transform(x_lon, LAT_MIN)
    x1, y1 = to_merc.transform(x_lon, lat_max)
    ax.plot([x0, x1], [y0, y1], color='black', linewidth=1.5, zorder=4)

for row in range(N + 1):
    y_lat = LAT_MIN + row * STEP
    x0, y0 = to_merc.transform(LON_MIN, y_lat)
    x1, y1 = to_merc.transform(lon_max, y_lat)
    ax.plot([x0, x1], [y0, y1], color='black', linewidth=1.5, zorder=4)

# Calculate a reliable text vertical offset inside Web Mercator space (meters)
y_cell_height = to_merc.transform(LON_MIN, LAT_MIN + STEP)[1] - to_merc.transform(LON_MIN, LAT_MIN)[1]
y_offset = y_cell_height * 0.24

# Annotate Cells
for cid, (lx, ly) in cell_geom_merc.items():
    dens = cell_density.get(cid, 0.0)
    pop = cell_population.get(cid, 0)
    
    # Cell ID Label Box
    ax.text(lx, ly + y_offset, cid,
            ha='center', va='center', fontsize=9.5, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor='black', linewidth=1.3, alpha=0.85),
            zorder=6)

    # Density Label
    ax.text(lx, ly, f"{dens:,.0f} /km²",
            ha='center', va='center', fontsize=8.5,
            fontweight='semibold', color='#111111', zorder=6,
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                      edgecolor='none', alpha=0.75))
    
    # Population Label
    ax.text(lx, ly - y_offset, f"pop: {pop:,.0f}",
            ha='center', va='center', fontsize=7.5, color='#222222', zorder=6,
            bbox=dict(boxstyle='round,pad=0.1', facecolor='white',
                      edgecolor='none', alpha=0.65))

# View Extents windowing (With the identical 0.06 padding)
xmin, ymin = to_merc.transform(LON_MIN, LAT_MIN)
xmax, ymax = to_merc.transform(lon_max, lat_max)
pad = (xmax - xmin) * 0.06
ax.set_xlim(xmin - pad, xmax + pad)
ax.set_ylim(ymin - pad, ymax + pad)

# Add matching OpenStreetMap Basemap
cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, zorder=1)
ax.set_axis_off()

# Colorbar Configuration
sm = plt.cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(vmin=vmin, vmax=vmax))
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, orientation='vertical', fraction=0.022, pad=0.015, shrink=0.65)
cbar.set_label('Population Density (people / km²)', fontsize=10, labelpad=12)
cbar.ax.tick_params(labelsize=9)

top_val = int(round(vmax / 100) * 100)
cbar.ax.text(0.5, 1.025, f'>{top_val:,}', ha='center', va='bottom',
             transform=cbar.ax.transAxes, fontsize=8, color='#555')

ax.set_title('ERA5 Grid Cells over Dublin — Population Density (Census 2022)\n'
             '(cell ID = row,col; row 1 = south, col 1 = west)', fontsize=13, fontweight='bold', pad=14)

plt.tight_layout()
out_file = SCRIPT_DIR / 'era5_population_density_dublin.png'
plt.savefig(out_file, dpi=200, bbox_inches='tight')
print(f"Saved → {out_file}")