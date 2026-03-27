from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import datetime
import random
import asyncio
import math
from sqlalchemy.orm import Session
import json
import threading
import uuid
import paho.mqtt.client as mqtt

# Database imports
import database
import models

# Create database tables (if they don't exist yet)
models.database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="India Innovate Traffic Backend")

# Allow all origins so Vercel and any frontend can reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Stream Status
STREAM_ACTIVE = False

# ─── GHOST NODE SIMULATION (23 simulated intersections) ─────────────────────
GHOST_NODE_NAMES = [
    "Connaught Place", "South Ext", "Dhaula Kuan", "Kashmere Gate",
    "Ashram Chowk", "Laxmi Nagar", "Karol Bagh", "Moolchand",
    "Raja Garden", "Akshardham", "Lajpat Nagar", "Dwarka",
    "Rohini", "Vasant Kunj", "Saket", "Nehru Place",
    "Hauz Khas", "Chandni Chowk", "Pitampura", "Janakpuri",
    "Okhla", "Vasant Vihar", "Greater Kailash",
]
LANE_IDS = ["01", "02", "03", "04"]
GHOST_NODES: dict = {}   # populated at startup


def init_ghost_nodes():
    """Seed 23 ghost nodes with random but plausible starting state."""
    global GHOST_NODES
    for idx, name in enumerate(GHOST_NODE_NAMES):
        node_id = f"Node_{idx + 3}"          # Node_3 … Node_25
        active_lane = random.choice(LANE_IDS)
        lanes = {}
        for lid in LANE_IDS:
            is_green = lid == active_lane
            lanes[lid] = {
                "density": random.randint(20, 70),
                "wait_time": 0 if is_green else random.randint(5, 30),
                "is_green": is_green,
            }
        GHOST_NODES[node_id] = {
            "name": name,
            "lanes": lanes,
            "active_green_lane": active_lane,
            "remaining_green_time": random.randint(15, 45),
        }


def _switch_light(node: dict):
    """Pressure-based light switch when remaining_green_time hits 0."""
    # Calculate pressure for every RED lane
    best_lane = None
    best_pressure = -1
    for lid in LANE_IDS:
        lane = node["lanes"][lid]
        if lane["is_green"]:
            continue
        pressure = lane["density"] * lane["wait_time"]
        if pressure > best_pressure:
            best_pressure = pressure
            best_lane = lid

    if best_lane is None:
        best_lane = random.choice(LANE_IDS)

    # Turn old green lane red
    old_green = node["active_green_lane"]
    node["lanes"][old_green]["is_green"] = False

    # Calculate new green time using the exponential formula
    new_lane = node["lanes"][best_lane]
    d = new_lane["density"]
    w = new_lane["wait_time"]
    base = 15 + ((d / 100) ** 1.5) * 30
    wait_mult = 1.0 + (0.5 * (w / 180))
    final_green = int(max(15, min(45, base * wait_mult)))

    # Activate new green lane
    new_lane["is_green"] = True
    new_lane["wait_time"] = 0
    node["active_green_lane"] = best_lane
    node["remaining_green_time"] = final_green


async def ghost_physics_loop():
    """1-second tick that updates every ghost node's lanes."""
    while True:
        for node in GHOST_NODES.values():
            for lid in LANE_IDS:
                lane = node["lanes"][lid]
                if lane["is_green"]:
                    # Green lane: density drains, wait stays 0
                    lane["density"] = max(0, lane["density"] - random.randint(2, 5))
                    lane["wait_time"] = 0
                else:
                    # Red lane: density slowly builds, wait ticks up
                    lane["density"] = min(100, lane["density"] + random.randint(0, 3))
                    if lane["density"] > 0:
                        lane["wait_time"] += 1

            node["remaining_green_time"] -= 1
            if node["remaining_green_time"] <= 0:
                _switch_light(node)

        await asyncio.sleep(1)

# --- MQTT BACKGROUND WORKER ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "mcd/traffic/#"

def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    print(f"[{datetime.datetime.utcnow().isoformat()}] Connected to HiveMQ Broker! Listening on {MQTT_TOPIC}")
    client.subscribe(MQTT_TOPIC)

def on_mqtt_message(client, userdata, msg):
    global STREAM_ACTIVE
    try:
        payload_str = msg.payload.decode("utf-8")
        raw_data = json.loads(payload_str)
        
        node_id = raw_data.get("nodeId")
        if not node_id:
            return
            
        # First payload received, trigger the global video stream
        if not STREAM_ACTIVE:
            STREAM_ACTIVE = True
            print(f"[{datetime.datetime.utcnow().isoformat()}] FIRST PAYLOAD TRIGGER: STREAM_ACTIVE = True")
            
        events = raw_data.get("critical_events_this_minus_cycle") or raw_data.get("critical_events_this_minute", {})
        db = database.SessionLocal()
        db_metrics = models.TrafficMetricsRecord(
            node_id=node_id,
            timestamp=raw_data.get("timestamp", datetime.datetime.utcnow().isoformat()),
            state_snapshot=raw_data.get("state_snapshot", {}),
            lane_metrics=raw_data.get("lane_metrics", {}),
            critical_events_this_minute=events
        )
        db.add(db_metrics)
        db.commit()
        db.close()
        print(f"[{datetime.datetime.utcnow().isoformat()}] MQTT INGEST SUCCESS: Node {node_id}")
    except Exception as e:
        print(f"[MQTT] ERROR processing message: {e}")

