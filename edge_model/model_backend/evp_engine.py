"""
Emergency Vehicle Preemption (EVP) Engine implementation.
Safely subclasses the main V6 TrafficEngine to add real-time 
interrupt logic based on ambulance Time-To-Arrival (TTA).
"""
import sys
from .engine import TrafficEngine, STATE_BASE_GREEN, STATE_EXTENSION, STATE_IDLE, STATE_YELLOW

class EVPTrafficEngine(TrafficEngine):
    """
    Extends TrafficEngine to provide a 2-tier Emergency Override:
      - 250m Far Zone: Soft cap current green to 15s max.
      - 150m Near Zone: Hard override. Instantly shift to yellow if red, or hold green indefinitely.
    """
    
    EVP_FAR_ZONE = 250   # Meters - Cap existing green to 15s
    EVP_NEAR_ZONE = 150  # Meters - Absolute override (Hold green or instantly abort current)
    EVP_MAX_HOLD = 45    # Maximum seconds an override can hold before timing out (Ghost ambulance)
    
    def __init__(self, intersection_id="INT-ITO-01", lane_ids=None):
        super().__init__(intersection_id, lane_ids)
        self.evp_target_lane = None
        self.evp_hold_timer = 0
        self.events_evp_overrides = 0
        self.last_alerted_amb_lane = None

    def get_highest_priority_arriving_ambulance(self):
        """Finds the ambulance with the lowest Time-To-Arrival (TTA) or VIP status."""
        ambs = []
        for n, data in self.lanes.items():
            if data.get("amb_dist") is not None and data["amb_dist"] > 0:
                ambs.append((n, data))
                
        if not ambs:
            return None
            
        vip_ambs = [(n, data) for n, data in ambs if data.get("vip", False)]
        if vip_ambs:
            return vip_ambs[0]
            
        def tta(item):
            d = item[1]
            speed = max(d.get("amb_speed", 1), 1)  # Prevent div zero
            return d["amb_dist"] / speed
            
        ambs.sort(key=tta)
        return ambs[0]

    def _evp_monitor(self):
        """
        Real-time monitor that interrupts standard state machine.
        Executed every tick before standard timer decrements.
        """
        amb_info = self.get_highest_priority_arriving_ambulance()
        
        if not amb_info:
            self.evp_target_lane = None
            self.evp_hold_timer = 0
            self.last_alerted_amb_lane = None
            return
            
        target_lane, data = amb_info
        dist = data["amb_dist"]
        
        # Send Cloud Alert if hitting Far Zone for the first time
        if dist <= self.EVP_FAR_ZONE and getattr(self, "reporter", None):
            if target_lane != getattr(self, "last_alerted_amb_lane", None):
                self.reporter.publish_ambulance_alert(target_lane, dist)
                self.last_alerted_amb_lane = target_lane
        
        # Reset hold timer if target shifts
        if target_lane != self.evp_target_lane:
            self.evp_target_lane = target_lane
            self.evp_hold_timer = 0
            
        # 1. Near Zone (<= 150m): Absolute Override
        if dist <= self.EVP_NEAR_ZONE:
            self.evp_hold_timer += 1
            if self.evp_hold_timer == 1:
                self.events_evp_overrides += 1
            
            # Anti-Ghost Timeout Failsafe (e.g. tracking lost or vehicle turned)
            if self.evp_hold_timer > self.EVP_MAX_HOLD:
                return

            if self.active_green == target_lane:
                # Target lane already green → HOLD IT OPEN
                if self.state in (STATE_BASE_GREEN, STATE_EXTENSION):
                    # Never let timer drop below 5s while crossing
                    new_val = max(self.green_timer, 5)
                    if new_val != self.green_timer:
                        self.green_timer = new_val
                    msg = f"EVP OVERRIDE: Holding Green for {target_lane} (Ambulance at {dist:.0f}m)"
                    if self.system["status_message"] != msg:
                        self.system["status_message"] = msg
                        self._log(msg)
            else:
                # Active green is NOT the target lane → INSTANT KICK
                if self.state in (STATE_BASE_GREEN, STATE_EXTENSION):
                    # Forcibly expire current phase to trigger yellow immediately
                    self.green_timer = 0
                    msg = f"EVP KICK: {self.active_green} instantly aborted for {target_lane}!"
                    if self.system["status_message"] != msg:
                        self.system["status_message"] = msg
                        self._log(msg)
                        
        # 2. Far Zone (<= 250m): Soft Cap
        elif dist <= self.EVP_FAR_ZONE:
            if self.active_green != target_lane and self.state in (STATE_BASE_GREEN, STATE_EXTENSION):
                if self.green_timer > 15:
                    self.green_timer = 15
                    msg = f"EVP PREP: Capping {self.active_green} to 15s for approaching Ambulance ({dist:.0f}m)"
                    if self.system["status_message"] != msg:
                        self.system["status_message"] = msg
                        self._log(msg)

    def tick_wait_times(self):
        """Override main loop to inject real-time monitor."""
        if self.state not in (STATE_IDLE, STATE_YELLOW):
            self._evp_monitor()
            
        # Run standard engine physics
        super().tick_wait_times()

    def _try_extension(self):
        """Override to boldly deny extensions if an ambulance is approaching."""
        amb_info = self.get_highest_priority_arriving_ambulance()
        if amb_info:
            target_lane, data = amb_info
            # If ambulance is within the "Far Zone" and wants a diff lane, deny the extension entirely.
            if data["amb_dist"] <= self.EVP_FAR_ZONE and target_lane != self.active_green:
                self._begin_yellow()
                self._log(f"EVP BLOCKED EXTENSION: Green handed over for {target_lane}")
                return
                
        # Safe to run normal extension logic
        super()._try_extension()
