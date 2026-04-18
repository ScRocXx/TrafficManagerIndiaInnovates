import asyncio
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from mqtt_handler import start_mqtt_client
from evp_engine import EVPTrafficEngine
from contextlib import asynccontextmanager

engine = EVPTrafficEngine(
    intersection_id="284501", 
    lane_ids=["284501-01", "284501-02", "284501-03", "284501-04"]
)

LATEST_FRAMES = {}
LATEST_LATENCY = {"yolo_ms": 0, "bev_ms": 0, "engine_ms": 0}

# ── Ambulance Simulation State ────────────────────────────────────
SIM_STATE = {
    "active": False,
    "lane": None,
    "step": 0,
    "total_steps": 0,
    "distance_m": 0,
}

async def ambulance_simulation(lane: str, steps: int = 30):
    """
    Background task: simulates an ambulance approaching the intersection.
    Directly calls engine.ingest_v2x() each second with decreasing distance.
    """
    START_DIST = 500.0  # meters
    dist_step = START_DIST / steps

    SIM_STATE["active"] = True
    SIM_STATE["lane"] = lane
    SIM_STATE["total_steps"] = steps
    
    print(f"[SIM] 🚨 Ambulance dispatched on {lane} — {steps} steps from {START_DIST:.0f}m")

    for i in range(steps):
        current_dist = START_DIST - (dist_step * (i + 1))
        current_dist = max(current_dist, 1.0)  # Never quite reach 0
        
        SIM_STATE["step"] = i + 1
        SIM_STATE["distance_m"] = current_dist
        
        engine.ingest_v2x({
            "lane": lane,
            "distance": current_dist,
            "speed": 40,
            "vip": False,
        })
        
        print(f"[SIM] 📡 {lane} — Step {i+1}/{steps} — Distance: {current_dist:.0f}m")
        await asyncio.sleep(1)

    # Ambulance has arrived — clear the V2X data after a brief hold
    print(f"[SIM] ✅ Ambulance arrived at intersection on {lane}!")
    await asyncio.sleep(3)

    # Clear ambulance data from the lane
    engine.lanes[lane]["amb_dist"] = None
    engine.lanes[lane]["amb_speed"] = 0
    engine.lanes[lane]["vip"] = False
    
    SIM_STATE["active"] = False
    SIM_STATE["lane"] = None
    SIM_STATE["step"] = 0
    SIM_STATE["distance_m"] = 0
    print(f"[SIM] 🏁 Simulation complete. Ambulance data cleared.")

async def engine_ticker():
    """Background task: ticks the engine state machine every 1 second."""
    while True:
        engine.tick_wait_times()
        await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start MQTT + Engine ticker
    mqtt_client = start_mqtt_client(engine)
    ticker_task = asyncio.create_task(engine_ticker())
    yield
    # Shutdown
    ticker_task.cancel()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

app = FastAPI(title="Northern Blades Core API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════════════════════════════
#  AMBULANCE SIMULATOR ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@app.post("/api/simulate/ambulance")
async def simulate_ambulance(request: Request):
    """Dispatch a simulated ambulance approaching a target lane."""
    if SIM_STATE["active"]:
        return {"status": "error", "message": "Simulation already running", "sim": SIM_STATE}

    body = await request.json()
    lane = body.get("lane", "284501-01")
    steps = body.get("steps", 30)

    # Validate lane
    valid_lanes = list(engine.lanes.keys())
    if lane not in valid_lanes:
        return {"status": "error", "message": f"Invalid lane. Choose from: {valid_lanes}"}

    # Fire and forget — runs in the background
    asyncio.create_task(ambulance_simulation(lane, steps))
    return {"status": "ok", "message": f"Ambulance dispatched on {lane}", "steps": steps}

@app.get("/api/simulate/status")
def simulate_status():
    """Check current ambulance simulation state."""
    return SIM_STATE

# ══════════════════════════════════════════════════════════════════
#  STANDARD API ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@app.post("/api/telemetry")
async def telemetry(request: Request):
    """Edge camera telemetry ingestion (does NOT reset state)."""
    payload = await request.json()
    engine.ingest_telemetry(payload)
    lane = payload.get("lane")
    if "frame_b64" in payload:
        LATEST_FRAMES[lane] = payload["frame_b64"]
    return {"status": "Telemetry accepted", "lane": lane}

@app.post("/api/override")
async def override_telemetry(request: Request):
    """Manual sandbox override (resets state for testing)."""
    payload = await request.json()
    engine.ingest_sandbox(payload)
    return {"status": "Manual Sandbox Evaluated"}

@app.post("/api/box")
async def box_density(request: Request):
    """5th Camera (God's Eye) box density ingestion."""
    payload = await request.json()
    engine.ingest_box_density(payload)
    return {
        "status": "Box density updated",
        "box_density": engine.box_density,
        "box_camera_ok": engine.box_camera_ok,
    }

@app.get("/api/state")
def get_full_state():
    """Return the complete engine state for dashboards."""
    return engine.get_current_state()

@app.post("/api/latency")
async def latency_telemetry(request: Request):
    """Receive pipeline latency metrics from the edge demo node."""
    global LATEST_LATENCY
    LATEST_LATENCY = await request.json()
    return {"status": "Latency updated"}

@app.get("/")
def read_root():
    return {"status": "Fluid Mass Engine Online", "active_green": engine.get_active_green()}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            state = engine.get_current_state()
            state["frames"] = LATEST_FRAMES
            state["latency"] = LATEST_LATENCY
            state["sim"] = SIM_STATE  # Include sim state for dashboard
            await websocket.send_json(state)
            await asyncio.sleep(1)
    except Exception as e:
        print("[WS] Client disconnected")
