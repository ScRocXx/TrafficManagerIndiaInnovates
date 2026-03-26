import time
import requests
import random
import datetime

BACKEND_URL = "http://localhost:8000"
NODE_ID = "INT-01"  # Simulating ITO Junction
DEVICE_ID = "CAM-001"

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
        # 10% chance of simulating a random issue
        "selfReportedIssues": [] if random.random() > 0.1 else ["High latency detected"]
    }
    
    try:
        res = requests.post(f"{BACKEND_URL}/api/health", json=payload)
        print(f"[HEALTH] {res.status_code}: {res.json().get('message')}")
    except Exception as e:
        print(f"[HEALTH] Connection Failed to Backend: {e}")

def send_traffic_data():
    """Simulates the Jetson sending up AI inference counts."""
    payload = {
        "nodeId": NODE_ID,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "state_snapshot": {
            "active_phase": f"{NODE_ID}-A",
            "engine_state": random.choice(["GREEN", "YELLOW", "RED"]),
            "box_gridlock_pct": round(random.uniform(10.0, 85.0), 1)
        },
        "lane_metrics": {
            f"{NODE_ID}-A": {"queue_N": random.randint(10, 150), "wait_time_T": random.randint(0, 10), "exit_flow": random.randint(5, 50)},
            f"{NODE_ID}-B": {"queue_N": random.randint(0, 30), "wait_time_T": random.randint(10, 80), "exit_flow": 0},
            f"{NODE_ID}-C": {"queue_N": random.randint(10, 50), "wait_time_T": random.randint(20, 90), "exit_flow": 0},
            f"{NODE_ID}-D": {"queue_N": random.randint(0, 20), "wait_time_T": random.randint(30, 80), "exit_flow": 0}
        },
        "critical_events_this_minute": {
            "evp_overrides": 0 if random.random() > 0.05 else 1,
            "gridlock_triggers": 0
        }
    }
    
    try:
        res = requests.post(f"{BACKEND_URL}/api/traffic", json=payload)
        print(f"[TRAFFIC] {res.status_code}: {res.json().get('message')}")
    except Exception as e:
        print(f"[TRAFFIC] Connection Failed to Backend: {e}")

if __name__ == "__main__":
    print(f"--- Starting simulated Jetson Edge Node ({NODE_ID}) ---")
    print(f"Targeting Backend: {BACKEND_URL}")
    while True:
        send_traffic_data()
        send_health_ping()
        print("Waiting 5 seconds before next inference payload...\n")
        time.sleep(5)
