

import math
import time

STATE_IDLE          = "IDLE"
STATE_BASE_GREEN    = "BASE_GREEN"
STATE_EXTENSION     = "EXTENSION"
STATE_LOOKAHEAD     = "LOOKAHEAD"
STATE_YELLOW        = "YELLOW"
STATE_DYNAMIC_RED   = "DYNAMIC_RED"
STATE_ROUND_ROBIN_FLUSH = "ROUND_ROBIN_FLUSH"


class TrafficEngine:
  
    MIN_GREEN     = 15      
    MAX_GREEN     = 60        

    # ── T-8 Dispatcher ────────────────────────────────────────────
    DISPATCH_INTERVAL = 8     # Seconds between extension evaluations
    EXTENSION_CHUNK   = 8     # Seconds added per extension grant

    # ── Phase Transition ──────────────────────────────────────────
    YELLOW_DURATION   = 3     # Standard yellow phase (seconds)
    ALL_RED_BUFFER    = 2     # Fixed all-red clearance (seconds)

    # ── Intersection Gating (5th Camera) ──────────────────────────
    BOX_BLOCK_THRESHOLD    = 80   # % → triggers Dynamic Red hold
    BOX_RECOVERY_THRESHOLD = 60   # % → releases Dynamic Red hold
    MAX_DYNAMIC_RED        = 180  # 3 minutes max before Round Robin Flush

    # ── Safety ────────────────────────────────────────────────────
    MAX_PATIENCE_SECONDS = 180    # Anti-starvation (Rank 2)
    DILEMMA_ZONE_PULSE   = 3      # Extra seconds for platoon safety

    # ── Lookahead ─────────────────────────────────────────────────
    LOOKAHEAD_WINDOW     = 5      # Lock next winner at T-5 seconds

    # ==============================================================
    #  INIT
    # ==============================================================

    def __init__(self, intersection_id="INT-ITO-01", lane_ids=None):
        self.intersection_id = intersection_id
        if lane_ids is None:
            # Fallback for sandbox compatibility
            lane_ids = ["North", "South", "East", "West"]
            
        self.lanes = {l: self._new_lane() for l in lane_ids}

        # ── 5th Camera (God's Eye) ────────────────────────────────
        self.box_density = 0.0          # Current box occupancy %
        self.box_camera_ok = True       # False = degraded / offline

        # ── State Machine ─────────────────────────────────────────
        self.state = STATE_IDLE
        self.active_green = None        # Lane name currently green
        self.next_green = None          # Locked-in next winner (T-0)
        self.shadow_winner = None       # Locked-in backup winner (T-2)
        self.green_timer = 0            # Seconds remaining in current phase
        self.total_green_elapsed = 0    # Tracks total green given (Base + Exts)
        self.yellow_timer = 0
        self.dynamic_red_timer = 0
        self.extension_count = 0        # How many +8s extensions granted
        self.tick_count = 0              # Total ticks elapsed

        # ── Round Robin Flush State ───────────────────────────────
        self.round_robin_queue = []
        self.round_robin_active = False

        # ── Decision Log (last 30 events) ─────────────────────────
        self.decision_log = []
        self.green_history = []          # [{lane, base, extensions, total, start_tick}]
        
        # ── Holistic Cloud Reporter Metrics ───────────────────────
        self.events_gridlock_triggers = 0

        # ── System Health ─────────────────────────────────────────
        self.system = {
            "network": "OK",
            "yolo_conf": 1.0,
            "center_anomaly": None,
            "glare": False,
            "status_message": "V6.0 Engine Initializing...",
        }

        # ── Cloud Reporter (MCD Sync) ─────────────────────────────
        try:
            from cloud_reporter import CloudReporter
            self.reporter = CloudReporter(self)
            self.reporter.start()
        except ImportError:
            try:
                from backend.cloud_reporter import CloudReporter
                self.reporter = CloudReporter(self)
                self.reporter.start()
            except ImportError:
                self.reporter = None
                print("[Warning] CloudReporter not found, running locally only.")

    @staticmethod
    def _new_lane():
        return {
            "N": 0, "T": 0, "exit": 0, "exit_total": 0,
            "amb_dist": None, "amb_speed": 0, "vip": False,
            "edges": {}, "velocity": 0,
        }

    # ==============================================================
    #  GREEN TIME CALCULATION — Exponential Density + Wait Multiplier
    # ==============================================================

    def calculate_green_duration(self, N, T):
        """
        Calculates optimal base green using the user's Exponential Density formula.
        
        G_base = G_min + (D/100)^1.5 * (G_max - G_min)
        M_w = 1.0 + (0.5 * W/W_max)
        G_t = Clamp(G_base * M_w, G_min, G_max)
        """
        # 1. Guardrails to prevent mathematical explosions (e.g. D > 100%)
        D = min(max(N, 0.0), 100.0)
        W = min(max(T, 0.0), float(self.MAX_PATIENCE_SECONDS))
        
        # 2. Exponential Density Base (1.5 exponent creates 'slow-start' curve)
        g_base = self.MIN_GREEN + ( (D / 100.0) ** 1.5 ) * (self.MAX_GREEN - self.MIN_GREEN)
        
        # 3. Wait Time Multiplier (up to 1.5x boost for starving lanes)
        m_w = 1.0 + (0.5 * (W / self.MAX_PATIENCE_SECONDS))
        
        # 4. Final Clamped Output
        g_t = g_base * m_w
        return int(max(self.MIN_GREEN, min(self.MAX_GREEN, g_t)))

    # ==============================================================
    #  TICK — Called every 1 second by FastAPI asyncio loop
    # ==============================================================

    def tick_wait_times(self):
        """
        Master 1-second heartbeat.  Updates wait times, decrements
        timers, and advances the state machine.
        """
        self.tick_count += 1

        # ── Event-Driven Cloud Triggers ───────────────────────────
        if self.tick_count % 30 == 0 and hasattr(self, "reporter") and self.reporter:
            # 30-Second Hardware Pings
            self.reporter.publish_health()

        # ── Always tick Wait Time (T) for non-green lanes ─────────
        # During HYSTERESIS, ALL lanes accumulate T (Stored Pressure)
        for name, data in self.lanes.items():
            if name != self.active_green:
                data["T"] += 1
            else:
                data["T"] = 0

        # ── State Machine Advance ─────────────────────────────────
        if self.state == STATE_IDLE:
            self._handle_idle()

        elif self.state == STATE_BASE_GREEN:
            self._handle_base_green()

        elif self.state == STATE_EXTENSION:
            self._handle_extension()

        elif self.state == STATE_LOOKAHEAD:
            self._handle_lookahead()

        elif self.state == STATE_YELLOW:
            self._handle_yellow()

        elif self.state == STATE_DYNAMIC_RED:
            self._handle_dynamic_red()

        elif self.state == STATE_ROUND_ROBIN_FLUSH:
            self._handle_round_robin_flush()

    # ==============================================================
    #  STATE HANDLERS
    # ==============================================================

    # ── STATE_IDLE ────────────────────────────────────────────────

    def _handle_idle(self):
        """Pick the highest-priority lane and enter BASE_GREEN."""

        # ── Rank 0: Intersection Gating (5th Camera) ─────────────
        if self.box_camera_ok and self.box_density >= self.BOX_BLOCK_THRESHOLD:
            self.state = STATE_DYNAMIC_RED
            self.events_gridlock_triggers += 1
            self.active_green = None
            self.dynamic_red_timer = 0
            self._log(f"GRIDLOCK: Box={self.box_density:.0f}% → DYNAMIC RED freeze")
            self.system["status_message"] = (
                f"STATE_DYNAMIC_RED: Box={self.box_density:.0f}% ≥ {self.BOX_BLOCK_THRESHOLD}% — "
                f"Holding All-Red"
            )
            return

        # ── Select winner ─────────────────────────────────────────
        winner = self._select_winner()
        if winner is None:
            self.active_green = None
            self.system["status_message"] = "ALL-RED: No eligible lane"
            return

        # ── Enter BASE_GREEN ──────────────────────────────────────
        base = self.calculate_green_duration(self.lanes[winner]["N"], self.lanes[winner]["T"])
        self.active_green = winner
        self.green_timer = base
        self.total_green_elapsed = 0
        self.extension_count = 0
        self.next_green = None
        self.state = STATE_BASE_GREEN
        self.lanes[winner]["T"] = 0
        all_pressures = {n: d["N"] * d["T"] for n, d in self.lanes.items()}
        sorted_p = sorted(all_pressures.items(), key=lambda x: x[1], reverse=True)
        runners_up = [(n, p) for n, p in sorted_p if n != winner]
        reason = f"P={all_pressures[winner]:.0f}"
        if runners_up:
            reason += f" vs {runners_up[0][0]}:{runners_up[0][1]:.0f}"
        self._log(f"WINNER: {winner} | Base={base}s | REASON: Highest Pressure {reason}")
        self.green_history.append({"lane": winner, "base": base, "extensions": 0,
                                   "total": base, "start_tick": self.tick_count})
        self.system["status_message"] = (
            f"GREEN {winner}: Base={base}s (N={self.lanes[winner]['N']:.0f}%)"
        )
        if hasattr(self, "reporter") and self.reporter:
            self.reporter.publish_state("STATE_IDLE_TO_GREEN")

    # ── STATE_BASE_GREEN ──────────────────────────────────────────

    def _handle_base_green(self):
        """Tick down the base green phase."""
        self.green_timer -= 1
        self.total_green_elapsed += 1

        # ── T-2 Shadow Winner Backup ──────────────────────────────
        if self.green_timer == 2:
            self.shadow_winner = self._select_winner(exclude=self.active_green)

        if self.green_timer <= 0:
            # Base phase exhausted → check if extension is warranted
            self._try_extension()

    # ── STATE_EXTENSION ───────────────────────────────────────────

    def _handle_extension(self):
        """
        Tick down the current extension chunk.
        Every 8s boundary: re-evaluate inflow.
        """
        self.green_timer -= 1
        self.total_green_elapsed += 1

        # ── T-2 Shadow Winner Backup ──────────────────────────────
        if self.green_timer == 2:
            self.shadow_winner = self._select_winner(exclude=self.active_green)

        # ── Anti-Bully hard cap ───────────────────────────────────
        if self.total_green_elapsed >= self.MAX_GREEN:
            self.system["status_message"] = (
                f"ANTI-BULLY: {self.active_green} hit {self.MAX_GREEN}s cap → transitioning"
            )
            self._begin_yellow()
            return

        if self.green_timer <= 0:
            # Extension chunk exhausted → try another or begin handover
            self._try_extension()

    # ── Extension Logic ───────────────────────────────────────────

    def _try_extension(self):
        """
        Decide whether to grant another +8s extension or begin
        the handover sequence.
        """
        lane = self.active_green
        data = self.lanes[lane]

        # ── Check hard cap ────────────────────────────────────────
        if self.total_green_elapsed >= self.MAX_GREEN:
            self._begin_yellow()
            return

        # ── Check if inflow warrants a single extension ───────────
        # User Feedback: Greedy extensions are flawed. Only grant 
        # a MAXIMUM of 1 extension per phase to guarantee handover.
        if data["N"] > 15 and self.extension_count < 1:
            remaining_cap = self.MAX_GREEN - self.total_green_elapsed
            ext = min(self.EXTENSION_CHUNK, remaining_cap)
            if ext > 0:
                self.green_timer = ext
                self.extension_count += 1
                self.state = STATE_EXTENSION
                self._log(f"EXT #{self.extension_count}: {lane} +{ext}s | REASON: Inflow N={data['N']:.0f}% > 15% AND Exts<1")
                if self.green_history:
                    self.green_history[-1]["extensions"] = self.extension_count
                    self.green_history[-1]["total"] = self.total_green_elapsed + ext
                self.system["status_message"] = (
                    f"GREEN {lane}: Extension #{self.extension_count} +{ext}s "
                    f"(Total={self.total_green_elapsed + ext}s, N={data['N']:.0f}%)"
                )
                return

        # ── Inflow dried up or cap reached → begin handover ───────
        self._begin_yellow()

    # ── STATE_LOOKAHEAD ───────────────────────────────────────────

    def _handle_lookahead(self):
        """
        Timer is at T-5.  The next winner has been locked.
        Continue ticking until T=0, then start YELLOW.
        """
        self.green_timer -= 1
        self.total_green_elapsed += 1

        if self.green_timer <= 0:
            self._begin_yellow()

    # ── STATE_YELLOW ──────────────────────────────────────────────

    def _handle_yellow(self):
        """Tick down yellow timer, then check box density before switching."""
        self.yellow_timer -= 1
        if self.yellow_timer <= 0:
            if self.box_camera_ok and self.box_density >= self.BOX_BLOCK_THRESHOLD:
                self.state = STATE_DYNAMIC_RED
                self.events_gridlock_triggers += 1
                self.dynamic_red_timer = 0
                self.active_green = None
                self._log(f"RED TRIGGER: Box blocked (Density={self.box_density:.0f}%) — REASON: Intersection occupied ≥{self.BOX_BLOCK_THRESHOLD}% → All-Red Hold")
                self.system["status_message"] = (
                    f"DYNAMIC RED: Intersection Box occupied ({self.box_density:.0f}%)"
                )
            else:
                if self.round_robin_active:
                    self._start_next_round_robin()
                else:
                    self._transition_to_next()

    # ── STATE_DYNAMIC_RED ─────────────────────────────────────────

    def _handle_dynamic_red(self):
        """
        Hold All-Red until returning below the 60% recovery threshold.
        If exceeding 180s, queue up the Round-Robin Equalization Flush.
        """
        self.dynamic_red_timer += 1
        self.active_green = None

        # ── 180s Gridlock Detection ───────────────────────────────
        if self.dynamic_red_timer >= self.MAX_DYNAMIC_RED and not self.round_robin_active:
            self._log(f"MCD ALERT: 180s Gridlock Reached. Preparing Equalization Flush.")
            self.round_robin_active = True
            # Sort lanes by Wait Time (T) descending
            sorted_lanes = sorted(self.lanes.items(), key=lambda x: x[1]["T"], reverse=True)
            self.round_robin_queue = [lane_name for lane_name, _ in sorted_lanes]

        # ── Check if box has cleared (Hysteresis Release) ─────────
        if self.box_density <= self.BOX_RECOVERY_THRESHOLD:
            self._log(f"BOX CLEARED: Density={self.box_density:.0f}%")
            if self.round_robin_active:
                self.system["status_message"] = "BOX CLEAR: Starting Round-Robin Flush"
                self._start_next_round_robin()
            else:
                self.system["status_message"] = "BOX CLEAR: Resuming normal flow"
                self._transition_to_next()
            return

        msgtail = " (Wait for Flush)" if self.round_robin_active else f" ({self.dynamic_red_timer}s)"
        self.system["status_message"] = (
            f"DYNAMIC RED: Box={self.box_density:.0f}%" + msgtail
        )

    # ── STATE_ROUND_ROBIN_FLUSH ───────────────────────────────────

    def _handle_round_robin_flush(self):
        """Give each lane exactly 30s of green to flush the buildup."""
        self.green_timer -= 1
        self.total_green_elapsed += 1

        if self.green_timer <= 0:
            # End of this lane's 30s flush, transition to Yellow
            self.state = STATE_YELLOW
            self.yellow_timer = self.YELLOW_DURATION
            self.system["status_message"] = f"YELLOW {self.active_green}: Round-Robin transitioning"

    def _start_next_round_robin(self):
        if not self.round_robin_queue:
            # Done with RR flush, resume normal operations
            self.round_robin_active = False
            self.state = STATE_IDLE
            self._handle_idle()
            return
            
        lane = self.round_robin_queue.pop(0)
        self.active_green = lane
        self.lanes[lane]["T"] = 0
        self.green_timer = 30
        self.total_green_elapsed = 0
        self.next_green = None
        self.state = STATE_ROUND_ROBIN_FLUSH
        self._log(f"ROUND_ROBIN: {lane} gets 30s Flush")
        self.system["status_message"] = f"EQUALIZATION FLUSH: {lane} (30s)"

    # ==============================================================
    #  TRANSITION HELPERS
    # ==============================================================

    def _begin_yellow(self):
        """Transition the current green lane to yellow."""
        self.state = STATE_YELLOW
        self.yellow_timer = self.YELLOW_DURATION
        self._log(f"YELLOW: {self.active_green} ending (Total Green={self.total_green_elapsed}s)")
        self.system["status_message"] = (
            f"YELLOW {self.active_green}: {self.YELLOW_DURATION}s to clear intersection"
        )
        # Calculate Next Winner, with fallback to T-2 shadow winner
        try:
            self.next_green = self._select_winner(exclude=self.active_green)
        except Exception as e:
            self._log(f"CALC FAILED at T-0: {str(e)[:20]}... Fallback to Shadow Winner")
            self.next_green = self.shadow_winner
            
        if self.next_green is None:
            self.next_green = self.shadow_winner

        prev = self.active_green or "None" # Re-added this line to ensure 'prev' is defined
        self.system["status_message"] = (
            f"YELLOW {prev}: {self.YELLOW_DURATION}s transition → "
            f"Next: {self.next_green or 'TBD'}"
        )

    def _transition_to_next(self):
        """
        Complete the phase change: activate the locked-in next winner.
        If no next winner was locked, select one now.
        """
        if self.next_green is None:
            self.next_green = self._select_winner()

        if self.next_green is None:
            self.state = STATE_IDLE
            self.active_green = None
            self.system["status_message"] = "IDLE: No eligible lane after transition"
            return

        winner = self.next_green
        base = self.calculate_green_duration(self.lanes[winner]["N"], self.lanes[winner]["T"])

        self.active_green = winner
        self.green_timer = base
        self.total_green_elapsed = 0
        self.extension_count = 0
        self.next_green = None
        self.lanes[winner]["T"] = 0
        self.state = STATE_BASE_GREEN
        self.system["status_message"] = (
            f"GREEN {winner}: Base={base}s (N={self.lanes[winner]['N']:.0f}%)"
        )
        if hasattr(self, "reporter") and self.reporter:
            self.reporter.publish_state("NORMAL_PHASE_CHANGE")

    def _check_box_spike(self):
        """(Deprecated) Former Hysteresis mid-green block"""
        pass

    # ==============================================================
    #  WINNER SELECTION — The Veto Priority Matrix
    # ==============================================================

    def _select_winner(self, exclude=None):
        """
        Select the next Green lane using the strict Veto Priority Matrix:
            Rank 0: Physics (Exit Jam + Box Density) — absolute veto
            Rank 1: Life Safety (Ambulance / V2X)
            Rank 2: Human Psychology (Anti-Starvation > 180s)
            Rank 3: Mathematics (Highest P = N × T)
        
        Returns the lane name or None.
        """
        # ── Build candidate list ──────────────────────────────────
        candidates = {}
        for name, data in self.lanes.items():
            if name == exclude:
                continue

            N = data["N"]
            T = data["T"]

            # ── Rank 0: Physics Gate ──────────────────────────────
            # Exit jammed → lane is physically blocked, disqualify
            if data["exit"] > 85:
                continue

            # Edge-case modifiers
            edges = data["edges"]
            if edges.get("police_barricade_detected", False):
                N *= 0.5
            if edges.get("grap_truck_pct"):
                N -= (edges["grap_truck_pct"] * 0.8)
                N = max(0, N)
            if "static_pixels_pct" in edges:
                N = max(0, N - edges["static_pixels_pct"])
            if edges.get("occluded", False):
                N = edges.get("last_known_n", 0)
            if edges.get("pedestrian_swarm_detected", False):
                continue
            if edges.get("exit_blocked", False):
                continue

            P = N * T
            candidates[name] = {"P": P, "N": N, "T": T, "data": data}

        if not candidates:
            return None

        # ── Rank 1: Life Safety (Ambulance) ───────────────────────
        ambs = [(n, c) for n, c in candidates.items()
                if c["data"]["amb_dist"] is not None]

        # VIP + Ambulance = absolute override
        vip_ambs = [(n, c) for n, c in ambs if c["data"].get("vip", False)]
        if vip_ambs:
            return vip_ambs[0][0]

        if ambs:
            # Sort by Time-To-Arrival (TTA)
            def tta(item):
                d = item[1]["data"]
                speed = max(d.get("amb_speed", 1), 1)
                return d["amb_dist"] / speed
            ambs.sort(key=tta)
            return ambs[0][0]

        # ── Rank 2: Anti-Starvation (T > 180s) ───────────────────
        # NOTE: This ONLY fires for lanes that PASSED Rank 0 physics.
        starved = [(n, c) for n, c in candidates.items()
                   if c["T"] >= self.MAX_PATIENCE_SECONDS and c["N"] > 0]
        if starved:
            starved.sort(key=lambda x: x[1]["T"], reverse=True)
            return starved[0][0]

        # ── Rank 3: Mathematics (Highest P = N × T) ──────────────
        ranked = sorted(candidates.items(),
                        key=lambda x: (x[1]["P"], x[1]["T"], x[1]["N"]),
                        reverse=True)
        return ranked[0][0]

    # ==============================================================
    #  DATA INGESTION (API Surface — unchanged for compatibility)
    # ==============================================================

    def ingest_telemetry(self, payload):
        """Process edge node telemetry (4 lane cameras)."""
        lane = payload.get("lane")
        if lane in self.lanes:
            self.lanes[lane]["N"] = payload.get("primary", 0) + payload.get("spill", 0)
            self.lanes[lane]["exit"] = payload.get("exit", 0)
            self.lanes[lane]["exit_total"] += payload.get("exit", 0)
            self.lanes[lane]["velocity"] = payload.get("velocity", 0)
            self.lanes[lane]["edges"] = payload.get("edges", {})

    def ingest_box_density(self, payload):
        """
        Process 5th Camera (God's Eye) telemetry.
        Expected: {"box_density": 42.5, "confidence": 0.92}
        """
        self.box_density = payload.get("box_density", 0.0)
        conf = payload.get("confidence", 1.0)

        # Graceful Degradation: if 5th camera confidence is too low,
        # disable box-gating to prevent phantom gridlocks
        if conf < 0.30:
            self.box_camera_ok = False
            self.system["status_message"] = (
                f"DEGRADED: 5th camera confidence={conf:.0%} — "
                f"Box gating disabled, falling back to V5.5 mode"
            )
        else:
            self.box_camera_ok = True

    def ingest_v2x(self, payload):
        """Process V2X ambulance/emergency telemetry."""
        lane = payload.get("lane")
        if lane in self.lanes:
            self.lanes[lane]["amb_dist"] = payload.get("distance")
            self.lanes[lane]["amb_speed"] = payload.get("speed", 0)
            self.lanes[lane]["vip"] = payload.get("vip", False)

    def ingest_sandbox(self, payload):
        """
        Manual sandbox override for testing.
        Resets state to IDLE for immediate re-evaluation.
        """
        self.state = STATE_IDLE
        self.green_timer = 0
        self.total_green_elapsed = 0
        self.active_green = None

        for lane, data in payload.items():
            if lane == "box_density":
                self.box_density = data
                continue
            if lane in self.lanes:
                self.lanes[lane]["N"] = data.get("N", 0)
                self.lanes[lane]["T"] = data.get("T", 0)
                self.lanes[lane]["exit"] = data.get("exit", 0)
                self.lanes[lane]["edges"] = data.get("edges", {})
                self.lanes[lane]["amb_dist"] = data.get("amb_dist", None)
                self.lanes[lane]["amb_speed"] = data.get("amb_speed", 0)
                self.lanes[lane]["vip"] = data.get("vip", False)

        # Immediately evaluate
        self._handle_idle()

    # ==============================================================
    #  GETTERS (API Surface — unchanged for compatibility)
    # ==============================================================

    def _log(self, msg):
        """Append timestamped message to decision log (max 30)."""
        entry = {"tick": self.tick_count, "msg": msg}
        self.decision_log.append(entry)
        if len(self.decision_log) > 30:
            self.decision_log.pop(0)

    def get_current_state(self):
        # Build P scores for each lane
        scores = {}
        for name, data in self.lanes.items():
            N = data["N"]
            T = data["T"]
            scores[name] = {"N": N, "T": T, "P": N * T, "exit": data["exit"]}

        return {
            "state": self.state,
            "tick": self.tick_count,
            "lanes": self.lanes,
            "scores": scores,
            "box_density": self.box_density,
            "box_camera_ok": self.box_camera_ok,
            "active_green": self.active_green,
            "next_green": self.next_green,
            "green_timer": self.green_timer,
            "total_green_elapsed": self.total_green_elapsed,
            "extension_count": self.extension_count,
            "system_health": self.system,
            "decision_log": self.decision_log[-15:],
            "green_history": self.green_history[-10:],
        }

    def get_active_green(self):
        return self.active_green

    # ==============================================================
    #  LEGACY COMPATIBILITY
    # ==============================================================

    def trigger_all_red_buffer(self, reason="Safety override"):
        """
        Legacy method for acoustic siren handler compatibility.
        In V6.0, this triggers DYNAMIC_RED state.
        """
        self.state = STATE_DYNAMIC_RED
        self.dynamic_red_timer = 0
        self.active_green = None
        self.system["status_message"] = f"DYNAMIC RED: {reason}"
