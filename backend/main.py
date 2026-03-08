from fastapi import FastAPI, Form, HTTPException
from uuid import UUID
from dotenv import load_dotenv
from seed import seed
from pydantic import BaseModel
from datetime import datetime, timezone

import os
import math
import asyncio
import networkx as nx
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


RISK_MULTIPLIER = 5.0  # risky segment costs up to 6x more than a safe one


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = math.sin(math.radians(lat2 - lat1) / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _snap(v):
    return round(v, 5)  # ~1 m precision, snaps adjacent segment endpoints together


def _build_graph(features):
    G = nx.Graph()
    for feat in features:
        coords = feat["geometry"]["coordinates"]  # [[lng, lat], ...]
        risk = feat["properties"].get("risk_score") or 0.0

        u = (_snap(coords[0][0]), _snap(coords[0][1]))   # (lng, lat)
        v = (_snap(coords[-1][0]), _snap(coords[-1][1]))

        length = sum(
            _haversine_m(coords[i][1], coords[i][0], coords[i + 1][1], coords[i + 1][0])
            for i in range(len(coords) - 1)
        )
        weight = length * (1 + RISK_MULTIPLIER * risk)

        G.add_edge(u, v, weight=weight, coords=coords, risk_score=risk, length=round(length, 2))
    return G


def _nearest_node(nodes, lat, lng):
    best, best_d = None, float("inf")
    for node in nodes:
        d = _haversine_m(lat, lng, node[1], node[0])
        if d < best_d:
            best, best_d = node, d
    return best


@app.get("/route")
async def get_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float):
    response = supabase.rpc("get_segments_geojson").execute()
    features = [
        {"geometry": row["geometry"], "properties": {"id": row["id"], "risk_score": row["risk_score"]}}
        for row in response.data
    ]

    G = _build_graph(features)

    # Use only the largest connected component (the main sidewalk network)
    largest_component = max(nx.connected_components(G), key=len)
    G = G.subgraph(largest_component).copy()

    start_node = _nearest_node(G.nodes(), start_lat, start_lng)
    end_node = _nearest_node(G.nodes(), end_lat, end_lng)

    if start_node == end_node:
        raise HTTPException(status_code=400, detail="Start and end points are too close or resolve to the same location")

    try:
        path_nodes = nx.shortest_path(G, start_node, end_node, weight="weight")
    except nx.NetworkXNoPath:
        raise HTTPException(status_code=404, detail="No path found between the given coordinates")

    path_features = []
    merged_coords = []

    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        edge = G[u][v]
        coords = edge["coords"]

        # Ensure coords run u → v (reverse if needed)
        if not (_snap(coords[0][0]) == u[0] and _snap(coords[0][1]) == u[1]):
            coords = list(reversed(coords))

        merged_coords.extend(coords if not merged_coords else coords[1:])

        path_features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"risk_score": edge["risk_score"], "length_m": edge["length"]},
        })

    return {
        "type": "FeatureCollection",
        "features": path_features,
        "summary": {
            "total_length_m": round(sum(f["properties"]["length_m"] for f in path_features), 2),
            "avg_risk_score": round(sum(f["properties"]["risk_score"] for f in path_features) / len(path_features), 4),
            "geometry": {"type": "LineString", "coordinates": merged_coords},
        },
    }


@app.post("/admin/seed")
async def admin_seed():
    count = seed()
    return {"inserted": count}