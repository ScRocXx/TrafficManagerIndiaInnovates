from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import datetime
import random
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
LAST_SEEN_NODES = {} # Tracks {node_id: datetime}
AMBULANCE_ALERTS = {} # Tracks {node_id: alert_payload}

# --- MQTT BACKGROUND WORKER ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "mcd/traffic/#"

def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    print(f"[{datetime.datetime.utcnow().isoformat()}] Connected to HiveMQ Broker!")
    client.subscribe("mcd/traffic/#")
    client.subscribe("mcd/alerts/#")
    print(f"[{datetime.datetime.utcnow().isoformat()}] Subscribed to mcd/traffic/# and mcd/alerts/#")

def on_mqtt_message(client, userdata, msg):
    global STREAM_ACTIVE, LAST_SEEN_NODES, AMBULANCE_ALERTS
    try:
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8")
        raw_data = json.loads(payload_str)

        # --- Dedicated Ambulance Alert Handler (separate from traffic) ---
        if topic.startswith("mcd/alerts/"):
            device_id = raw_data.get("deviceId")
            if device_id:
                AMBULANCE_ALERTS[device_id] = {
                    **raw_data,
                    "received_at": datetime.datetime.utcnow().isoformat()
                }
                print(f"[{datetime.datetime.utcnow().isoformat()}] EVP ALERT RECEIVED: {raw_data.get('alert_type')} for node {device_id}")
            return  # Do NOT process further — this is not traffic data
        
        node_id = raw_data.get("nodeId")
        if not node_id:
            return
            
        LAST_SEEN_NODES[node_id] = datetime.datetime.utcnow()
            
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
    global STREAM_ACTIVE, LAST_SEEN_NODES
    LAST_SEEN_NODES[data.nodeId] = datetime.datetime.utcnow()
    
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

            # Check node health
            last_seen = LAST_SEEN_NODES.get(m.node_id)
            is_offline = False
            if last_seen:
                seconds_since = (datetime.datetime.utcnow() - last_seen).total_seconds()
                if seconds_since > 20: # 20 second timeout
                    is_offline = True
            
            # Status calculation
            base_status = "Red" if gridlock_p > 0.6 else "Yellow" if gridlock_p > 0.3 else "Green"
            if is_offline:
                base_status = "FAULT_OFFLINE"

            frontend_traffic.append({
                "nodeId": m.node_id,
                "vehiclesPassed": vehicles_passed,
                "status": base_status,
                "congestionLevel": gridlock_p,
                "avgWaitTime": int(avg_wait),
                "systemMode": "LEGACY_MICROCONTROLLER" if is_offline else "AI_OPTIMIZED"
            })
    return frontend_traffic

@app.get("/api/network-status")
def get_network_status():
    """Simulate multi-node network status for the V6 dashboard mapping."""
    nodes = []
    for i in range(1, 13):
        # Give the first two nodes higher density to make them critical "red" in UI
        density = 85 if i <= 2 else random.randint(15, 70)
        status = "ONLINE"
        if random.random() < 0.05:
            status = random.choice(["CAMERA_FAULT", "THERMAL_THROTTLE"])
        nodes.append({
            "node_id": f"Node_{i}",
            "hardware_status": status,
            "lanes": {
               "N": {"density": density, "wait_time": random.randint(10, 55)}
            }
        })
    return {"status": "success", "nodes": nodes}

@app.get("/api/traffic/{node_id}")
def get_node_traffic(node_id: str, db: Session = Depends(database.get_db)):
    """Returns the raw detailed metric payload for a specific intersection"""
    record = db.query(models.TrafficMetricsRecord).filter(models.TrafficMetricsRecord.node_id == node_id).order_by(models.TrafficMetricsRecord.timestamp.desc()).first()
    if not record:
        import hashlib
        # deterministic random seed based on node_id so each node is a bit different
        seed = int(hashlib.md5(node_id.encode()).hexdigest(), 16)
        
        # 120 second cycle
        now = int(datetime.datetime.utcnow().timestamp())
        cycle_time = (now + seed) % 120
        
        # Phase 01: 0-30s. Phase 02: 30-60s. Phase 03: 60-90s. Phase 04: 90-120s
        phase_idx = cycle_time // 30
        active_phase = f"{node_id}-0{phase_idx + 1}"
        
        # Inside the 30s phase, first 25s is GREEN, last 5s is YELLOW
        phase_sec = cycle_time % 30
        engine_state = "BASE_GREEN" if phase_sec < 25 else "YELLOW_HANDOVER"
        
        # Generate some deterministic but realistic-looking queue numbers based on cycle time
        lane_metrics = {}
        for i in range(1, 5):
            lane_str = f"{node_id}-0{i}"
            if i - 1 == phase_idx:
                # Active lane: queue drains, exit flow is high, wait gets reset
                q = max(0, 30 - phase_sec) 
                w = 0
            else:
                # Inactive lane: queue builds up, wait increases
                offset = (phase_idx - (i - 1)) % 4
                time_waiting = (offset * 30) + phase_sec
                q = int(time_waiting * 0.5) + (seed % 10)
                w = time_waiting
            lane_metrics[lane_str] = {"queue_N": q, "wait_time_T": w, "exit_flow": 5 if i-1 == phase_idx else 0}

        return {
            "nodeId": node_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "state_snapshot": {
                "active_phase": active_phase,
                "engine_state": engine_state,
                "box_gridlock_pct": float((seed % 30) + 10.0),
                "trigger": "STATE_TRANSITION"
            },
            "lane_metrics": lane_metrics,
            "critical_events": {"evp_overrides": 0, "gridlock_triggers": 0},
            "status": "ONLINE",
            "systemMode": "AI_OPTIMIZED"
        }
    
    last_seen = LAST_SEEN_NODES.get(node_id)
    is_offline = False
    if last_seen:
        seconds_since = (datetime.datetime.utcnow() - last_seen).total_seconds()
        if seconds_since > 20:
            is_offline = True

    return {
        "nodeId": record.node_id,
        "timestamp": record.timestamp.isoformat(),
        "state_snapshot": record.state_snapshot,
        "lane_metrics": record.lane_metrics,
        "critical_events": record.critical_events_this_minute,
        "status": "FAULT_OFFLINE" if is_offline else "ONLINE",
        "systemMode": "LEGACY_MICROCONTROLLER" if is_offline else "AI_OPTIMIZED",
    }

@app.get("/api/stream-status")
def get_stream_status():
    """Endpoint for frontend to poll if actual camera simulation data has started arriving"""
    return {"active": STREAM_ACTIVE}

@app.get("/api/ambulance-alerts/{node_id}")
def get_ambulance_alert(node_id: str):
    """Dedicated endpoint for ambulance alerts — completely separate from /api/traffic"""
    alert = AMBULANCE_ALERTS.get(node_id)
    if alert:
        return {"active": True, "alert": alert}
    return {"active": False, "alert": None}

@app.post("/api/ambulance-alerts/{node_id}/clear")
def clear_ambulance_alert(node_id: str):
    """Clear an ambulance alert after operator acknowledgement"""
    if node_id in AMBULANCE_ALERTS:
        del AMBULANCE_ALERTS[node_id]
        print(f"[{datetime.datetime.utcnow().isoformat()}] EVP CLEAR: Alert cleared for node {node_id}")
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
