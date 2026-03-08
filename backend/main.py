from fastapi import FastAPI, Form
from uuid import UUID
from dotenv import load_dotenv
from seed import seed
from pydantic import BaseModel
from datetime import datetime, timezone

import os
import asyncio
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


CONDITION_WEIGHTS = {"puddle": 1, "snow": 2, "crack": 3}


def recalculate_risk_score(segment_id: UUID):
    reports = (
        supabase.table("reports")
        .select("condition")
        .eq("segment_id", str(segment_id))
        .execute()
    ).data

    if not reports:
        supabase.table("segments").update({"risk_score": 0.0}).eq("id", str(segment_id)).execute()
        return

    scores = [CONDITION_WEIGHTS.get(r["condition"], 1) for r in reports]
    risk_score = round(sum(scores) / (len(scores) * 3), 4)  # normalised 0–1

    supabase.table("segments").update({"risk_score": risk_score}).eq("id", str(segment_id)).execute()

class ReportRequest(BaseModel):
    condition: str
    lat: float
    lng: float


COOLDOWN_SECONDS = {"snow": 15, "puddle": 30}

async def cooldown_loop():
    while True:
        await asyncio.sleep(10)
        now = datetime.now(timezone.utc)

        reports = (
            supabase.table("reports")
            .select("id, condition, created_at, segment_id")
            .in_("condition", ["snow", "puddle"])
            .execute()
        ).data

        affected_segments = set()
        for report in reports:
            age = (now - datetime.fromisoformat(report["created_at"])).total_seconds()
            if age > COOLDOWN_SECONDS[report["condition"]]:
                supabase.table("reports").delete().eq("id", report["id"]).execute()
                if report["segment_id"]:
                    affected_segments.add(report["segment_id"])

        for segment_id in affected_segments:
            recalculate_risk_score(segment_id)


@app.on_event("startup")
async def start_cooldown_loop():
    asyncio.create_task(cooldown_loop())


@app.post("/report")
async def submit_report(body: ReportRequest):

    result = supabase.rpc("nearest_segment", {"lat": body.lat, "lng": body.lng}).execute()
    segment_id = result.data

    supabase.table("reports").insert(
        {"segment_id": segment_id, "condition": body.condition, "lat": body.lat, "lng": body.lng}
    ).execute()

    recalculate_risk_score(segment_id)


@app.get("/segments")
async def get_segments():
    response = supabase.rpc("get_segments_geojson").execute()
    # print([r for r in response.data if r.get("risk_score", 0) > 0][:5])
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