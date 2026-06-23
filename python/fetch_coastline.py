"""
Detect coastal cells for the 16 ERA5 cells using SRTM elevation only.
For each cell, samples a grid over the cell PLUS a margin, then derives:
  - sea_share: fraction of IN-CELL points at sea level (0 m) -> composition
  - coast_dist_km: distance from cell centre to nearest land/sea boundary -> position
  - classification: marine / coastal / inland

No external coastline needed. Pure SRTM via OpenTopoData.
Writes cell_coast.json and prints a table.

Run: uv run python fetch_coast.py
"""
import json
import time
import math
import urllib.request

# ERA5 domain: 4x4 cells, each 0.25 deg
LAT_MIN, LON_MIN = 52.75, -6.75
STEP = 0.25
N = 4
GRID = 10            # 10x10 = 100 sample points per request (API max)
MARGIN = 0.10        # degrees of margin around each cell so inland cells "see" the coast
PAUSE = 1.1          # seconds between requests
SEA_THRESHOLD = 1.0  # elevation <= this (m) counts as sea

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def sample_points(row, col):
    """Grid over the cell plus margin. Returns list of (lat, lon) and the in-cell mask."""
    south = LAT_MIN + row * STEP
    west = LON_MIN + col * STEP
    north, east = south + STEP, west + STEP
    s, n = south - MARGIN, north + MARGIN
    w, e = west - MARGIN, east + MARGIN
    pts, in_cell = [], []
    for r in range(GRID):
        for c in range(GRID):
            lat = s + (n - s) * (r / (GRID - 1))
            lon = w + (e - w) * (c / (GRID - 1))
            pts.append((lat, lon))
            in_cell.append(south <= lat <= north and west <= lon <= east)
    return pts, in_cell, (south + north) / 2, (west + east) / 2

def fetch(pts):
    q = "|".join(f"{lat:.6f},{lon:.6f}" for lat, lon in pts)
    url = "https://api.opentopodata.org/v1/srtm30m?locations=" + q
    with urllib.request.urlopen(url) as resp:
        data = json.load(resp)
    if data["status"] != "OK":
        raise RuntimeError("API returned " + data["status"])
    return [r["elevation"] if r["elevation"] is not None else 0 for r in data["results"]]

results = {}
print("Detecting coast for 16 cells (cell + margin, 10x10 each)...\n")

for row in range(N):
    for col in range(N):
        cid = f"{row+1},{col+1}"
        pts, in_cell, clat, clon = sample_points(row, col)
        elevs = fetch(pts)

        is_sea = [e <= SEA_THRESHOLD for e in elevs]

        # sea share: only points INSIDE the cell
        in_cell_sea = [is_sea[i] for i in range(len(pts)) if in_cell[i]]
        sea_share = sum(in_cell_sea) / len(in_cell_sea) if in_cell_sea else 0

        # coastline points: a point that is land but has a sea neighbour, or sea with a land neighbour.
        # we approximate neighbours via grid adjacency in the GRID x GRID layout.
        def idx(r, c): return r * GRID + c
        coast_pts = []
        for r in range(GRID):
            for c in range(GRID):
                i = idx(r, c)
                here = is_sea[i]
                neigh = []
                if r > 0: neigh.append(is_sea[idx(r-1, c)])
                if r < GRID-1: neigh.append(is_sea[idx(r+1, c)])
                if c > 0: neigh.append(is_sea[idx(r, c-1)])
                if c < GRID-1: neigh.append(is_sea[idx(r, c+1)])
                if any(nb != here for nb in neigh):   # boundary between land and sea
                    coast_pts.append(pts[i])

        # distance from cell centre to nearest coastline point
        if coast_pts:
            coast_dist = min(haversine_km(clat, clon, p[0], p[1]) for p in coast_pts)
        else:
            coast_dist = None   # no coast found within the sampled margin

        # classification
        if sea_share >= 0.85:
            cls = "marine"
        elif coast_dist is not None and coast_dist <= 8:   # within ~8 km of coast
            cls = "coastal"
        else:
            cls = "inland"

        results[cid] = {
            "row": row+1, "col": col+1,
            "sea_share": round(sea_share, 2),
            "coast_dist_km": round(coast_dist, 1) if coast_dist is not None else None,
            "class": cls,
        }
        dist_str = f"{coast_dist:5.1f}" if coast_dist is not None else "  >margin"
        print(f"  cell {cid}: sea={int(sea_share*100):>3}%  "
              f"coast_dist={dist_str} km  -> {cls}")
        time.sleep(PAUSE)

with open("cell_coast.json", "w") as f:
    json.dump(results, f, indent=2)

# table sorted by coast distance (nearest first)
print("\n" + "="*56)
print(f"{'cell':>5} {'sea%':>6} {'coast_km':>10} {'class':>9}")
print("-"*56)
def sortkey(kv):
    d = kv[1]["coast_dist_km"]
    return (d if d is not None else 1e9)
for cid, s in sorted(results.items(), key=sortkey):
    d = s["coast_dist_km"]
    dstr = f"{d:.1f}" if d is not None else ">margin"
    print(f"{cid:>5} {int(s['sea_share']*100):>5}% {dstr:>10} {s['class']:>9}")
print("="*56)
print("\nSaved cell_coast.json")
print("marine = mostly sea; coastal = land within ~8km of coast; inland = further.")
print("Tune SEA_THRESHOLD, the 8km cutoff, and MARGIN to taste.")