def start_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "india-innovate-backend-" + str(uuid.uuid4()))
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"MQTT Connection Failed: {e}")

@app.on_event("startup")
async def startup_event():
    # Run MQTT entirely in the background outside of FastAPI event loop
    mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()
    # Seed and start ghost node physics simulation
    init_ghost_nodes()
    asyncio.create_task(ghost_physics_loop())

# --- Pydantic Data Models (Input Validation) ---
class DeviceHealth(BaseModel):
    deviceId: str
    type: str
    timestamp: datetime.datetime
    firmware: str
    health: dict
    selfReportedIssues: List[str]

class StateSnapshot(BaseModel):
    active_phase: str
    engine_state: str
    box_gridlock_pct: float
    trigger: str | None = None

class LaneMetric(BaseModel):
    queue_N: int
    wait_time_T: int
    exit_flow: int

class CriticalEvents(BaseModel):
    evp_overrides: int
    gridlock_triggers: int

class TrafficPayload(BaseModel):
    nodeId: str
    timestamp: datetime.datetime
    state_snapshot: StateSnapshot
    lane_metrics: dict[str, LaneMetric]
    critical_events_this_minute: CriticalEvents | None = None
    critical_events_this_minus_cycle: CriticalEvents | None = None

class OverrideRequest(BaseModel):
    nodeId: str
    lane: str
    state: str
    reason: str

# --- API Routes ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend is running with PostgreSQL support"}

@app.post("/api/health")
def ingest_health(data: DeviceHealth, db: Session = Depends(database.get_db)):
    """
    Endpoint for Jetson devices to report their hardware health/uptime.
    Saves the payload to PostgreSQL.
    """
    db_record = models.DeviceHealthRecord(
        device_id=data.deviceId,
        device_type=data.type,
        timestamp=data.timestamp,
        firmware=data.firmware,
        health_data=data.health,
        issues=data.selfReportedIssues
    )
    db.add(db_record)
    db.commit()
    return {"success": True, "message": f"Health data saved for {data.deviceId}"}

@app.post("/api/traffic")
def ingest_traffic(data: TrafficPayload, db: Session = Depends(database.get_db)):
    """
    Endpoint for Jetson devices to send real-time traffic inference results.
    Saves the metrics to PostgreSQL.
    """
    global STREAM_ACTIVE
    if not STREAM_ACTIVE:
        STREAM_ACTIVE = True
        print(f"[{datetime.datetime.utcnow().isoformat()}] FIRST HTTP PAYLOAD TRIGGER: STREAM_ACTIVE = True")

    events = data.critical_events_this_minus_cycle or data.critical_events_this_minute
    if not events:
        events = CriticalEvents(evp_overrides=0, gridlock_triggers=0)

    db_metrics = models.TrafficMetricsRecord(
        node_id=data.nodeId,
        timestamp=data.timestamp,
        state_snapshot=data.state_snapshot.dict(),
        lane_metrics={k: v.dict() for k, v in data.lane_metrics.items()},
        critical_events_this_minute=events.dict()
    )
    db.add(db_metrics)
    db.commit()
    return {"success": True, "message": f"Traffic metrics saved for {data.nodeId}"}

@app.post("/api/override")
def override_signal(data: OverrideRequest):
    """
    Endpoint mapping frontend override command directly to Jetson Edge.
    In real life this would push an MQTT message back down to the edge node.
    """
    print(f"[{datetime.datetime.utcnow().isoformat()}] COMMAND TO JETSON {data.nodeId} -> Lane {data.lane} to {data.state}. Reason: {data.reason}")
    return {"success": True, "message": "Signal transmitted to Edge Jetson device."}

@app.get("/api/devices")
def get_devices(db: Session = Depends(database.get_db)):
    """Returns the most recent health ping for all devices"""
    # Quick, simple aggregation for demo purposes
    devices = db.query(models.DeviceHealthRecord).order_by(models.DeviceHealthRecord.timestamp.desc()).limit(10).all()
    
    frontend_devices = []
    seen = set()
    for d in devices:
        if d.device_id not in seen:
            seen.add(d.device_id)
            frontend_devices.append({
                "id": d.device_id,
                "type": d.device_type,
                "status": "online" if "High latency detected" not in d.issues else "degraded",
                "uptime": "99.9%",  # placeholder for demo
                "lastPing": "Just now",
                "firmware": d.firmware,
                "issues": d.issues
            })
    return frontend_devices

