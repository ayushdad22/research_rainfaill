"""
Plot the 16 ERA5 cells over a Dublin basemap, coloured by coastal classification
(marine / coastal / inland) from cell_coast.json, with sea-share and coast distance
labelled on each cell.

Requires cell_coast.json (produced by fetch_coast.py).
Run:  uv run python plot_cells_coast.py
"""
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
import contextily as cx
from pyproj import Transformer

# ---- ERA5 domain ----
LAT_MIN, LON_MIN = 52.75, -6.75
STEP = 0.25
N = 4

# ---- load coast json ----
try:
    with open("cell_coast.json") as f:
        coast = json.load(f)
except FileNotFoundError:
    raise SystemExit("cell_coast.json not found. Run fetch_coast.py first.")

# colours per class
CLASS_COLOR = {
    "marine":  "#2c6fa3",   # blue
    "coastal": "#4fb3c4",   # teal
    "inland":  "#8bbf6a",   # green
}

to_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

fig, ax = plt.subplots(figsize=(11, 11))

for row in range(N):           # 0 = south
    for col in range(N):       # 0 = west
        cid = f"{row+1},{col+1}"
        s = coast.get(cid)

        south = LAT_MIN + row * STEP
        west = LON_MIN + col * STEP
        north, east = south + STEP, west + STEP

        x0, y0 = to_merc.transform(west, south)
        x1, y1 = to_merc.transform(east, north)

        cls = s["class"] if s else None
        face = CLASS_COLOR.get(cls, "#999999")

        rect = patches.Rectangle(
            (x0, y0), x1 - x0, y1 - y0,
            linewidth=1.5, edgecolor="black",
            facecolor=face, alpha=0.5
        )
        ax.add_patch(rect)

        lx, ly = to_merc.transform((west + east) / 2, (south + north) / 2)
        if s:
            d = s["coast_dist_km"]
            dstr = f"{d:.0f} km" if d is not None else ">margin"
            label = (f"{cid}\n"
                     f"{cls.upper()}\n"
                     f"sea {int(s['sea_share']*100)}%\n"
                     f"coast {dstr}")
        else:
            label = f"{cid}\n(no data)"

        ax.text(lx, ly, label, ha="center", va="center",
                fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", alpha=0.82))

# view window
xmin, ymin = to_merc.transform(LON_MIN, LAT_MIN)
xmax, ymax = to_merc.transform(LON_MIN + N * STEP, LAT_MIN + N * STEP)
pad = (xmax - xmin) * 0.06
ax.set_xlim(xmin - pad, xmax + pad)
ax.set_ylim(ymin - pad, ymax + pad)

cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik)
ax.set_axis_off()
ax.set_title("ERA5 Cells by coastal classification (SRTM sea-share + distance)", fontsize=13)

# legend
legend_items = [
    Line2D([0], [0], marker='s', color='none', markerfacecolor=CLASS_COLOR["marine"],
           markeredgecolor='black', markersize=14, label='Marine (mostly sea)'),
    Line2D([0], [0], marker='s', color='none', markerfacecolor=CLASS_COLOR["coastal"],
           markeredgecolor='black', markersize=14, label='Coastal (land near sea)'),
    Line2D([0], [0], marker='s', color='none', markerfacecolor=CLASS_COLOR["inland"],
           markeredgecolor='black', markersize=14, label='Inland'),
]
ax.legend(handles=legend_items, loc='lower left', fontsize=10, framealpha=0.9)

plt.tight_layout()
plt.savefig("era5_cells_coast.png", dpi=200, bbox_inches="tight")
print("Saved era5_cells_coast.png")