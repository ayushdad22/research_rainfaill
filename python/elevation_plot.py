"""
Fetch SRTM elevation statistics for each of the 16 ERA5 cells over Dublin.
Writes cell_elevation.json (machine-readable) and prints a table.

Each cell is sampled on a small grid; we report mean, min, max, std, and range.
These stats support the division scheme (mountain vs inland vs coast).
"""
import json
import time
import urllib.request
import statistics

# ERA5 domain: 4x4 cells, each 0.25 deg
LAT_MIN, LON_MIN = 52.75, -6.75
STEP = 0.25
N = 4                 # 4x4 grid of cells
PER_SIDE = 8          # 8x8 = 64 sample points per cell (fits one request)
PAUSE = 1.1           # seconds between requests (API limit: 1/sec)

def cell_points(row, col):
    """Sample points across one cell. row,col are 0-indexed (row 0 = south)."""
    south = LAT_MIN + row * STEP
    west = LON_MIN + col * STEP
    locs = []
    for r in range(PER_SIDE):
        for c in range(PER_SIDE):
            lat = south + STEP * (r / (PER_SIDE - 1))
            lon = west + STEP * (c / (PER_SIDE - 1))
            locs.append((lat, lon))
    return locs

def fetch(locs):
    q = "|".join(f"{lat:.6f},{lon:.6f}" for lat, lon in locs)
    url = "https://api.opentopodata.org/v1/srtm30m?locations=" + q
    with urllib.request.urlopen(url) as resp:
        data = json.load(resp)
    if data["status"] != "OK":
        raise RuntimeError("API returned " + data["status"])
    # SRTM returns null over open sea; treat those as 0 m (sea level)
    return [r["elevation"] if r["elevation"] is not None else 0 for r in data["results"]]

results = {}
print(f"Fetching elevation for 16 cells ({PER_SIDE}x{PER_SIDE} points each)...\n")

for row in range(N):
    for col in range(N):
        cid = f"{row+1},{col+1}"            # 1-indexed ID, matches the map
        elevs = fetch(cell_points(row, col))
        # fraction of sampled points at exactly 0 m = rough "sea share"
        sea_share = sum(1 for e in elevs if e <= 0) / len(elevs)
        results[cid] = {
            "row": row + 1, "col": col + 1,
            "mean": round(statistics.mean(elevs), 1),
            "min": round(min(elevs), 1),
            "max": round(max(elevs), 1),
            "std": round(statistics.pstdev(elevs), 1),
            "range": round(max(elevs) - min(elevs), 1),
            "sea_share": round(sea_share, 2),
        }
        print(f"  cell {cid}: mean={results[cid]['mean']:>6} m  "
              f"max={results[cid]['max']:>6} m  std={results[cid]['std']:>5}  "
              f"sea={int(sea_share*100):>3}%")
        time.sleep(PAUSE)

with open("cell_elevation.json", "w") as f:
    json.dump(results, f, indent=2)

# ---- pretty table sorted by mean elevation (highest first) ----
print("\n" + "=" * 64)
print(f"{'cell':>5} {'mean':>8} {'max':>8} {'std':>7} {'range':>8} {'sea%':>6}")
print("-" * 64)
for cid, s in sorted(results.items(), key=lambda kv: kv[1]["mean"], reverse=True):
    print(f"{cid:>5} {s['mean']:>8} {s['max']:>8} {s['std']:>7} "
          f"{s['range']:>8} {int(s['sea_share']*100):>5}%")
print("=" * 64)
print("\nSaved cell_elevation.json")
print("Hint: high mean + high std = mountain;  ~0 mean + high sea% = coastal/marine;")
print("      low mean + low std on land = flat inland / urban.")