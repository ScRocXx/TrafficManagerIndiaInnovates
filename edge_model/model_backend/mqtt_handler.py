"""
Northern Blades V5.5 — MQTT Handler with V2X Green Corridor
=============================================================
Listens to edge telemetry and V2X ambulance protocols.
Implements the Two-Phase GeoFence Corridor:
    Phase A (500m): Pre-Flush — truncate cross-traffic.
    Phase B (150m): Hard Lock — absolute Green for ambulance lane.
"""

import paho.mqtt.client as mqtt
import json
import math

# ──────────────────────────────────────────────────────────────────
#  BROKER CONFIGURATION
# ──────────────────────────────────────────────────────────────────

BROKER = "broker.hivemq.com"  # Free public broker for testing
PORT = 1883
TOPICS = [
    ("telemetry/edge", 0),
    ("v2x/ambulance", 0),
    ("v2x/siren", 0),        # Acoustic failsafe topic
    ("intersection/box", 0), # 5th Camera (God's Eye) box density
]

CENTER_LAT = 28.6139
CENTER_LON = 77.2090

# Approximate: 1 degree lat ≈ 111,320 meters
# 500m ≈ 0.00449 degrees, 150m ≈ 0.00135 degrees
OFFSET_500M = 0.00449
OFFSET_150M = 0.00135

# Approach Funnel definitions:  (min_lat, max_lat, min_lon, max_lon)
GEOFENCE_CORRIDORS = {
    "North": {
        "phase_a": (CENTER_LAT, CENTER_LAT + OFFSET_500M, CENTER_LON - 0.0005, CENTER_LON + 0.0005),
        "phase_b": (CENTER_LAT, CENTER_LAT + OFFSET_150M, CENTER_LON - 0.0005, CENTER_LON + 0.0005),
    },
    "South": {
        "phase_a": (CENTER_LAT - OFFSET_500M, CENTER_LAT, CENTER_LON - 0.0005, CENTER_LON + 0.0005),
        "phase_b": (CENTER_LAT - OFFSET_150M, CENTER_LAT, CENTER_LON - 0.0005, CENTER_LON + 0.0005),
    },
    "East": {
        "phase_a": (CENTER_LAT - 0.0005, CENTER_LAT + 0.0005, CENTER_LON, CENTER_LON + OFFSET_500M),
        "phase_b": (CENTER_LAT - 0.0005, CENTER_LAT + 0.0005, CENTER_LON, CENTER_LON + OFFSET_150M),
    },
    "West": {
        "phase_a": (CENTER_LAT - 0.0005, CENTER_LAT + 0.0005, CENTER_LON - OFFSET_500M, CENTER_LON),
        "phase_b": (CENTER_LAT - 0.0005, CENTER_LAT + 0.0005, CENTER_LON - OFFSET_150M, CENTER_LON),
    },
}


def point_in_rect(lat, lon, rect):
    """Check if a GPS point falls inside a rectangular geofence."""
    min_lat, max_lat, min_lon, max_lon = rect
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def resolve_geofence(lat, lon):
    """
    Determine which approach lane the ambulance is in, and which
    phase (A or B) applies.

    Returns
    -------
    tuple (lane_name, phase) or (None, None) if outside all fences.
    """
    for lane, fences in GEOFENCE_CORRIDORS.items():
        if point_in_rect(lat, lon, fences["phase_b"]):
            return lane, "B"
        if point_in_rect(lat, lon, fences["phase_a"]):
            return lane, "A"
    return None, None


# ──────────────────────────────────────────────────────────────────
#  MQTT CLIENT FACTORY
# ──────────────────────────────────────────────────────────────────

