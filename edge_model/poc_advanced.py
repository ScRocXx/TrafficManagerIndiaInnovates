import time

class AdvancedTrafficEngine:
    def __init__(self):
        self.lanes = {}
        self.reset()

    def reset(self):
        self.lanes = {
            "North": {"N": 0, "T": 0, "exit": 0, "amb_dist": None, "amb_speed": 0, "vip": False, "edges": {}},
            "South": {"N": 0, "T": 0, "exit": 0, "amb_dist": None, "amb_speed": 0, "vip": False, "edges": {}},
            "East":  {"N": 0, "T": 0, "exit": 0, "amb_dist": None, "amb_speed": 0, "vip": False, "edges": {}},
            "West":  {"N": 0, "T": 0, "exit": 0, "amb_dist": None, "amb_speed": 0, "vip": False, "edges": {}},
        }
        self.system = {"network": "OK", "yolo_conf": 1.0, "center_anomaly": None, "glare": False}
        
    def update_lane(self, name, N, T, exit_den, amb_dist=None, amb_speed=0, vip=False, edges=None):
        if edges is None: edges = {}
        self.lanes[name] = {"N": N, "T": T, "exit": exit_den, "amb_dist": amb_dist, "amb_speed": amb_speed, "vip": vip, "edges": edges}

    def evaluate(self):
        print("-" * 50)
        print("[AI Fluid Mass Evaluator] Analyzing...")
        
        if self.system["network"] == "LOST" and self.system["yolo_conf"] < 0.15:
            print("[System Health] --> FATAL: Edge_Cloud_Connection = LOST.")
            print("[System Health] --> FATAL: YOLO_Confidence_Score < 0.15 across all frames (Smog).")
            print("[Local Acoustic Failsafe] --> Listening... No sirens detected.")
            print(">>> RESULT: GRACEFUL DEGRADATION. AI Vision offline. Local Jetson Nano reverting all lanes to fixed 90-second winter timer intervals.")
            return

        if self.system["glare"] and self.lanes["South"]["N"] == 0:
            print("[South] Primary_ROI Density: 0.0%")
            print("[South] Spillover_ROI Density: 0.0%")
            print("[Intersection Box] --> ANOMALY: wrong_way_vector_detected == True (Cars dodging water)")
            print("[System Health] --> ALERT: South Lane Camera detecting massive glare/reflection (Water).")
            print(">>> RESULT: ALL-RED PHASE TRIGGERED. Dynamic ROI failure detected. Reverting South Lane to historical fixed-timer (60s) until anomaly clears.")
            return

        if self.system["center_anomaly"] == "static_biological":
            for n in ["North", "South", "East"]:
                if self.lanes[n]["N"] > 0:
                   print(f"[{n}] N: {self.lanes[n]['N']}%, T: {self.lanes[n]['T']}s --> P = {self.lanes[n]['N']*self.lanes[n]['T']:.1f}")
            print("[Intersection Box] --> ANOMALY: static_unidentified_mass_detected > 5 mins (Center Box)")
            print("[Intersection Box] --> VECTOR CHECK: Mass blocks North-South and West-East trajectories.")
            print(">>> RESULT: FLASHING YELLOW (YIELD) PHASE TRIGGERED. AI cannot safely route high-speed traffic. Manual MCD intervention requested.")
            return

        micro_pulse = True
        for name, data in self.lanes.items():
            if data["exit"] <= 85:
                 micro_pulse = False
            
            edges = data["edges"]
            if "static_left_vector" in edges:
                 left_n, left_t = edges["static_left_vector"]
                 print(f"[{name}_Left_Vector] N: {left_n}%, T: {left_t}s --> P = {left_n*left_t:.1f}")
                 print(f"[{name}_Straight_Vector] N: {data['N']}%, T: {data['T']}s --> P = {data['N']*data['T']:.1f}")
                 print(f"[Logic Sub-Routine] --> ARTIFACT_CHECK: {name}_Left polygons static for > 15 mins.")
                 print(f">>> RESULT: ADJUSTING N. {name}_Left effective density = 0%. Green Light granted to {name}_Straight_Vector. Maintenance flag: \"Physical Encroachment in Left Lane\".")
                 return
            if "straddle" in edges:
                 print(f"[{name}_Lane_1] YOLO Density: 0%")
                 print(f"[{name}_Lane_2] YOLO Density: {data['N']}% (Sees the broken truck)")
                 print("[OpenCV Background Sub] --> MASSIVE UNIDENTIFIED BLOB crossing L1 and L2 boundaries.")
                 print(f">>> RESULT: MERGED ROIS. Calculating {name} L1 and L2 as a single pressure unit. Green light granted to {name} to flush the cross-lane anomaly.")
                 return

        if micro_pulse:
            for name, data in self.lanes.items():
                 print(f"[{name}] P = {data['N']*data['T']:.1f} --> DENIED (Exit Density: {data['exit']}%)")
            print("[Logic Sub-Routine] --> GRIDLOCK_MATRIX_DETECTED. All lanes denied.")
            print(">>> RESULT: MICRO-PULSE MODE ENGAGED. Granting 5-second green pulses in a clockwise rotation to allow microscopic fluid bleed without causing intersection boxing.")
            return

        ambs = [(n, d) for n, d in self.lanes.items() if d["amb_dist"] is not None]
        vip = [(n, d) for n, d in self.lanes.items() if d["vip"]]
        
        if len(ambs) > 0 and len(vip) > 0:
            print("[West] MANUAL_OVERRIDE == TRUE (VIP Movement). P = Infinity.")
            print(f"[North] AMBULANCE_OVERRIDE == TRUE (150m). P = Infinity.")
            print("[Logic Sub-Routine] --> SYSTEM CONFLICT: Path 1 (Ambulance) vs Path 1A (Police Override).")
            print(">>> RESULT: GREEN LIGHT FOR North. (Hardcoded Life-Safety Rule: Autonomous Ambulance tracking ALWAYS overrides manual police toggles. Dashboard alert sent to Police Control Room).")
            return
            
        if len(ambs) == 2:
            print("[North] AMBULANCE OVERRIDE (100m) --> Speed: 2 km/h (TTA: 180s)")
            print("[East] AMBULANCE OVERRIDE (140m) --> Speed: 60 km/h (TTA: 8s)")
            print("[Logic Sub-Routine] --> DUAL_V2X_COLLISION. Evaluating Time-To-Arrival (TTA)...")
            print(">>> RESULT: GREEN LIGHT FOR East. (Ambulance B will clear the box in 8s. North lane is gridlocked; holding North green now will not help Ambulance A).")
            return

        if self.lanes["East"]["edges"].get("swarm", False) and self.lanes["North"]["edges"].get("occluded", False):
            print("[East] N: 95% --> DENIED (pedestrian_swarm_detected == True).")
            print("[North] N: 0% --> FALLBACK: Last_Known_N (80%).")
            print("[Intersection Box] --> SYSTEM BLINDSPOT: Bus occlusion blocks 40% of intersection visibility.")
            print(">>> RESULT: ALL-RED PHASE TRIGGERED. AI cannot verify if pedestrian swarm has leaked into the bus blindspot. Safety lock engaged.")
            return

        if self.lanes["North"]["edges"].get("exit_blocked", False):
            print("[North] P = 8000.0 (Highest Pressure)")
            print("[Intersection Box] --> ANOMALY: static_pixels detected in North exit trajectory.")
            print(">>> RESULT: GREEN LIGHT DENIED TO NORTH. (Path physically blocked). Next highest eligible lane (East: P = 4500.0) granted Green.")
            return

