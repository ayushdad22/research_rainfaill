import json
import urllib.request

# Wicklow mountain cell
CELL = {"south": 53.00, "north": 53.25, "west": -6.50, "east": -6.25}
SAMPLE = 10  # 10x10 = 100 points = the API's max per request

def build_locations():
    locs = []
    for r in range(SAMPLE):
        for c in range(SAMPLE):
            lat = CELL["south"] + (CELL["north"] - CELL["south"]) * (r / (SAMPLE - 1))
            lon = CELL["west"] + (CELL["east"] - CELL["west"]) * (c / (SAMPLE - 1))
            locs.append(f"{lat:.5f},{lon:.5f}")
    return "|".join(locs)

url = f"https://api.opentopodata.org/v1/srtm30m?locations={build_locations()}"
print("Requesting elevation data...")
with urllib.request.urlopen(url) as resp:
    data = json.load(resp)

elevations = [r["elevation"] if r["elevation"] is not None else 0 for r in data["results"]]

with open("elevation.json", "w") as f:
    json.dump({"cell": CELL, "sample": SAMPLE, "elevations": elevations}, f)

print(f"Saved {len(elevations)} points to elevation.json")
print(f"Min: {min(elevations):.0f}m  Max: {max(elevations):.0f}m  Mean: {sum(elevations)/len(elevations):.0f}m")