from fastapi import FastAPI, Form, File, UploadFile
from typing import Optional
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


@app.post("/report")
async def submit_report(
    condition: str = Form(...),
    severity: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    segment_id: Optional[UUID] = Form(None),
):
    
    response = (
        supabase.table("reports")
        .insert({"segment_id": segment_id, "condition": condition, "severity": severity, "lat": lat, "lng": lng})
        .execute()
    )


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