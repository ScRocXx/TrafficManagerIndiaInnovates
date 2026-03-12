import requests, time

API_BASE = "http://127.0.0.1:8000/api/v1/telemetry/"

def send(node, story, payload):
    print(f"\n--- {node}: {story} ---")
    try:
        r = requests.post(API_BASE + node, json=payload)
        print(f"Decision: {r.json().get('command')}")
    except: print("Server Error")
    time.sleep(3)

def get_base():
    return {
        "ambulance_lane": None, "is_waterlogged": False, "vip_route": None, 
        "network_status": "ONLINE", "visibility_index": 100, "wrong_way_alert": None, 
        "heavy_transit_lane": None, "densities": {"north": 30, "south": 30, "east": 30, "west": 30},
        "honk_decibels": {"north": 10, "south": 10, "east": 10, "west": 10}
    }

print("🚀 INITIATING NORTHERN BLADES MACRO-GRID SIMULATION...")

# 1. Start all nodes in normal state
for n in ["Minto_Bridge", "Ashram_Chowk", "AIIMS_Junction"]:
    send(n, "Normalizing Node", get_base())

# 2. THE RIPPLE EFFECT: Minto Bridge Floods
minto_flood = get_base()
minto_flood["is_waterlogged"] = True
send("Minto_Bridge", "🛑 CRITICAL: UNDERPASS WATERLOGGED", minto_flood)

# 3. ASHRAM RESPONDS: Ashram sees Minto is flooded and reroutes North-bound traffic
ashram_react = get_base()
ashram_react["densities"]["north"] = 100 # High demand for Minto
send("Ashram_Chowk", "🔄 MACRO-GRID REROUTE: Avoiding Minto Flood", ashram_react)

# 4. AMBULANCE HANDSHAKE: Ambulance at AIIMS headed North
aiims_amb = get_base()
aiims_amb["ambulance_lane"] = "north"
send("AIIMS_Junction", "🚨 V2X: Ambulance Priority North", aiims_amb)

# 5. SMOG AT ASHRAM: Optical blind, using acoustics
ashram_smog = get_base()
ashram_smog["visibility_index"] = 20
ashram_smog["honk_decibels"] = {"north": 10, "south": 120, "east": 10, "west": 10}
send("Ashram_Chowk", "🌫️ SENSOR FUSION: Smog Blind / Acoustic Active", ashram_smog)

# 6. TOTAL SYSTEM TEST: Minto goes Offline
minto_offline = get_base()
minto_offline["network_status"] = "OFFLINE"
send("Minto_Bridge", "💥 NETWORK CRASH: Island Mode Failsafe", minto_offline)

print("\n✅ MACRO-GRID DEMO COMPLETE.")