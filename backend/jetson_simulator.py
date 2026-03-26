import time
import requests
import random
import datetime
import json

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

BACKEND_URL = "http://localhost:8000"
NODE_ID = "284501"  # Simulating intersection 284501
DEVICE_ID = "CAM-001"

# --- MQTT Setup (publishes to HiveMQ so the Render cloud backend also receives data) ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_TRAFFIC = f"mcd/traffic/{NODE_ID}"
MQTT_TOPIC_HEALTH = f"mcd/health/{NODE_ID}"

mqtt_client = None
if MQTT_AVAILABLE:
    import uuid
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "jetson-sim-" + str(uuid.uuid4()))
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"[MQTT] Connection failed: {e}")
        mqtt_client = None


def send_health_ping():
    """Simulates the Jetson sending its hardware health status."""
    payload = {
        "deviceId": DEVICE_ID,
        "type": "camera",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "firmware": "v3.2.1",
        "health": {
            "cpuUsage": random.randint(30, 85),
            "temperature": random.randint(55, 75),
            "networkLatencyMs": random.randint(20, 150)
        },
        "selfReportedIssues": [] if random.random() > 0.1 else ["High latency detected"]
    }

    try:
        res = requests.post(f"{BACKEND_URL}/api/health", json=payload)
        print(f"[HEALTH] {res.status_code}: {res.json().get('message')}")
    except Exception as e:
        print(f"[HEALTH] Local backend unreachable (OK if using MQTT only): {e}")


PHASES = ["01", "02", "03", "04"]
phase_index = 0

def send_traffic_data():
    """Simulates the Jetson sending AI inference counts via both HTTP and MQTT."""
    global phase_index
    active_phase = PHASES[phase_index % len(PHASES)]
    phase_index += 1

    payload = {
        "nodeId": NODE_ID,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "state_snapshot": {
            "active_phase": f"{NODE_ID}-{active_phase}",
            "engine_state": random.choice(["BASE_GREEN", "BASE_GREEN", "BASE_GREEN", "YELLOW_HANDOVER"]),
            "box_gridlock_pct": round(random.uniform(10.0, 85.0), 1),
            "trigger": "STATE_TRANSITION"
        },
        "lane_metrics": {
            f"{NODE_ID}-01": {"queue_N": random.randint(10, 150), "wait_time_T": random.randint(0, 10), "exit_flow": random.randint(5, 50)},
            f"{NODE_ID}-02": {"queue_N": random.randint(0, 30), "wait_time_T": random.randint(10, 80), "exit_flow": 0},
            f"{NODE_ID}-03": {"queue_N": random.randint(10, 50), "wait_time_T": random.randint(20, 90), "exit_flow": 0},
            f"{NODE_ID}-04": {"queue_N": random.randint(0, 20), "wait_time_T": random.randint(30, 80), "exit_flow": 0}
        },
        "critical_events_this_minus_cycle": {
            "evp_overrides": 0 if random.random() > 0.05 else 1,
            "gridlock_triggers": 0
        }
    }

    # 1) Publish to MQTT (reaches the deployed Render backend via HiveMQ)
    if mqtt_client:
        mqtt_client.publish(MQTT_TOPIC_TRAFFIC, json.dumps(payload))
        print(f"[MQTT] Published to {MQTT_TOPIC_TRAFFIC} | Phase: {active_phase}")

    # 2) Also POST to local backend (for local dev)
    try:
        res = requests.post(f"{BACKEND_URL}/api/traffic", json=payload)
        print(f"[HTTP] {res.status_code}: {res.json().get('message')}")
    except Exception:
        pass  # Local backend might not be running, that's fine


if __name__ == "__main__":
    print(f"--- Starting simulated Jetson Edge Node ({NODE_ID}) ---")
    print(f"Local Backend: {BACKEND_URL}")
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"MQTT Available: {MQTT_AVAILABLE}")
    while True:
        send_traffic_data()
        send_health_ping()
        print("Waiting 5 seconds before next inference payload...\n")
        time.sleep(5)
