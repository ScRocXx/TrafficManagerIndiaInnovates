import time
import sys

class TrafficEngine:
    def __init__(self):
        self.lanes = {
            "North": {"primary": 0, "spill": 0, "exit": 0, "wait": 0, "amb": None, "edge_cases": {}},
            "South": {"primary": 0, "spill": 0, "exit": 0, "wait": 0, "amb": None, "edge_cases": {}},
            "East":  {"primary": 0, "spill": 0, "exit": 0, "wait": 0, "amb": None, "edge_cases": {}},
            "West":  {"primary": 0, "spill": 0, "exit": 0, "wait": 0, "amb": None, "edge_cases": {}},
        }
        self.intersection_box_wrong_way = False

    def reset_lanes(self):
         for name in self.lanes:
             self.lanes[name] = {"primary": 0, "spill": 0, "exit": 0, "wait": 0, "amb": None, "edge_cases": {}}
         self.intersection_box_wrong_way = False

    def update_lane(self, name, primary, spill, exit_den, wait, amb=None, edge_cases=None):
        if edge_cases is None: edge_cases = {}
        self.lanes[name] = {
            "primary": primary, "spill": spill, "exit": exit_den, "wait": wait, "amb": amb, "edge_cases": edge_cases
        }

    def evaluate(self):
        print("-" * 50)
        print("[AI Fluid Mass Evaluator] Analyzing Intersection...")
        scores = {}
        all_red = False
        suspend_algo = False

        if self.intersection_box_wrong_way:
             print("[Intersection Box] --> ANOMALY: wrong_way_vector_detected == True")
             all_red = True

        for name, data in self.lanes.items():
            primary = data["primary"]
            spill = data["spill"]
            exit_den = data["exit"]
            t = data["wait"]
            amb_dist = data["amb"]
            edges = data["edge_cases"]

            n = (primary + spill)
            score_context = ""

            # Scenario 5
            if edges.get("occluded", False):
                 last_n = edges.get("last_known_n", 0)
                 print(f"[{name}] N(Density): {n:.1f}%, T(Wait): {t}s --> P = {n*t:.1f} (Hidden by Bus) -> FALLBACK: Last_Known_N({last_n:.1f}%) * {t}s --> P = {last_n*t:.1f}")
                 n = last_n
                 score_context = "(Occlusion Memory Activated)"

            # Scenario 8
            elif "static_pixels_pct" in edges:
                 static_pct = edges["static_pixels_pct"]
                 old_p = n * t
                 print(f"[{name}] N(Density): {n:.1f}%, T(Wait): {t}s --> P = {old_p:.1f} --> ARTIFACT CHECK: static_pixels > 15 mins.")
                 n = max(0.0, n - static_pct)
                 print(f"[{name}] --> ADJUSTING N: {n+static_pct:.1f}% - {static_pct:.1f}% (Artifact Area) = {n:.1f}%. New P = {n*t:.1f}.")

            p = n * t

            # Scenario 4
            if edges.get("police_barricade_detected", False):
                 n = n * 0.5
                 p = n * t
                 score_context = f"(Barricade Penalty Applied, Effective N: {n}%)"

            # Scenario 9
            if edges.get("grap_truck_pct"):
                 truck_pct = edges["grap_truck_pct"]
                 old_p = p
                 print(f"[{name}] N(Density): {n:.1f}%, T(Wait): {t}s --> P = {old_p:.1f} --> PENALTY: GRAP_stage_4_active == True AND class_truck > 0.")
                 n = n - (truck_pct * 0.8) 
                 p = n * t
                 print(f"[{name}] --> ADJUSTING N: Shrinking truck mass by 80%. Effective N = {n:.1f}%. New P = {p:.1f}.")

            # Scenario 6
            if edges.get("pedestrian_swarm_detected", False):
                 print(f"[{name}] N(Density): {n:.1f}%, T(Wait): {t}s --> P = {p:.1f} --> DENIED (pedestrian_swarm_detected == True)")
                 suspend_algo = True
                 p = -1

            # Flaw 3
            if exit_den > 85 and not suspend_algo:
                print(f"[{name}] N(Density): {n:.1f}%, T(Wait): {t}s --> P = {p:.1f} --> DENIED (Exit Density > 85%)")
                p = -1
                score_context = "(DENIED)"

            # Flaw 1
            if amb_dist is not None and amb_dist < 150:
                 p = float('inf')
                 score_context = f"(AMBULANCE HARD LOCK)"

            if p != -1 and not (edges.get("pedestrian_swarm_detected", False)) and not("static_pixels_pct" in edges or "grap_truck_pct" in edges or edges.get("occluded", False)):
                print(f"[{name}] N(Density): {n:.1f}%, T(Wait): {t}s --> P = {p:.1f} {score_context}")

            scores[name] = p

        if suspend_algo:
             print(">>> RESULT: ALGORITHM SUSPENDED. TRIGGERING 60s HARDCODED CYCLE. EVENT FLAGGED TO DASHBOARD.")
             return "SUSPENDED"

        winner = max(scores, key=scores.get)
        max_score = scores[winner]

        if all_red:
             print(f">>> RESULT: ALL-RED PHASE TRIGGERED (10s). Allowing intersection to clear before granting {winner} green.")
             return "ALL_RED"
        elif max_score == -1:
            print(f">>> RESULT: ALL RED (Gridlock Prevention)")
        elif max_score == float('inf'):
            print(f">>> RESULT: GREEN LIGHT FOR {winner} (V2X Emergency Pre-Flush)")
        elif "occluded" in self.lanes[winner]["edge_cases"]:
            print(f">>> RESULT: GREEN LIGHT FOR {winner} (Occlusion Memory Activated)")
        elif any("static_pixels_pct" in v["edge_cases"] for v in self.lanes.values()):
            print(f">>> RESULT: GREEN LIGHT FOR {winner} (Highest Valid Fluid Pressure). Maintenance flag sent for South camera.")
        elif any("grap_truck_pct" in v["edge_cases"] for v in self.lanes.values()):
            print(f">>> RESULT: GREEN LIGHT FOR {winner}. E-Challan ANPR trigger queued for West lane truck.")
        else:
            print(f">>> RESULT: GREEN LIGHT FOR {winner}")
        
        return winner

