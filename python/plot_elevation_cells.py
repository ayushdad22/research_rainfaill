"""
Plot the 16 ERA5 cells over a Dublin basemap, coloured by mean elevation,
with elevation stats labelled on each cell.

Requires cell_elevation.json (produced by fetch_cell_elevation.py).
Run:  uv run python plot_cells_elevation.py
"""
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import cm, colors
import contextily as cx
from pyproj import Transformer

# ---- ERA5 domain ----
LAT_MIN, LON_MIN = 52.75, -6.75
STEP = 0.25
N = 4  # 4x4 cells

# ---- load elevation json ----
try:
    with open("cell_elevation.json") as f:
        elev = json.load(f)
except FileNotFoundError:
    raise SystemExit("cell_elevation.json not found. Run fetch_cell_elevation.py first.")

# colour scale based on mean elevation across all cells
means = [v["mean"] for v in elev.values()]
vmin, vmax = min(means), max(means)
norm = colors.Normalize(vmin=vmin, vmax=vmax)
cmap = cm.get_cmap("terrain")  # low=green/blue, high=brown/white

to_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

fig, ax = plt.subplots(figsize=(11, 11))

for row in range(N):           # 0 = south
    for col in range(N):       # 0 = west
        cid = f"{row+1},{col+1}"
        stats = elev.get(cid)

        south = LAT_MIN + row * STEP
        west = LON_MIN + col * STEP
        north, east = south + STEP, west + STEP

        x0, y0 = to_merc.transform(west, south)
        x1, y1 = to_merc.transform(east, north)

        if stats:
            face = cmap(norm(stats["mean"]))
            alpha = 0.55
        else:
            face = (0.5, 0.5, 0.5, 1)
            alpha = 0.3

        rect = patches.Rectangle(
            (x0, y0), x1 - x0, y1 - y0,
            linewidth=1.5, edgecolor="black",
            facecolor=face, alpha=alpha
        )
        ax.add_patch(rect)

        # label: cell id + elevation stats
        lx, ly = to_merc.transform((west + east) / 2, (south + north) / 2)
        if stats:
            label = (f"{cid}\n"
                     f"mean {stats['mean']:.0f}m\n"
                     f"max {stats['max']:.0f}m\n"
                     f"std {stats['std']:.0f}")
            if stats.get("sea_share", 0) >= 0.5:
                label += f"\nsea {int(stats['sea_share']*100)}%"
        else:
            label = f"{cid}\n(no data)"

        ax.text(lx, ly, label, ha="center", va="center",
                fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", alpha=0.8))

# view window
xmin, ymin = to_merc.transform(LON_MIN, LAT_MIN)
xmax, ymax = to_merc.transform(LON_MIN + N * STEP, LAT_MIN + N * STEP)
pad = (xmax - xmin) * 0.06
ax.set_xlim(xmin - pad, xmax + pad)
ax.set_ylim(ymin - pad, ymax + pad)

cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik)
ax.set_axis_off()
ax.set_title("ERA5 Cells coloured by mean elevation (SRTM via OpenTopoData)", fontsize=13)

# colour bar
sm = cm.ScalarMappable(norm=norm, cmap=cmap)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.02)
cbar.set_label("Mean elevation (m)")

plt.tight_layout()
plt.savefig("era5_cells_elevation.png", dpi=200, bbox_inches="tight")
print("Saved era5_cells_elevation.png")