@app.get("/api/traffic")
def get_latest_traffic(db: Session = Depends(database.get_db)):
    """Returns the latest traffic state for intersections"""
    metrics = db.query(models.TrafficMetricsRecord).order_by(models.TrafficMetricsRecord.timestamp.desc()).limit(20).all()
    
    frontend_traffic = []
    seen = set()
    for m in metrics:
        if m.node_id not in seen:
            seen.add(m.node_id)
            
            # The dashboard consumes a flattened API. We calculate the entire intersection's aggregated status:
            l_mets = m.lane_metrics or {}
            state = m.state_snapshot or {}
            
            queue_size = sum(lm.get("queue_N", 0) for lm in l_mets.values()) if l_mets else 0
            avg_wait = sum(lm.get("wait_time_T", 0) for lm in l_mets.values()) / max(len(l_mets), 1) if l_mets else 0
            
            gridlock_p = state.get("box_gridlock_pct", 0) / 100.0 if state else 0
            
            # Calculate inferred hourly volume:
            # Base flow: ~1200 vehicles/lane/hour for green light. We have 4 lanes.
            # If wait_time is high and queue_size is high, congestion is high.
            # We estimate vehicles passed per hour based on current queue density + gridlock.
            # A completely full intersection (queue ~400 total) at high gridlock might push 8000+ vehicles/hr at peak.
            # We use a formula: Base flow + (Queue size * turnover_rate)
            turnover_rate = 60 / max(1, (avg_wait / 2)) # Estimated cycles per hour
            estimated_volume = int((queue_size * turnover_rate) + (gridlock_p * 2000))
            
            # Add some noise to make it realistic for the Most Busiest ranking scale
            # (which ranges from 2000 to 14000 in the static data)
            vehicles_passed = max(1200, estimated_volume * 15) # Scale up to match dashboard norms

            frontend_traffic.append({
                "nodeId": m.node_id,
                "vehiclesPassed": vehicles_passed,
                "status": "Red" if gridlock_p > 0.6 else "Yellow" if gridlock_p > 0.3 else "Green",
                "congestionLevel": gridlock_p,
                "avgWaitTime": int(avg_wait)
            })
    return frontend_traffic

@app.get("/api/network-status")
def get_network_status():
    """Return 25-node unified status: 2 hero nodes + 23 physics-simulated ghost nodes."""
    nodes = []

    # ── Hero Nodes (Node_1 ITO, Node_2 AIIMS) — untouched, same as before ──
    for i in range(1, 3):
        nodes.append({
            "node_id": f"Node_{i}",
            "hardware_status": "ONLINE",
            "lanes": {
                "N": {"density": 85, "wait_time": random.randint(10, 55)}
            },
        })

    # ── Ghost Nodes (Node_3 … Node_25) — driven by physics loop ──
    for node_id, node in GHOST_NODES.items():
        # Pick the highest-density lane as the representative 'N' value for the frontend
        best_lane = max(node["lanes"].values(), key=lambda l: l["density"])
        nodes.append({
            "node_id": node_id,
            "hardware_status": "ONLINE",
            "lanes": {
                "N": {
                    "density": best_lane["density"],
                    "wait_time": best_lane["wait_time"],
                }
            },
            "active_green": node["active_green_lane"],
            "green_timer": node["remaining_green_time"],
        })

    return {"status": "success", "nodes": nodes}

@app.get("/api/traffic/{node_id}")
def get_node_traffic(node_id: str, db: Session = Depends(database.get_db)):
    """Returns the raw detailed metric payload for a specific intersection"""
    record = db.query(models.TrafficMetricsRecord).filter(models.TrafficMetricsRecord.node_id == node_id).order_by(models.TrafficMetricsRecord.timestamp.desc()).first()
    if not record:
        # Return empty skeleton so the frontend doesn't break while waiting for first MQTT packet
        return {
            "nodeId": node_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "state_snapshot": {"active_phase": f"{node_id}-01", "engine_state": "AWAITING_DATA", "box_gridlock_pct": 0.0},
            "lane_metrics": {},
            "critical_events": {"evp_overrides": 0, "gridlock_triggers": 0}
        }
    
    return {
        "nodeId": record.node_id,
        "timestamp": record.timestamp.isoformat(),
        "state_snapshot": record.state_snapshot,
        "lane_metrics": record.lane_metrics,
        "critical_events": record.critical_events_this_minute
    }

@app.get("/api/stream-status")
def get_stream_status():
    """Endpoint for frontend to poll if actual camera simulation data has started arriving"""
    return {"active": STREAM_ACTIVE}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
