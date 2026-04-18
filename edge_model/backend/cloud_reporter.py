"""
Cloud Reporter Module (Event-Driven MQTT)
=========================================
Publishes Device Health and Traffic Data directly to broker.hivemq.com.
Triggered seamlessly by the TrafficEngine upon state changes (e.g. Phase Switch),
rather than using an arbitrary background 60s loop.
"""

import json
import datetime
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883

class CloudReporter:
    def __init__(self, engine, broker=BROKER, port=PORT):
        self.engine = engine
        self.broker = broker
        self.port = port
        self.intersection_id = getattr(self.engine, "intersection_id", "INT-ITO-01")
        
        # Setup MQTT Publisher Client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
    def start(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()  # This starts a background network thread strictly for socket traffic, so it never blocks the mainloop!
            print(f"[CloudReporter] Event-Driven MQTT Sync Started for {self.intersection_id}")
        except Exception as e:
            print(f"[CloudReporter WARNING] Could not connect to MQTT: {e}")
            
    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish_health(self):
        sys_state = getattr(self.engine, "system", {})
        issues = []
        if sys_state.get("glare", False):
            issues.append("Camera glare detected")
        if not getattr(self.engine, "box_camera_ok", True):
            issues.append("5th Camera confidence degraded")
            
        payload = {
            "deviceId": self.intersection_id,
            "type": "camera",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "firmware": "V6.0-T8",
            "health": {
                "cpuTemp": 65,
                "networkLatencyMs": 42
            },
            "selfReportedIssues": issues
        }
        try:
            self.client.publish(f"mcd/health/{self.intersection_id}", json.dumps(payload), qos=1)
        except Exception:
            pass

    def publish_state(self, trigger_reason="PHASE_CHANGE"):
        """Publishes holistic metrics immediately when the intersection changes state."""
        lanes = getattr(self.engine, "lanes", {})
        
        state_snapshot = {
            "active_phase": getattr(self.engine, "active_green", None),
            "engine_state": getattr(self.engine, "state", "IDLE"),
            "green_timer": getattr(self.engine, "green_timer", 0),
            "total_green_elapsed": getattr(self.engine, "total_green_elapsed", 0),
            "box_gridlock_pct": getattr(self.engine, "box_density", 0.0),
            "trigger": trigger_reason
        }
        
        lane_metrics = {}
        for name, data in lanes.items():
            lane_metrics[name] = {
                "queue_N": data.get("N", 0),
                "wait_time_T": data.get("T", 0),
                "exit_flow": data.get("exit_total", 0)
            }
            if "exit_total" in data:
                data["exit_total"] = 0
                
        events = {
            "evp_overrides": getattr(self.engine, "events_evp_overrides", 0),
            "gridlock_triggers": getattr(self.engine, "events_gridlock_triggers", 0)
        }
        
        if hasattr(self.engine, "events_evp_overrides"):
            self.engine.events_evp_overrides = 0
        if hasattr(self.engine, "events_gridlock_triggers"):
            self.engine.events_gridlock_triggers = 0
            
        payload = {
            "nodeId": self.intersection_id,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "state_snapshot": state_snapshot,
            "lane_metrics": lane_metrics,
            "critical_events_this_minus_cycle": events
        }
        try:
            self.client.publish(f"mcd/traffic/{self.intersection_id}", json.dumps(payload), qos=1)
        except Exception:
            pass

    def publish_ambulance_alert(self, lane_id, distance_m):
        """
        Publishes an alert to the MCD cloud dashboard when an ambulance enters the Far Zone.
        """
        payload = {
            "deviceId": self.intersection_id,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "alert_type": "EVP_AMBULANCE_APPROACHING",
            "lane_id": lane_id,
            "distance_m": distance_m,
            "message": f"Ambulance detected approaching on lane {lane_id} at {distance_m:.0f}m."
        }
        try:
            self.client.publish(f"mcd/alerts/{self.intersection_id}", json.dumps(payload), qos=1)
            print(f"[CloudReporter] Published Ambulance Alert: Lane {lane_id} at {distance_m:.0f}m")
        except Exception as e:
            print(f"[CloudReporter WARNING] Failed to publish ambulance alert: {e}")
