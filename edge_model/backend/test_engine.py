"""
Northern Blades V5.5 — Core Engine Unit Tests
===============================================
Run with:  pytest backend/test_engine.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from engine import TrafficEngine


# ──────────────────────────────────────────────────────────────────
#  1. URGENCY SCORE (P = N × T)
# ──────────────────────────────────────────────────────────────────

class TestUrgencyScore:
    def test_basic_pressure_calculation(self):
        engine = TrafficEngine()
        engine.lanes["North"]["N"] = 80
        engine.lanes["North"]["T"] = 60
        engine.evaluate_intersection()
        # P_north = 80 * 60 = 4800 → should win green
        assert engine.active_green == "North"

    def test_side_street_starvation_beats_highway(self):
        """A side street waiting 180s should beat a main road with high N."""
        engine = TrafficEngine()
        engine.lanes["North"]["N"] = 90
        engine.lanes["North"]["T"] = 10   # P = 900
        engine.lanes["South"]["N"] = 5
        engine.lanes["South"]["T"] = 200  # P = 1000, also triggers starvation
        engine.evaluate_intersection()
        assert engine.active_green == "South"


# ──────────────────────────────────────────────────────────────────
#  2. VETO PRIORITY MATRIX
# ──────────────────────────────────────────────────────────────────

class TestVetoMatrix:
    def test_rank0_exit_blocked_forces_red(self):
        """If exit density > 85%, lane P is set to -1 (blocked)."""
        engine = TrafficEngine()
        engine.lanes["North"]["N"] = 95
        engine.lanes["North"]["T"] = 100
        engine.lanes["North"]["exit"] = 90  # Blocked exit
        engine.lanes["South"]["N"] = 20
        engine.lanes["South"]["T"] = 50
        engine.evaluate_intersection()
        # North should NOT get green despite high P
        assert engine.active_green != "North" or engine.active_green == "South"

    def test_rank1_ambulance_override(self):
        """V2X ambulance should get absolute Green override."""
        engine = TrafficEngine()
        engine.lanes["East"]["N"] = 90
        engine.lanes["East"]["T"] = 100  # Highest pressure
        engine.lanes["West"]["amb_dist"] = 200
        engine.lanes["West"]["amb_speed"] = 40
        engine.evaluate_intersection()
        assert engine.active_green == "West"

    def test_rank1_vip_ambulance_override(self):
        """VIP ambulance takes absolute priority."""
        engine = TrafficEngine()
        engine.lanes["North"]["amb_dist"] = 100
        engine.lanes["North"]["amb_speed"] = 30
        engine.lanes["North"]["vip"] = True
        engine.evaluate_intersection()
        assert engine.active_green == "North"

    def test_rank2_starvation_failsafe(self):
        """Lane waiting > 180s triggers mandatory rotation."""
        engine = TrafficEngine()
        engine.lanes["South"]["N"] = 10
        engine.lanes["South"]["T"] = 200  # Starved
        engine.lanes["North"]["N"] = 50
        engine.lanes["North"]["T"] = 30
        engine.evaluate_intersection()
        assert engine.active_green == "South"


# ──────────────────────────────────────────────────────────────────
#  3. ACCORDION DISCHARGE ($T_g$)
# ──────────────────────────────────────────────────────────────────

class TestAccordionDischarge:
    def test_min_green_enforced(self):
        engine = TrafficEngine()
        Tg = engine.calculate_green_duration(1)  # Very low density
        assert Tg >= engine.MIN_GREEN

    def test_max_green_enforced(self):
        engine = TrafficEngine()
        Tg = engine.calculate_green_duration(99)  # Near-max density
        assert Tg <= engine.MAX_GREEN

    def test_high_density_gets_longer_green(self):
        engine = TrafficEngine()
        Tg_low = engine.calculate_green_duration(20)
        Tg_high = engine.calculate_green_duration(80)
        assert Tg_high > Tg_low, "Higher density should produce longer green time"


# ──────────────────────────────────────────────────────────────────
#  4. DILEMMA ZONE SAFETY PULSE
# ──────────────────────────────────────────────────────────────────

class TestDilemmaZone:
    def test_safety_pulse_extends_timer(self):
        engine = TrafficEngine()
        engine.active_green = "North"
        engine.green_timer = 2  # About to expire
        engine.lanes["North"]["velocity"] = 50  # Fast platoon
        result = engine.check_dilemma_zone("North")
        assert result is True
        assert engine.green_timer == 5  # 2 + 3 = 5

    def test_no_pulse_when_slow(self):
        engine = TrafficEngine()
        engine.active_green = "North"
        engine.green_timer = 2
        engine.lanes["North"]["velocity"] = 10  # Slow traffic
        result = engine.check_dilemma_zone("North")
        assert result is False
        assert engine.green_timer == 2  # Unchanged


# ──────────────────────────────────────────────────────────────────
#  5. DYNAMIC ALL-RED BUFFER
# ──────────────────────────────────────────────────────────────────

class TestAllRedBuffer:
    def test_all_red_activates(self):
        engine = TrafficEngine()
        engine.trigger_all_red_buffer("Test")
        assert engine.all_red_active is True
        assert engine.all_red_timer == 2

    def test_all_red_prevents_green(self):
        engine = TrafficEngine()
        engine.lanes["North"]["N"] = 90
        engine.lanes["North"]["T"] = 100
        engine.trigger_all_red_buffer("Test")
        engine.evaluate_intersection()
        assert engine.active_green is None  # No green during all-red


# ──────────────────────────────────────────────────────────────────
#  6. THRASH-LOCK
# ──────────────────────────────────────────────────────────────────

class TestThrashLock:
    def test_green_timer_prevents_immediate_switch(self):
        engine = TrafficEngine()
        engine.active_green = "North"
        engine.green_timer = 10
        engine.lanes["South"]["N"] = 100
        engine.lanes["South"]["T"] = 200
        engine.lanes["North"]["N"] = 1
        engine.lanes["North"]["T"] = 0
        # North still has time on its timer, South should NOT take over instantly
        # (Unless starvation override kicks in, which it does here since T=200)
        # The starvation path also checks thrash-lock
        engine.evaluate_intersection()
        # Thrash-lock should hold North's green
        assert engine.active_green == "North"


# ──────────────────────────────────────────────────────────────────
#  RUN
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
