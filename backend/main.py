from fastapi import FastAPI, Form
from uuid import UUID
from dotenv import load_dotenv
from seed import seed
from pydantic import BaseModel

import os
from supabase import create_client, Client

from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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

class ReportRequest(BaseModel):
    condition: str
    severity: str
    lat: float
    lng: float

@app.post("/report")
async def submit_report(body: ReportRequest):

    result = supabase.rpc("nearest_segment", {"lat": body.lat, "lng": body.lng}).execute()
    segment_id = result.data

    supabase.table("reports").insert(
        {"segment_id": segment_id, "condition": body.condition, "severity": body.severity, "lat": body.lat, "lng": body.lng}
    ).execute()

    recalculate_risk_score(segment_id)


@app.get("/segments")
async def get_segments():
    response = supabase.rpc("get_segments_geojson").limit(17500).execute()
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