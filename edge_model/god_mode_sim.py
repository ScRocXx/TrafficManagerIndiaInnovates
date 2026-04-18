import time
import json
import threading
import sys

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("⚠️  paho-mqtt not installed. Please run: pip install paho-mqtt")
    sys.exit(1)

# ----- CONFIGURATION -----
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC = "northern_blades/delhi/ambulance/1"
TARGET_LAT = 28.5678
TARGET_LON = 77.2100
# Roughly 500 meters South. 1 degree latitude is approx 111km.
START_LAT = TARGET_LAT - 0.0045 
STEPS = 30

def worker_ambulance_simulation():
    """Simulates the ambulance driving towards the intersection in the background."""
    print("\n📡 \033[36m[V2X SIM] Connecting to MQTT broker...\033[0m")
    
    # Use a unique client ID per thread so multiple ambulances can run simultaneously if needed
    client_id = f"god_mode_sim_amb_{int(time.time()*1000)}"
    
    # Handle both old and new paho-mqtt versions gracefully
    if hasattr(mqtt, "CallbackAPIVersion"):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    else:
        client = mqtt.Client(client_id=client_id)

    try:
        # If FastAPI isn't running, we handle potential network issues gracefully without crashing
        client.connect(BROKER, PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"\n⚠️  \033[93m[WARNING] Could not connect to MQTT Broker. (If FastAPI server isn't running yet, ignore this). Error: {e}\033[0m")
        # We continue the simulation anyway so the terminal output looks good for the live demo

    current_lat = START_LAT
    lat_step = (TARGET_LAT - START_LAT) / STEPS

    for _ in range(STEPS):
        payload = {
            "vehicle_id": "AMB_DL_14_9921",
            "lat": round(current_lat, 6),
            "lon": TARGET_LON,
            "heading": 0.0,
            "siren_active": True
        }

        try:
            client.publish(TOPIC, json.dumps(payload))
            print(f"📡  \033[92m[V2X SIM]\033[0m AMBULANCE APPROACHING: Lat {current_lat:.6f} | Distance closing...")
        except Exception as e:
            print(f"⚠️  \033[93m[WARNING] Failed to publish. Is the FastAPI server running? Error: {e}\033[0m")

        current_lat += lat_step
        time.sleep(1)

    print("\n✅ \033[92m[V2X SIM] AMBULANCE HAS ARRIVED AT THE INTERSECTION.\033[0m")
    print("\n\033[91m\033[1m🚨 PRESS ENTER TO DISPATCH AMBULANCE 🚨\033[0m")
    
    try:
        client.loop_stop()
        client.disconnect()
    except:
        pass

def main():
    print("\n" + "="*60)
    print("🚗 \033[1mNORTHERN BLADES - GOD MODE SIMULATOR\033[0m 🚗")
    print("="*60)
    print("This script simulates hardware V2X inputs for a flawless demo.\n")
    
    # Setup initial prompt
    print("\033[91m\033[1m🚨 PRESS ENTER TO DISPATCH AMBULANCE 🚨\033[0m")
    
    while True:
        try:
            # Main thread blocks and waits for user input
            input()
            
            # Use threading to do things simultaneously (Main thread handles input, worker handles simulation)
            amb_thread = threading.Thread(target=worker_ambulance_simulation, daemon=True)
            amb_thread.start()
            
        except KeyboardInterrupt:
            print("\n\n🛑 \033[91mExiting God Mode Simulator. Good luck with the presentation!\033[0m")
            break
        except Exception as e:
            print(f"\n⚠️  \033[93m[WARNING] An unexpected error occurred: {e}\033[0m")

if __name__ == "__main__":
    main()
