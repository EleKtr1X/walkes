from fastapi import FastAPI, Form
from uuid import UUID
from dotenv import load_dotenv
from seed import seed

import os
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)


app = FastAPI()


SEVERITY_WEIGHTS = {"low": 1, "medium": 2, "high": 3}


def recalculate_risk_score(segment_id: UUID):
    reports = (
        supabase.table("reports")
        .select("severity")
        .eq("segment_id", str(segment_id))
        .execute()
    ).data

    if not reports:
        return

    scores = [SEVERITY_WEIGHTS.get(r["severity"], 1) for r in reports]
    risk_score = round(sum(scores) / (len(scores) * 3), 4)  # normalised 0–1

    supabase.table("segments").update({"risk_score": risk_score}).eq("id", str(segment_id)).execute()


@app.post("/report")
async def submit_report(
    condition: str = Form(...),
    severity: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
):

    result = supabase.rpc("nearest_segment", {"lat": lat, "lng": lng}).execute()
    segment_id = result.data

    supabase.table("reports").insert(
        {"segment_id": segment_id, "condition": condition, "severity": severity, "lat": lat, "lng": lng}
    ).execute()

    recalculate_risk_score(segment_id)


@app.get("/segments")
async def get_segments():
    response = supabase.rpc("get_segments_geojson").execute()
    features = []
    for row in response.data:
        new = {
            "type": "Feature",
            "geometry": row["geometry"],
            "properties": {
                "id": row["id"],
                "risk_score": row["risk_score"],
                "surface_type": row["surface_type"],
            },
        }

        features.append(new)

    return {"type": "FeatureCollection", "features": features}


@app.post("/admin/seed")
async def admin_seed():
    count = seed()
    return {"inserted": count}