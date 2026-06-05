import json
import time
import urllib.request

CELL = {"south": 53.00, "north": 53.25, "west": -6.50, "east": -6.25}
SAMPLE = 30          # <-- change this (10, 20, 30, 50...)
BATCH = 100          # API max per request
PAUSE = 1.1          # seconds between requests (just over the 1/sec limit)

def all_locations():
    locs = []
    for r in range(SAMPLE):
        for c in range(SAMPLE):
            lat = CELL["south"] + (CELL["north"] - CELL["south"]) * (r / (SAMPLE - 1))
            lon = CELL["west"]  + (CELL["east"]  - CELL["west"])  * (c / (SAMPLE - 1))
            locs.append(f"{lat:.6f},{lon:.6f}")
    return locs

def fetch_batch(batch):
    url = "https://api.opentopodata.org/v1/srtm30m?locations=" + "|".join(batch)
    with urllib.request.urlopen(url) as resp:
        data = json.load(resp)
    if data["status"] != "OK":
        raise RuntimeError("API returned " + data["status"])
    return [r["elevation"] if r["elevation"] is not None else 0 for r in data["results"]]

locs = all_locations()
total = len(locs)
n_requests = (total + BATCH - 1) // BATCH
print(f"Fetching {total} points ({SAMPLE}x{SAMPLE}) in {n_requests} requests...")

elevations = []
for i in range(0, total, BATCH):
    batch = locs[i:i + BATCH]
    elevations.extend(fetch_batch(batch))
    done = len(elevations)
    print(f"  {done}/{total} points")
    if i + BATCH < total:      # don't sleep after the final request
        time.sleep(PAUSE)

with open("elevation.json", "w") as f:
    json.dump({"cell": CELL, "sample": SAMPLE, "elevations": elevations}, f)

print(f"Saved {len(elevations)} points to elevation.json")
print(f"Min: {min(elevations):.0f}m  Max: {max(elevations):.0f}m  Mean: {sum(elevations)/len(elevations):.0f}m")