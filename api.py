# api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from engine import TrafficNode

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

intersections = {
    "Ashram_Chowk": TrafficNode("Ashram_Chowk", neighbors=["Minto_Bridge"]),
    "AIIMS_Junction": TrafficNode("AIIMS_Junction", neighbors=["Ashram_Chowk"]),
    "Minto_Bridge": TrafficNode("Minto_Bridge", neighbors=[])
}

class EdgeTelemetry(BaseModel):
    ambulance_lane: Optional[str] = None
    is_waterlogged: bool = False
    vip_route: Optional[str] = None
    network_status: str = "ONLINE" 
    visibility_index: int = 100
    honk_decibels: Dict[str, int] = {"north": 0, "south": 0, "east": 0, "west": 0}
    heavy_transit_lane: Optional[str] = None 
    wrong_way_alert: Optional[Dict[str, str]] = None 
    densities: Dict[str, int]

@app.post("/api/v1/telemetry/{node_id}")
async def process_data(node_id: str, payload: EdgeTelemetry):
    node = intersections.get(node_id)
    if not node: raise HTTPException(status_code=404)
    macro_state = {k: {"is_waterlogged": v.is_waterlogged} for k, v in intersections.items()}
    node.receive_edge_telemetry(payload.dict(), macro_state)
    action = node.calculate_next_state()
    return {"command": action}

@app.get("/api/v1/network/status")
async def get_network_summary():
    summary = {}
    for id, node in intersections.items():
        summary[id] = {
            "current_green": node.current_green,
            "pressures": {lane: node.lanes[lane] * node.wait_times[lane] for lane in node.lanes},
            "wait_times": node.wait_times,
            "island_time": node.island_time_remaining,
            "densities": node.lanes, # ADDED THIS FOR THE MICRO VIEW TIMERS
            "flags": {
                "v2x": node.emergency_v2x_lane,
                "flood": node.is_waterlogged,
                "neighbor_flood": node.neighbor_flood_alert,
                "vis": node.visibility,
                "net": node.network,
                "transit": node.heavy_transit_lane,
                "wrong": node.wrong_way_data
            }
        }
    return summary