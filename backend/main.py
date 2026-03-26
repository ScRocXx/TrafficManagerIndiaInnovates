from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import datetime
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

# Allow Next.js (port 3000) to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000","http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MQTT BACKGROUND WORKER ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "mcd/traffic/#"

def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    print(f"[{datetime.datetime.utcnow().isoformat()}] Connected to HiveMQ Broker! Listening on {MQTT_TOPIC}")
    client.subscribe(MQTT_TOPIC)

def on_mqtt_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode("utf-8")
        raw_data = json.loads(payload_str)
        
        node_id = raw_data.get("nodeId")
        if not node_id:
            return
            
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
        pass # Ignore malformed packets quietly

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
def startup_event():
    # Run MQTT entirely in the background outside of FastAPI event loop
    mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()

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
            
            frontend_traffic.append({
                "nodeId": m.node_id,
                "vehiclesPassed": queue_size, # using queue volume proxy for demo 
                "status": "Red" if gridlock_p > 0.6 else "Yellow" if gridlock_p > 0.3 else "Green",
                "congestionLevel": gridlock_p,
                "avgWaitTime": int(avg_wait)
            })
    return frontend_traffic

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
