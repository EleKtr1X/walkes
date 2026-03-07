import os
import requests
from dotenv import load_dotenv
from supabase import create_client
import json 

load_dotenv()

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = """
[out:json][timeout:60];
way["highway"="footway"](43.38,-80.55,43.48,-80.44);
out geom;
"""


def fetch_sidewalks():
    response = requests.post(OVERPASS_URL, data={"data": OVERPASS_QUERY})
    response.raise_for_status()
    return response.json()["elements"]


def build_segments(elements):
    segments = []
    for way in elements:
        coords = [[node["lon"], node["lat"]] for node in way.get("geometry", [])]
        if len(coords) < 2:
            continue
        segments.append({
            "geometry": f"SRID=4326;LINESTRING({', '.join(f'{c[0]} {c[1]}' for c in coords)})",
            "risk_score": 0.0,
            "surface_type": way.get("tags", {}).get("surface"),
        })
    return segments


def seed():
    print("Fetching sidewalks from Overpass API...")
    elements = fetch_sidewalks()
    print(f"Found {len(elements)} ways")

    segments = build_segments(elements)
    print(f"Inserting {len(segments)} segments into Supabase...")

    # Insert in batches of 500 to avoid request size limits
    batch_size = 500
    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        supabase.table("segments").insert(batch).execute()
        print(f"  Inserted {min(i + batch_size, len(segments))}/{len(segments)}")

    print("Done.")
    return len(segments)


if __name__ == "__main__":
    seed()