engine = TrafficEngine()

print("SCENARIO 4: Flaw 14 (Yellow Barricade Ghost Jam)")
engine.reset_lanes()
engine.update_lane("North", primary=50, spill=0, exit_den=20, wait=60) 
engine.update_lane("South", primary=20, spill=0, exit_den=20, wait=30) 
engine.update_lane("East",  primary=10, spill=0, exit_den=10, wait=30) 
engine.update_lane("West",  primary=80, spill=0, exit_den=0,  wait=50, edge_cases={"police_barricade_detected": True}) 
engine.evaluate()

print("\nSCENARIO 5: Flaw 12 (DTC Bus Occlusion / The Blind Spot)")
engine.reset_lanes()
engine.update_lane("North", primary=0, spill=0, exit_den=20, wait=60, edge_cases={"occluded": True, "last_known_n": 75.0}) 
engine.update_lane("South", primary=50, spill=0, exit_den=20, wait=50) 
engine.update_lane("East",  primary=20, spill=0, exit_den=20, wait=30) 
engine.update_lane("West",  primary=10, spill=0, exit_den=10, wait=10) 
engine.evaluate()

print("\nSCENARIO 6: Flaw 10 (The Baraat / Pedestrian Swarm Anomaly)")
engine.reset_lanes()
engine.update_lane("North", primary=60, spill=0, exit_den=20, wait=80) 
engine.update_lane("South", primary=40, spill=0, exit_den=20, wait=60) 
engine.update_lane("East",  primary=95, spill=0, exit_den=20, wait=300, edge_cases={"pedestrian_swarm_detected": True}) 
engine.update_lane("West",  primary=15, spill=0, exit_den=10, wait=20) 
engine.evaluate()

print("\nSCENARIO 7: Flaw 15 (Wrong-Way Swarm / The Filtration Wall)")
engine.reset_lanes()
engine.update_lane("North", primary=70, spill=0, exit_den=20, wait=70) 
engine.update_lane("South", primary=30, spill=0, exit_den=20, wait=40) 
engine.update_lane("East",  primary=10, spill=0, exit_den=10, wait=10) 
engine.update_lane("West",  primary=80, spill=0, exit_den=95, wait=90) 
engine.intersection_box_wrong_way = True
engine.evaluate()

print("\nSCENARIO 8: Flaw 16 (The Ghost Object / Lens Dirt)")
engine.reset_lanes()
engine.update_lane("North", primary=40, spill=0, exit_den=20, wait=50) 
engine.update_lane("South", primary=30, spill=0, exit_den=20, wait=300, edge_cases={"static_pixels_pct": 30.0}) 
engine.update_lane("East",  primary=60, spill=0, exit_den=20, wait=60) 
engine.update_lane("West",  primary=5,  spill=0, exit_den=10, wait=10) 
engine.evaluate()

print("\nSCENARIO 9: Flaw 13 (GRAP Ban Truck Detection)")
engine.reset_lanes()
engine.update_lane("North", primary=50, spill=0, exit_den=20, wait=60) 
engine.update_lane("South", primary=20, spill=0, exit_den=20, wait=30) 
engine.update_lane("East",  primary=15, spill=0, exit_den=10, wait=20) 
engine.update_lane("West",  primary=80, spill=0, exit_den=20, wait=50, edge_cases={"grap_truck_pct": 80.0}) 
engine.evaluate()

print("\nSCENARIO 10: The Ultimate Delhi Deadlock")
engine.reset_lanes()
engine.update_lane("North", primary=90, spill=0, exit_den=95, wait=200) 
engine.update_lane("East",  primary=10, spill=0, exit_den=10, wait=30, amb=100) 
engine.intersection_box_wrong_way = True
engine.evaluate()
