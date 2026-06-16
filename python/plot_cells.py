import matplotlib.pyplot as plt
import matplotlib.patches as patches
import contextily as cx
from pyproj import Transformer

LAT_MIN, LAT_MAX = 52.75, 53.75
LON_MIN, LON_MAX = -6.75, -5.75
STEP = 0.25
N = 4 

to_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

fig, ax = plt.subplots(figsize=(10, 10))

for row in range(N):           
    for col in range(N):       
        south = LAT_MIN + row * STEP
        west = LON_MIN + col * STEP
        north, east = south + STEP, west + STEP

        x0, y0 = to_merc.transform(west, south)
        x1, y1 = to_merc.transform(east, north)

        rect = patches.Rectangle(
            (x0, y0), x1 - x0, y1 - y0,
            linewidth=1.5, edgecolor="black", facecolor="none", alpha=0.9
        )
        ax.add_patch(rect)

        cx_lon, cy_lat = (west + east) / 2, (south + north) / 2
        lx, ly = to_merc.transform(cx_lon, cy_lat)
        ax.text(lx, ly, f"{row+1},{col+1}",
                ha="center", va="center", fontsize=11, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", alpha=0.85))

xmin, ymin = to_merc.transform(LON_MIN, LAT_MIN)
xmax, ymax = to_merc.transform(LON_MAX, LAT_MAX)
pad = (xmax - xmin) * 0.08
ax.set_xlim(xmin - pad, xmax + pad)
ax.set_ylim(ymin - pad, ymax + pad)

cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik)

ax.set_axis_off()
ax.set_title("ERA5 Grid Cells over Dublin (cell ID = row,col; row 1 = south, col 1 = west)",
             fontsize=12)

plt.tight_layout()
plt.savefig("era5_cells_dublin.png", dpi=200, bbox_inches="tight")
print("Saved era5_cells_dublin.png")