def start_mqtt_client(engine):
    """
    Create and start the MQTT client.  Subscribes to telemetry,
    V2X ambulance, and acoustic siren topics.
    """

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("[MQTT] Connected to Broker. Listening for Telemetry + V2X...")
            client.subscribe(TOPICS)
        else:
            print(f"[MQTT] Failed to connect, return code {rc}")

    def on_message(client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())

            # ── Standard Edge Telemetry ──────────────────────────
            if topic == "telemetry/edge":
                engine.ingest_telemetry(payload)

            # ── 5th Camera (God's Eye) Box Density ────────────────
            elif topic == "intersection/box":
                engine.ingest_box_density(payload)

            # ── V2X Ambulance GPS + Route ────────────────────────
            elif topic == "v2x/ambulance":
                _handle_ambulance(engine, payload)

            # ── Acoustic Siren Failsafe ──────────────────────────
            elif topic == "v2x/siren":
                _handle_siren(engine, payload)

        except json.JSONDecodeError:
            print("[MQTT] Malformed JSON received")
        except Exception as e:
            print(f"[MQTT ERROR] {e}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"[MQTT] Warning: Broker connection failed: {e}. Is Mosquitto running?")

    return client


# ──────────────────────────────────────────────────────────────────
#  V2X AMBULANCE HANDLER (Two-Phase GeoFence)
# ──────────────────────────────────────────────────────────────────

def _handle_ambulance(engine, payload):
    """
    Process an ambulance GPS ping.

    Expected payload:
    {
        "lat": 28.6145,
        "lon": 77.2090,
        "speed": 45,
        "route": [[lat1,lon1], [lat2,lon2], [lat3,lon3]],
        "vip": true
    }
    """
    lat = payload.get("lat")
    lon = payload.get("lon")
    speed = payload.get("speed", 0)
    vip = payload.get("vip", False)

    if lat is None or lon is None:
        return

    # Resolve which lane and phase
    lane, phase = resolve_geofence(lat, lon)

    if lane is None:
        # Ambulance is outside all geofences — clear any previous override
        for name in engine.lanes:
            engine.lanes[name]["amb_dist"] = None
            engine.lanes[name]["vip"] = False
        return

    # Calculate approximate distance from center
    dist_m = math.sqrt(
        ((lat - CENTER_LAT) * 111320) ** 2 +
        ((lon - CENTER_LON) * 111320 * math.cos(math.radians(CENTER_LAT))) ** 2
    )

    # Build the V2X payload for the engine
    v2x_payload = {
        "lane": lane,
        "distance": dist_m,
        "speed": speed,
        "vip": vip,
        "phase": phase,
    }

    engine.ingest_v2x(v2x_payload)

    if phase == "B":
        print(f"[V2X] 🚨 PHASE B — HARD LOCK for {lane} lane (dist: {dist_m:.0f}m)")
    elif phase == "A":
        print(f"[V2X] ⚠️  PHASE A — PRE-FLUSH for {lane} lane (dist: {dist_m:.0f}m)")


# ──────────────────────────────────────────────────────────────────
#  ACOUSTIC SIREN FAILSAFE HANDLER
# ──────────────────────────────────────────────────────────────────

def _handle_siren(engine, payload):
    """
    Process an acoustic siren detection event from the edge node.

    Expected payload:
    {
        "detected": true,
        "frequency_hz": 1350,
        "volume_trend": "escalating",  // "escalating" | "stable" | "fading"
        "confidence": 0.85
    }
    """
    detected = payload.get("detected", False)
    trend = payload.get("volume_trend", "stable")
    confidence = payload.get("confidence", 0)

    if detected and trend == "escalating" and confidence >= 0.70:
        # Siren is confirmed and approaching — trigger emergency
        # Without GPS we don't know the lane, so we use the
        # microphone directionality (if available) or fall back
        # to holding current green + extending all-red for safety.
        print(f"[SIREN] 🔊 Acoustic emergency detected (conf: {confidence:.0%}, trend: {trend})")

        # If no GPS ambulance is already active, trigger a conservative hold
        any_amb = any(d["amb_dist"] is not None for d in engine.lanes.values())
        if not any_amb:
            engine.trigger_all_red_buffer(reason="Acoustic siren detected — holding intersection")