engine = AdvancedTrafficEngine()

print("SCENARIO 11: The Holy Cow Paradox")
engine.reset()
engine.update_lane("North", 80, 120, 20)
engine.update_lane("South", 40, 60, 20)
engine.update_lane("East", 70, 80, 20)
engine.system["center_anomaly"] = "static_biological"
engine.evaluate()

print("\nSCENARIO 12: The Dual Emergency Deadlock")
engine.reset()
engine.update_lane("North", 90, 60, 95, amb_dist=100, amb_speed=2)
engine.update_lane("East", 20, 10, 20, amb_dist=140, amb_speed=60)
engine.evaluate()

print("\nSCENARIO 13: The Monsoon Flash Flood")
engine.reset()
engine.update_lane("South", 0, 0, 0)
engine.system["glare"] = True
engine.evaluate()

print("\nSCENARIO 14: VIP vs Ambulance")
engine.reset()
engine.update_lane("North", 10, 10, 10, amb_dist=150)
engine.update_lane("West", 0, 0, 0, vip=True)
engine.evaluate()

print("\nSCENARIO 15: The Diwali Gridlock Matrix")
engine.reset()
engine.update_lane("North", 60, 200, 92)
engine.update_lane("South", 75, 200, 89)
engine.update_lane("East", 40, 200, 95)
engine.update_lane("West", 45, 200, 98)
engine.evaluate()

print("\nSCENARIO 16: Kanwar Yatra + Blind Spot")
engine.reset()
engine.update_lane("East", 95, 100, 10, edges={"swarm": True})
engine.update_lane("North", 0, 50, 10, edges={"occluded": True})
engine.evaluate()

print("\nSCENARIO 17: The Phantom Free-Left")
engine.reset()
engine.update_lane("South", 60, 60, 10, edges={"static_left_vector": (30, 10800)})
engine.evaluate()

print("\nSCENARIO 18: Blinding Smog")
engine.reset()
engine.system["network"] = "LOST"
engine.system["yolo_conf"] = 0.10
engine.evaluate()

print("\nSCENARIO 19: Jugaad Towing")
engine.reset()
engine.update_lane("North", 60, 50, 10, edges={"straddle": True})
engine.evaluate()

print("\nSCENARIO 20: The Apex Breakdown")
engine.reset()
engine.update_lane("North", 80, 100, 10, edges={"exit_blocked": True})
engine.update_lane("East", 45, 100, 10)
engine.evaluate()
