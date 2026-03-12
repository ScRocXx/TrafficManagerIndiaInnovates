# engine.py
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import random

class TrafficNode:
    def __init__(self, node_id, neighbors=None):
        self.node_id = node_id
        self.neighbors = neighbors or []
        self.lanes = {"north": 0, "south": 0, "east": 0, "west": 0}
        self.wait_times = {"north": 0, "south": 0, "east": 0, "west": 0}
        self.honk_levels = {"north": 0, "south": 0, "east": 0, "west": 0}
        self.current_green = None
        
        # Flags
        self.emergency_v2x_lane = None
        self.is_waterlogged = False
        self.neighbor_flood_alert = None
        self.mcd_vip_override = None
        self.visibility = 100
        self.network = "ONLINE"
        self.heavy_transit_lane = None
        self.wrong_way_data = None 
        
        self.island_cycle = ["north", "east", "south", "west"]
        self.island_index = 0
        self.island_time_remaining = 60
        
        # --- THE AI UPGRADE ---
        self.lane_map = {0: "north", 1: "south", 2: "east", 3: "west"}
        self.reverse_map = {"north": 0, "south": 1, "east": 2, "west": 3}
        self.ai_model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
        self._train_ai_model() # Train the AI the moment the node boots up

    def _train_ai_model(self):
        """Generates synthetic historical data and trains the Random Forest AI."""
        print(f"🧠 Training AI Model for {self.node_id}...")
        X_train = []
        y_train = []
        
        # Generate 2000 scenarios of historical "Delhi Data"
        for _ in range(2000):
            # Features: [N_dens, S_dens, E_dens, W_dens, N_wait, S_wait, E_wait, W_wait, Visibility]
            features = [random.randint(0, 100) for _ in range(4)] + \
                       [random.randint(0, 60) for _ in range(4)] + \
                       [random.choice([15, 50, 100])] # Visibility
            
            # Labeling logic for training: AI learns that high mass + high wait time = Green
            pressures = [features[i] * features[i+4] for i in range(4)]
            
            # Teach it acoustic fusion: If vis is low, ignore visual density
            if features[8] < 30:
                best_lane = random.randint(0, 3) # Add noise for low visibility learning
            else:
                best_lane = pressures.index(max(pressures))
                
            X_train.append(features)
            y_train.append(best_lane)
            
        self.ai_model.fit(X_train, y_train)
        print(f"✅ AI Model successfully trained for {self.node_id}.")

    def receive_edge_telemetry(self, edge_data, global_macro_state):
        self.emergency_v2x_lane = edge_data.get("ambulance_lane")
        self.is_waterlogged = edge_data.get("is_waterlogged", False)
        self.mcd_vip_override = edge_data.get("vip_route")
        self.visibility = edge_data.get("visibility_index", 100)
        self.network = edge_data.get("network_status", "ONLINE")
        self.heavy_transit_lane = edge_data.get("heavy_transit_lane")
        self.honk_levels = edge_data.get("honk_decibels", self.honk_levels)
        self.wrong_way_data = edge_data.get("wrong_way_alert") 
        
        self.neighbor_flood_alert = None
        for neighbor_id in self.neighbors:
            if global_macro_state.get(neighbor_id, {}).get("is_waterlogged"):
                self.neighbor_flood_alert = neighbor_id

        if self.network == "OFFLINE":
            self.island_time_remaining -= 5
            if self.island_time_remaining <= 0:
                self.island_index = (self.island_index + 1) % 4
                self.island_time_remaining = 60
        else: self.island_time_remaining = 60

        for lane, density in edge_data.get("densities", {}).items():
            self.lanes[lane] = density
            if density > 0 and self.current_green != lane:
                self.wait_times[lane] += 5 
            elif density == 0 or self.current_green == lane:
                self.wait_times[lane] = 0

    def calculate_next_state(self):
        # Deterministic Failsafes (AI should not guess emergencies)
        if self.network == "OFFLINE":
            self.current_green = self.island_cycle[self.island_index]
            return f"{self.current_green.upper()} (ISLAND MODE - {self.island_time_remaining}s)"

        if self.mcd_vip_override:
            self.current_green = self.mcd_vip_override
            return f"{self.current_green.upper()} (VIP OVERRIDE)"

        if self.emergency_v2x_lane:
            self.current_green = self.emergency_v2x_lane
            return f"{self.current_green.upper()} (V2X AMBULANCE)"

        # --- THE ML INFERENCE ENGINE ---
        reasoning = "ML Random Forest Prediction"
        
        # Prepare the exact feature vector the AI was trained on
        current_features = [
            self.lanes["north"], self.lanes["south"], self.lanes["east"], self.lanes["west"],
            self.wait_times["north"], self.wait_times["south"], self.wait_times["east"], self.wait_times["west"],
            self.visibility
        ]
        
        # 1. Ask the AI Model to predict the best lane based on patterns
        predicted_lane_index = self.ai_model.predict([current_features])[0]
        ai_choice = self.lane_map[predicted_lane_index]
        
        # 2. Post-Prediction Macro-Grid Filtering (Checking the AI's work)
        if ai_choice == "north" and self.neighbor_flood_alert:
            # If AI picks a flooded route, override it via Macro-Grid logic
            reasoning = f"AI Overridden: Reroute from {self.neighbor_flood_alert}"
            ai_choice = "south" if self.lanes["south"] > self.lanes["east"] else "east"
        elif self.is_waterlogged:
            reasoning = "Local Flood Lock"
            ai_choice = "IDLE"
        elif self.visibility < 30:
            # AI acoustic fusion logic
            reasoning = "AI Acoustic Inference"
            acoustics = [self.honk_levels["north"], self.honk_levels["south"], self.honk_levels["east"], self.honk_levels["west"]]
            ai_choice = self.lane_map[acoustics.index(max(acoustics))]
        elif ai_choice == self.heavy_transit_lane and ai_choice == self.current_green:
            reasoning = "AI MTMC Momentum Hold"

        self.current_green = ai_choice
        return f"{self.current_green.upper()} ({reasoning})"